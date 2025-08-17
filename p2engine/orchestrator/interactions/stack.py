from __future__ import annotations

import json
import re
import uuid
from dataclasses import asdict, dataclass
from typing import Iterable, List, Optional, Union

import redis

from infra.artifacts.bus import get_bus
from infra.artifacts.schema import ArtifactHeader, current_timestamp, generate_ref
from infra.logging.logging_config import logger
from runtime.constants import MAX_STACK_LEN

from .serializers import decode, encode
from .states.agent_call import AgentCallState
from .states.agent_result import AgentResultState
from .states.assistant_message import AssistantMessageState
from .states.base import BaseState
from .states.finished import FinishedState
from .states.tool_call import ToolCallState
from .states.tool_result import ToolResultState


def _b2s(v: Union[str, bytes, None]) -> Optional[str]:
    return v if v is None or isinstance(v, str) else v.decode()


_BRANCH_SUFFIX_RE = re.compile(r":[0-9a-f]{8}$")


@dataclass(slots=True)
class StackEntry:
    state: BaseState
    ts: float


class InteractionStack:
    def __init__(
        self,
        r: redis.Redis,
        conversation_id: str,
        agent_id: str = "default",
    ):
        self.r = r
        self.redis = r

        self.cid = conversation_id
        self.aid = agent_id

        self._base_key = f"stack:{self.cid}:{self.aid}"
        self._ptr_key = f"{self._base_key}:branch"

        self._branch_id: Optional[str] = None
        self.refresh_current_branch()

        self._episode_key_tpl = f"{self._base_key}:episode:{{branch}}"

        self._rollout_team: Optional[str] = None
        self._rollout_variant: Optional[str] = None


    def _branch_key(self, branch_id: str) -> str:
        return self._base_key if branch_id == "main" else f"{self._base_key}:{branch_id}"

    def _all_branch_ids(self) -> List[str]:
        found: set[str] = {"main"}
        pattern = f"{self._base_key}:*"
        for raw in self.redis.scan_iter(match=pattern):
            key = raw.decode() if isinstance(raw, bytes) else raw
            if key == self._ptr_key:
                continue
            if _BRANCH_SUFFIX_RE.search(key):
                found.add(key.rsplit(":", 1)[-1])
        return sorted(found)

    def _get_rollout_provenance(self) -> tuple[Optional[str], Optional[str]]:
        if self._rollout_team is None and self._rollout_variant is None:
            self._rollout_team = _b2s(self.redis.get(f"{self.cid}:team"))
            self._rollout_variant = _b2s(self.redis.get(f"{self.cid}:variant"))
        return self._rollout_team, self._rollout_variant


    def push(self, *states: BaseState, group_id: Optional[str] = None) -> None:
        """
        Push one or more states onto the current branch and persist them
        as artefacts.  Includes *lazy* agent registration: if this is the
        very first state emitted by the agent inside the current session,
        we register the agent right here.  That way silent helpers (e.g.
        delegate children that never speak) never show up in
        `session:{cid}:agents`.
        """
        if not states:
            return

        agents_key = f"session:{self.cid}:agents"
        if not self.redis.sismember(agents_key, self.aid):
            self.redis.sadd(agents_key, self.aid)
            self.redis.sadd("active_sessions", self.cid)

        cur = self.current()
        if cur and isinstance(cur.state, FinishedState):
            self.pop(1)

        if len(states) == 1 and isinstance(states[0], FinishedState) and cur and isinstance(cur.state, FinishedState):
            return

        branch_id = self.current_branch()
        key = self._branch_key(branch_id)

        encoded = [json.dumps(encode(s)) for s in states]
        self.r.rpush(key, *encoded)

        ep_key = self._episode_key_tpl.format(branch=branch_id)
        episode_id = _b2s(self.redis.get(ep_key))
        if episode_id is None:
            episode_id = uuid.uuid4().hex[:8]
            self.redis.set(ep_key, episode_id, ex=86_400)
        bus = get_bus()
        rollout_team, rollout_variant = self._get_rollout_provenance()

        for s in states:
            header: ArtifactHeader = {
                "ref": generate_ref(),
                "session_id": self.cid,
                "agent_id": self.aid,
                "branch_id": branch_id,
                "episode_id": episode_id,
                "group_id": group_id,
                "state_id": getattr(s, "id", ""),
                "type": "state",
                "mime": "application/json",
                "ts": current_timestamp(),
                "meta": {
                    "state_cls": type(s).__name__,
                    **(
                        {
                            "team_id": rollout_team,
                            "variant_id": rollout_variant,
                        }
                        if rollout_team or rollout_variant
                        else {}
                    ),
                },
                "parent_refs": [],
            }

            if isinstance(s, FinishedState):
                header["meta"]["is_terminal"] = True

            if isinstance(s, ToolCallState):
                self.redis.hset(f"{self._base_key}:toolcall_ref", s.id, header["ref"])
                self.redis.expire(f"{self._base_key}:toolcall_ref", 86_400)

            elif isinstance(s, ToolResultState):
                p = self.redis.hget(f"{self._base_key}:toolcall_ref", s.tool_call_id)
                if p:
                    header["parent_refs"] = [p]

            if isinstance(s, AgentCallState):
                self.redis.set(
                    f"{self._base_key}:last_agentcall_ref",
                    header["ref"],
                    ex=86_400,
                )
            elif isinstance(s, AgentResultState):
                p = self.redis.hget(f"{self._base_key}:agentcall_ref", s.correlation_id)
                if p:
                    header["parent_refs"] = [p]
                self.redis.expire(f"{self._base_key}:agentcall_ref", 86_400)

            if isinstance(s, AssistantMessageState):
                self.redis.set(
                    f"{self._base_key}:last_assistant_ref",
                    header["ref"],
                    ex=86_400,
                )

            try:
                bus.publish(header, asdict(s))
            except Exception as exc:
                logger.error(
                    {
                        "message": "artifact_publish_failed",
                        "conversation_id": self.cid,
                        "agent_id": self.aid,
                        "error": str(exc),
                    },
                    exc_info=True,
                )

        if self.r.llen(key) > MAX_STACK_LEN:
            self.r.ltrim(key, -MAX_STACK_LEN, -1)

    def pop(self, n: int = 1, branch_id: Optional[str] = None) -> List[BaseState]:
        if n <= 0:
            return []
        key = self._branch_key(branch_id or self.current_branch())
        out: List[BaseState] = []
        for _ in range(n):
            raw = self.redis.rpop(key)
            if raw is None:
                break
            env = json.loads(raw)
            out.append(decode(env))
        if out:
            self.redis.expire(key, 86_400)
        return out

    def at(self, idx: int, branch_id: Optional[str] = None) -> StackEntry:
        raw = self.r.lindex(self._branch_key(branch_id or self.current_branch()), idx)
        if raw is None:
            raise IndexError("stack index out of range")
        env = json.loads(raw)
        return StackEntry(decode(env), env["ts"])

    def current(self, branch_id: Optional[str] = None) -> Optional[StackEntry]:
        try:
            return self.at(-1, branch_id)
        except IndexError:
            return None

    def length(self, branch_id: Optional[str] = None) -> int:
        return self.r.llen(self._branch_key(branch_id or self.current_branch()))

    def iter_last_n(self, n: int) -> Iterable[StackEntry]:
        key = self._branch_key(self.current_branch())
        for raw in self.r.lrange(key, -n, -1):
            env = json.loads(raw)
            yield StackEntry(decode(env), env["ts"])


    def refresh_current_branch(self) -> None:
        self._branch_id = _b2s(self.r.get(self._ptr_key)) or "main"

    def current_branch(self) -> str:
        if self._branch_id is None:
            self.refresh_current_branch()
        return self._branch_id

    def checkout(self, branch_id: str) -> None:
        if not self.r.exists(self._branch_key(branch_id)):
            raise ValueError(f"Branch {branch_id!r} does not exist")
        self.r.set(self._ptr_key, branch_id)
        self._branch_id = branch_id
        logger.info({"message": "Checked out branch", "branch_id": branch_id})

    def fork(self, idx: int) -> str:
        src = self.current_branch()
        dst = uuid.uuid4().hex[:8]
        slice_ = self.r.lrange(self._branch_key(src), 0, idx)
        if slice_:
            self.r.rpush(self._branch_key(dst), *slice_)
        self.checkout(dst)
        self._branch_id = dst
        self.redis.publish(self._ptr_key, dst)
        logger.info({"message": "Forked branch", "from": src, "to": dst})
        return dst


    def get_branch_info(self) -> List[dict]:
        cur = self.current_branch()
        info: List[dict] = []
        for bid in self._all_branch_ids():
            key = self._branch_key(bid)
            length = self.r.llen(key)
            if length:
                last_raw = self.r.lindex(key, -1)
                try:
                    ts_val = json.loads(last_raw)["ts"] if last_raw else None
                except Exception:
                    ts_val = None
            else:
                ts_val = None
            info.append(
                {
                    "branch_id": bid,
                    "length": length,
                    "last_ts": ts_val,
                    "is_current": bid == cur,
                }
            )
        return sorted(info, key=lambda d: d["branch_id"])

    def get_last_assistant_msg(self) -> Optional[str]:
        for entry in self.iter_last_n(100):
            if isinstance(entry.state, AssistantMessageState) and entry.state.content:
                return entry.state.content
        return None

    def get_parent_agent_id(self) -> Optional[str]:
        key = f"child_to_parent:{self.cid}:{self.aid}"
        return _b2s(self.redis.get(key))

    def get_correlation_id(self) -> Optional[str]:
        key = f"agent_call_correlation:{self.cid}:{self.aid}"
        return _b2s(self.redis.get(key))


if not hasattr(InteractionStack, "_stack_key"):

    def _stack_key(self, branch_id: str) -> str:
        return self._branch_key(branch_id)

    InteractionStack._stack_key = _stack_key

if not hasattr(InteractionStack, "_current_ptr_key"):

    def _current_ptr_key(self) -> str:
        return self._ptr_key

    InteractionStack._current_ptr_key = _current_ptr_key

if not hasattr(InteractionStack, "conversation_id"):

    @property
    def conversation_id(self) -> str:
        return self.cid

    InteractionStack.conversation_id = conversation_id
