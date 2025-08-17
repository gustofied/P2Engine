from __future__ import annotations

import base64
import gzip
import json
import os
from pathlib import Path
from typing import Any, Dict

from infra.logging.logging_config import logger

from .base import BaseStorageDriver


class FSStorageDriver(BaseStorageDriver):
    """
    Stores artefacts on the local filesystem.

    ── New layout ───────────────────────────────
    <run-dir>/artifacts/<session_id>/payloads/<ref>.<ext>[.gz]
    <run-dir>/artifacts/<session_id>/journal.ndjson
    ─────────────────────────────────────────────
    (older runs that still live under .../artifacts/agents/
     will continue to be readable – see read_payload()).
    """

    def __init__(self, base_dir: Path):
        self.base_dir = base_dir
        self.journal_enabled: bool = os.getenv("ARTIFACT_JOURNAL", "1") != "0"
        self.payload_files_enabled: bool = os.getenv("ARTIFACT_PAYLOAD_FILES", "0") == "1"

    @staticmethod
    def _ext(mime: str) -> str:
        return {"application/json": "json", "text/plain": "txt"}.get(mime, "bin")


    def _payload_path(self, session: str, ref: str, mime: str, compressed: bool) -> Path:
        ext = self._ext(mime) + (".gz" if compressed else "")
        return self.base_dir / "artifacts" / session / "payloads" / f"{ref}.{ext}"

    def _legacy_payload_path(self, session: str, ref: str, mime: str, compressed: bool) -> Path:
        """Path used by older runs that still wrote to artifacts/agents/…"""
        ext = self._ext(mime) + (".gz" if compressed else "")
        return self.base_dir / "artifacts" / "agents" / session / "payloads" / f"{ref}.{ext}"

    def _journal_path(self, session: str) -> Path:
        return self.base_dir / "artifacts" / session / "journal.ndjson"

    def _legacy_journal_path(self, session: str) -> Path:
        return self.base_dir / "artifacts" / "agents" / session / "journal.ndjson"


    def write_payload(
        self,
        session_id: str,
        ref: str,
        payload: Any,
        mime: str,
        header: Dict[str, Any],
    ) -> None:
        if mime == "application/json":
            blob: bytes = json.dumps(payload, separators=(",", ":")).encode()
        elif mime == "text/plain":
            blob = payload.encode()
        else:
            blob = payload if isinstance(payload, (bytes, bytearray)) else bytes(payload)

        header["raw_len"] = len(blob)

        compressed = header.get("compressed")
        if compressed is None:
            compressed = len(blob) > 2048
            header["compressed"] = compressed
        if compressed:
            blob = gzip.compress(blob)

        if self.payload_files_enabled:
            p = self._payload_path(session_id, ref, mime, compressed)
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_bytes(blob)

        if self.journal_enabled:
            self._append_to_journal(session_id, header, payload)

        logger.debug(
            {
                "message": "Artifact payload written",
                "session": session_id,
                "ref": ref,
                "compressed": compressed,
                "bytes": len(blob),
            }
        )


    def read_payload(self, session_id: str, ref: str, mime: str) -> Any:
        """
        Tries the new location first, then falls back to the legacy path so
        old sessions remain accessible.
        """
        for compressed in (False, True):
            path = self._payload_path(session_id, ref, mime, compressed)
            if self.payload_files_enabled and path.exists():
                data = path.read_bytes()
                if compressed:
                    data = gzip.decompress(data)
                return self._decode(data, mime)

        for compressed in (False, True):
            path = self._legacy_payload_path(session_id, ref, mime, compressed)
            if self.payload_files_enabled and path.exists():
                data = path.read_bytes()
                if compressed:
                    data = gzip.decompress(data)
                return self._decode(data, mime)

        for jp in (self._journal_path(session_id), self._legacy_journal_path(session_id)):
            if not jp.exists():
                continue
            with jp.open(encoding="utf-8") as f:
                for line in f:
                    try:
                        entry = json.loads(line)
                    except json.JSONDecodeError:
                        continue
                    if entry.get("header", {}).get("ref") == ref:
                        return entry["payload"]

        raise FileNotFoundError(f"Artifact {ref} not found")


    def delete_payload(self, session_id: str, ref: str, mime: str, compressed: bool) -> None:
        for builder in (self._payload_path, self._legacy_payload_path):
            p = builder(session_id, ref, mime, compressed)
            if p.exists():
                p.unlink(missing_ok=True)



    @staticmethod
    def _decode(data: bytes, mime: str) -> Any:
        if mime == "application/json":
            return json.loads(data.decode())
        if mime == "text/plain":
            return data.decode()
        return data

    def _append_to_journal(self, session: str, header: Dict[str, Any], payload: Any) -> None:
        journal = self._journal_path(session)
        journal.parent.mkdir(parents=True, exist_ok=True)
        entry = {"header": header, "payload": payload}
        if isinstance(payload, (bytes, bytearray)):
            entry["payload"] = {"type": "bytes", "data": base64.b64encode(payload).decode()}
        with journal.open("a", encoding="utf-8") as f:
            f.write(json.dumps(entry, separators=(",", ":")) + "\n")
