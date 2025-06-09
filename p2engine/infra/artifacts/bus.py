from __future__ import annotations

import json
import os
import threading
from importlib import resources
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import redis

from infra.artifacts.schema import (
    ArtifactHeader,
    current_timestamp,
    generate_ref,
    parse_timestamp,
)
from infra.logging.logging_config import logger
from .drivers.base import BaseStorageDriver
from .drivers.fs_driver import FSStorageDriver

# ────────────────────────────────────────────────────────────────────────────
__all__ = ["ArtifactBus", "get_bus"]


class ArtifactBus:
    """
    Responsible for *all* durable storage of artefacts plus a thin Redis index
    that powers fast queries.  Implemented as a process-local singleton.
    """

    _instance: "ArtifactBus | None" = None
    _lock = threading.Lock()

    def __init__(self, redis_client: redis.Redis, driver: BaseStorageDriver):
        self.redis = redis_client
        self.driver = driver

        # key templates
        self.stream_key = "stream:artifacts"
        self.index_tpl = "artifacts:{session}:index"
        self.header_tpl = "artifacts:{session}:headers"
        self.timeline_tpl = "artifacts:{session}:timeline"

        self._lua_sha_next_idx: str | None = None
        self._load_lua_scripts()

    # ------------------------------------------------------------------ class factory
    @classmethod
    def get_instance(
        cls,
        *,
        redis_client: Optional[redis.Redis] = None,
        driver: Optional[BaseStorageDriver] = None,
        base_dir: Optional[Path] = None,
    ) -> "ArtifactBus":
        """
        Acquire (or lazily create) the process-wide singleton.
        """
        if cls._instance is not None:
            return cls._instance

        with cls._lock:
            if cls._instance is None:
                if redis_client is None:
                    raise ValueError("First call must provide redis_client")
                if driver is None:
                    base_dir = base_dir or Path(os.getenv("BASE_DIR", "."))
                    driver = FSStorageDriver(base_dir=base_dir)
                cls._instance = cls(redis_client, driver)

        return cls._instance

    __call__ = get_instance  # legacy alias (kept for ABI)

    # ------------------------------------------------------------------ Lua helper
    def _load_lua_scripts(self) -> None:
        lua_src = resources.files("infra.artifacts.lua").joinpath("next_idx.lua").read_text()
        self._lua_sha_next_idx = self.redis.script_load(lua_src)

    def _next_step_idx(self, session: str, branch: str, ref: str) -> int:
        try:
            return int(self.redis.evalsha(self._lua_sha_next_idx, 0, session, branch, ref))
        except redis.exceptions.ResponseError as exc:
            if "NOSCRIPT" in str(exc):  # hot-reload after Redis restart
                self._load_lua_scripts()
                return int(self.redis.evalsha(self._lua_sha_next_idx, 0, session, branch, ref))
            raise

    # ------------------------------------------------------------------ patch helpers
    def patch_artifact(
        self,
        ref: str,
        *,
        updates_header: Dict[str, Any] | None = None,
        updates_payload: Dict[str, Any] | None = None,
    ) -> None:
        """
        Atomic, in-place modifications of an artefact.  Safe for concurrent use
        from multiple workers – all writes happen under Redis primitives.
        """
        hdr_key, idx_key = self._header_by_ref(ref, return_keys=True)
        raw_hdr = self.redis.hget(hdr_key, ref)
        if not raw_hdr:
            raise KeyError(f"Artifact {ref!r} header missing")

        # deserialize header
        header: ArtifactHeader = json.loads(raw_hdr)

        # ── header patch ───────────────────────────────────────────────
        if updates_header:
            meta_patch = updates_header.pop("meta", None)
            header.update(updates_header)
            if meta_patch:
                header_meta = header.setdefault("meta", {})
                header_meta.update(meta_patch)

        # ── payload patch ──────────────────────────────────────────────
        if updates_payload is not None:
            try:
                payload = self.driver.read_payload(header["session_id"], ref, header["mime"])
            except Exception as exc:
                logger.warning({"message": "patch_read_payload_failed", "ref": ref, "error": str(exc)})
                payload = {}

            if isinstance(payload, dict) and isinstance(updates_payload, dict):
                payload.update(updates_payload)
            else:
                payload = updates_payload

            try:
                self.driver.write_payload(
                    session_id=header["session_id"],
                    ref=ref,
                    payload=payload,
                    mime=header["mime"],
                    header=header,
                )
            except Exception as exc:
                logger.error(
                    {"message": "patch_write_payload_failed", "ref": ref, "error": str(exc)},
                    exc_info=True,
                )

        # ── lean-index patch (score / meta) ────────────────────────────
        raw_lean = self.redis.hget(idx_key, ref)
        if raw_lean:
            lean = json.loads(raw_lean)
            if "score" in header:
                lean["score"] = header["score"]
            if "meta" in header:
                lean["meta"] = header["meta"]
            self.redis.hset(idx_key, ref, json.dumps(lean))

        # keep sorted-set up-to-date for score queries
        if header.get("score") is not None:
            scores_z = f"artifacts:{header['session_id']}:scores"
            self.redis.zadd(scores_z, {ref: header["score"]})

        # finally store patched header + stream event
        self.redis.hset(hdr_key, ref, json.dumps(header))
        self.redis.xadd(
            self.stream_key,
            {k: json.dumps(v) if not isinstance(v, str) else v for k, v in header.items()},
            maxlen=100_000,
            approximate=True,
        )
        logger.info(
            {
                "message": "artifact_patched",
                "ref": ref,
                "session": header["session_id"],
                "updates_header": bool(updates_header),
                "updates_payload": bool(updates_payload),
            }
        )

    def patch_evaluation(
        self,
        ref: str,
        *,
        evaluator_id: str,
        judge_version: str,
        score: float,
        metrics: Dict[str, float],
        review: Optional[str] = None,
        reward: Optional[float] = None,
    ) -> None:
        """
        Convenience helper used by the **judge worker** once it has produced a
        score / review.
        """
        hdr_updates: Dict[str, Any] = {
            "evaluator_id": evaluator_id,
            "judge_version": judge_version,
            "score": score,
            "meta": {"eval_metrics": metrics, "status": "finished"},
        }
        if reward is not None:
            hdr_updates["reward"] = reward

        payload_updates: Dict[str, Any] = {"score": score}
        if review is not None:
            payload_updates["review"] = review

        self.patch_artifact(ref, updates_header=hdr_updates, updates_payload=payload_updates)

    # ------------------------------------------------------------------ evaluation helpers
    def create_evaluation(
        self,
        *,
        session_id: str,
        branch_id: str,
        evaluator_id: str,
        judge_version: str,
        payload: Dict[str, Any],
    ) -> str:
        """
        Synchronously *records* an evaluation request (status=pending) then
        immediately schedules the Celery job via **EvaluationCoordinator**.
        """
        header: ArtifactHeader = {
            "ref": generate_ref(),
            "session_id": session_id,
            "branch_id": branch_id,
            "episode_id": "",
            "group_id": None,
            "parent_refs": payload.get("parent_refs", []),
            "role": "evaluation",
            "mime": "application/json",
            "ts": current_timestamp(),
            "agent_id": evaluator_id,
            "evaluator_id": evaluator_id,
            "judge_version": judge_version,
            "score": None,
            "reward": None,
            "meta": {"status": "pending", "eval_metrics": {}},
        }

        # persist artefact first (so workers can stream-watch it)
        self._persist_artifact(header, payload)

        # schedule the worker task (new, direct route – no flush timer)
        from runtime.tasks.celery_app import app as celery_app
        from infra.evals.batcher import EvaluationCoordinator

        EvaluationCoordinator(self.redis, celery_app).schedule(  # type: ignore[call-arg]
            header["ref"],
            evaluator_id,
            judge_version,
            payload,
        )

        logger.info(
            {
                "message": "evaluation_created",
                "ref": header["ref"],
                "session": session_id,
                "branch": branch_id,
                "evaluator": evaluator_id,
            }
        )
        return header["ref"]

    def create_evaluation_for(
        self,
        target_ref: str,
        *,
        evaluator_id: str,
        judge_version: str | None = None,
        payload: Dict[str, Any] | None = None,
    ) -> str:
        """
        Helper that infers *session & branch* from an existing artefact ref.
        """
        from infra.evals.registry import registry

        payload = payload or {}
        target_hdr = self._header_by_ref(target_ref)

        if judge_version is None:
            try:
                judge_version = registry.get(evaluator_id).version
            except Exception:
                judge_version = "0"

        return self.create_evaluation(
            session_id=target_hdr["session_id"],
            branch_id=target_hdr["branch_id"],
            evaluator_id=evaluator_id,
            judge_version=judge_version,
            payload={"parent_refs": [target_ref], **payload},
        )

    # ------------------------------------------------------------------ timeline helpers
    def evaluations_for(
        self,
        session_id: str,
        branch_id: Optional[str] = None,
    ) -> List[Tuple[ArtifactHeader, Any]]:
        """
        Return **all** evaluation artefacts for a session (optionally filtered
        to a branch) ordered by timestamp.
        """
        idx_key = self.index_tpl.format(session=session_id)
        out: List[Tuple[ArtifactHeader, Any]] = []

        for ref, raw_lean in self.redis.hscan_iter(idx_key):
            lean: ArtifactHeader = json.loads(raw_lean)
            if lean.get("role") != "evaluation":
                continue
            if branch_id and lean.get("branch_id") != branch_id:
                continue
            payload = self.driver.read_payload(session_id, ref, lean["mime"])
            out.append((lean, payload))

        out.sort(key=lambda pair: pair[0]["ts"])
        return out

    # ------------------------------------------------------------------ *publishing* a new artefact
    def publish(self, header: ArtifactHeader, payload: Any) -> None:
        """
        Low-level entry-point: store an artefact (state, tool-call, metrics…).
        Public so that outside callers can bypass convenience helpers.
        """
        self._persist_artifact(header, payload)

    # ------------------------------------------------------------------ internal persistence
    def _persist_artifact(self, header: ArtifactHeader, payload: Any) -> None:
        """
        Writes payload to backing store + updates Redis indices, all
        transactionally.  Called by *every* public write helper.
        """
        header["ref"] = header.get("ref") or generate_ref()
        header["ts"] = header.get("ts") or current_timestamp()
        header.setdefault("episode_id", "")
        header.setdefault("group_id", None)
        header.setdefault("parent_refs", [])
        header.setdefault("role", header.get("type", "state"))

        session_id: str = header["session_id"]
        branch_id: str = header["branch_id"]
        ref: str = header["ref"]

        # monotonic step index per branch
        step_idx = self._next_step_idx(session_id, branch_id, ref)
        header["step_idx"] = step_idx

        # write payload (can be large, goes to FS/S3)
        self.driver.write_payload(
            session_id=session_id,
            ref=ref,
            payload=payload,
            mime=header["mime"],
            header=header,
        )

        # slim “lean” index object (fast lookup)
        lean: Dict[str, Any] = {
            "ts": header["ts"],
            "role": header["role"],
            "type": header["role"],
            "branch_id": branch_id,
            "mime": header["mime"],
            "step_idx": step_idx,
            "episode_id": header["episode_id"],
            "group_id": header.get("group_id"),
            "score": header.get("score"),
            "compressed": header.get("compressed"),
            "raw_len": header.get("raw_len"),
        }
        if "meta" in header:
            lean["meta"] = header["meta"]

        # Redis keys
        idx_key = self.index_tpl.format(session=session_id)
        hdr_key = self.header_tpl.format(session=session_id)
        tline_key = self.timeline_tpl.format(session=session_id)
        episode_z = f"artifacts:{session_id}:episode:{header['episode_id']}"
        group_z = f"artifacts:{session_id}:group:{header['group_id']}" if header.get("group_id") else None
        scores_z = f"artifacts:{session_id}:scores"
        ts_unix = parse_timestamp(header["ts"])

        with self.redis.pipeline() as pipe:
            pipe.hset(hdr_key, ref, json.dumps(header))
            pipe.hset(idx_key, ref, json.dumps(lean))
            pipe.zadd(tline_key, {ref: ts_unix})
            if header["episode_id"]:
                pipe.zadd(episode_z, {ref: step_idx})
            if group_z:
                pipe.zadd(group_z, {ref: step_idx})
            if header.get("score") is not None:
                pipe.zadd(scores_z, {ref: header["score"]})
            pipe.hset("artifacts:ref_to_session", ref, session_id)
            pipe.xadd(
                self.stream_key,
                {k: json.dumps(v) if not isinstance(v, str) else v for k, v in header.items()},
                maxlen=100_000,
                approximate=True,
            )
            pipe.execute()

        logger.info(
            {
                "message": "artifact_published",
                "ref": ref,
                "session": session_id,
                "branch": branch_id,
                "step_idx": step_idx,
                "role": header["role"],
            }
        )

        self._maybe_prune(session_id, tline_key)

    # ------------------------------------------------------------------ internal helpers
    def _header_by_ref(self, ref: str, *, return_keys: bool = False):
        session_id_b = self.redis.hget("artifacts:ref_to_session", ref)
        if not session_id_b:
            raise KeyError(f"Artifact {ref!r} not found")

        session_id = session_id_b.decode() if isinstance(session_id_b, (bytes, bytearray)) else session_id_b
        hdr_key = self.header_tpl.format(session=session_id)
        idx_key = self.index_tpl.format(session=session_id)

        if return_keys:
            return hdr_key, idx_key

        raw = self.redis.hget(hdr_key, ref)
        if not raw:
            raise KeyError(f"Artifact {ref!r} header missing")

        return json.loads(raw)

    def _maybe_prune(self, session_id: str, timeline_key: str) -> None:
        """
        Enforce ``MAX_ARTIFACTS_PER_SESSION`` by deleting the oldest artefacts
        from both Redis and the backing store.  Runs synchronously but on a
        simple ZRANGE so impact is minimal.
        """
        limit = int(os.getenv("MAX_ARTIFACTS_PER_SESSION", "100000"))
        current = self.redis.zcard(timeline_key)
        if current <= limit:
            return

        to_del = current - limit
        old_refs = self.redis.zrange(timeline_key, 0, to_del - 1)

        hdr_key = self.header_tpl.format(session=session_id)
        idx_key = self.index_tpl.format(session=session_id)

        old_refs_s = [r.decode() if isinstance(r, bytes) else r for r in old_refs]

        # delete payloads from driver
        for ref in old_refs_s:
            raw_hdr = self.redis.hget(hdr_key, ref)
            if raw_hdr is None:
                continue
            hdr = json.loads(raw_hdr)
            mime = hdr.get("mime", "application/octet-stream")
            compressed = bool(hdr.get("compressed"))
            try:
                self.driver.delete_payload(session_id, ref, mime, compressed)
            except Exception as exc:
                logger.warning({"message": "payload_prune_failed", "ref": ref, "error": str(exc)})

        # trim Redis indices
        with self.redis.pipeline() as pipe:
            pipe.zrem(timeline_key, *old_refs_s)
            pipe.hdel(idx_key, *old_refs_s)
            pipe.hdel(hdr_key, *old_refs_s)
            pipe.execute()

        logger.debug({"message": "pruned", "session": session_id, "removed": len(old_refs_s)})

    # ------------------------------------------------------------------ convenience readers
    def read_first_n(
        self,
        n: int,
        *,
        session_id: str,
        role: str | None = None,
    ) -> List[Tuple[ArtifactHeader, object]]:
        """
        Return the *oldest* ``n`` artefacts (optionally filtered by role).
        """
        timeline_key = self.timeline_tpl.format(session=session_id)
        refs = self.redis.zrange(timeline_key, 0, n - 1)

        out: List[Tuple[ArtifactHeader, object]] = []
        for ref_b in refs:
            ref = ref_b.decode() if isinstance(ref_b, (bytes, bytearray)) else ref_b
            hdr, payload = self.get(ref)
            if role and hdr.get("role") != role:
                continue
            out.append((hdr, payload))
        return out

    def read_last_n(
        self,
        n: int,
        *,
        session_id: str,
        role: str | None = None,
    ) -> List[Tuple[ArtifactHeader, object]]:
        """
        Return the *newest* ``n`` artefacts (optionally filtered by role).
        """
        timeline_key = self.timeline_tpl.format(session=session_id)
        refs = self.redis.zrevrange(timeline_key, 0, n - 1)

        out: List[Tuple[ArtifactHeader, object]] = []
        for ref_b in refs:
            ref = ref_b.decode() if isinstance(ref_b, (bytes, bytearray)) else ref_b
            hdr, payload = self.get(ref)
            if role and hdr.get("role") != role:
                continue
            out.append((hdr, payload))
        return out

    def search(
        self,
        session_id: str,
        *,
        tag: str | None = None,
        since: str | None = None,
        limit: int = 50,
    ) -> List[Tuple[ArtifactHeader, object]]:
        """
        Simple linear scan across the timeline (newest→oldest) applying optional
        tag / timestamp filters.  Good enough for operator CLI tooling.
        """
        timeline_key = self.timeline_tpl.format(session=session_id)
        refs = self.redis.zrevrange(timeline_key, 0, -1)

        rows: List[Tuple[ArtifactHeader, object]] = []
        ts_cutoff: float | None = parse_timestamp(since) if since else None

        for ref_b in refs:
            if len(rows) >= limit:
                break
            ref = ref_b.decode() if isinstance(ref_b, (bytes, bytearray)) else ref_b
            hdr, payload = self.get(ref)

            if ts_cutoff is not None and parse_timestamp(hdr["ts"]) < ts_cutoff:
                continue
            if tag and tag not in hdr.get("meta", {}).get("tags", []):
                continue
            rows.append((hdr, payload))

        return rows

    # ------------------------------------------------------------------ public accessor
    def get(self, ref: str) -> Tuple[ArtifactHeader, Any]:
        """
        Fetch *header & payload* for a single ref.  Raises ``KeyError`` if not
        found (callers treat missing artefacts as fatal).
        """
        header = self._header_by_ref(ref)
        payload = self.driver.read_payload(header["session_id"], ref, header["mime"])
        return header, payload


# --------------------------------------------------------------------------- utility
def get_bus() -> ArtifactBus:
    if ArtifactBus._instance is None:
        raise RuntimeError("ArtifactBus not yet initialised")
    return ArtifactBus._instance
