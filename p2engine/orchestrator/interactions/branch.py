from __future__ import annotations
import json
import uuid
from typing import TYPE_CHECKING

from infra.logging.logging_config import logger

if TYPE_CHECKING:
    from .stack import InteractionStack


def fork(stack: InteractionStack, idx: int) -> str:
    """Fork the stack at a specific index, creating a new branch."""
    current_branch = stack.current_branch()
    current_key = stack._stack_key(current_branch)
    length = stack.redis.llen(current_key)

    if idx < 0 or idx >= length:
        raise IndexError(f"Index {idx} out of range for branch {current_branch} with length {length}")

    new_branch_id = uuid.uuid4().hex[:8]
    new_key = stack._stack_key(new_branch_id)

    interactions = stack.redis.lrange(current_key, 0, idx)

    pipe = stack.redis.pipeline()
    if interactions:
        pipe.rpush(new_key, *interactions)
        pipe.expire(new_key, 86400) 

    pipe.set(stack._current_ptr_key(), new_branch_id)
    pipe.execute()

    return new_branch_id


def checkout(stack: InteractionStack, branch_id: str) -> None:
    """Switch to a different branch."""
    key = stack._stack_key(branch_id)

    if not stack.redis.exists(key):
        raise ValueError(f"Branch {branch_id} does not exist for conversation {stack.conversation_id}")

    stack.redis.set(stack._current_ptr_key(), branch_id)


def rewind(stack: InteractionStack, idx: int) -> None:
    """Rewind the current branch to a specific index."""
    if idx < 0:
        raise IndexError("Index must be non-negative")

    current_key = stack._stack_key(stack.current_branch())
    length = stack.redis.llen(current_key)

    if idx >= length:
        raise IndexError(f"Index {idx} out of range for branch {stack.current_branch()} with length {length}")

    items_to_remove = stack.redis.lrange(current_key, idx + 1, -1)

    stack.redis.ltrim(current_key, 0, idx)
    stack.redis.expire(current_key, 86400)

    for item in items_to_remove:
        try:
            envelope = json.loads(item)
            state_type = envelope.get("t")

            if state_type == "ToolCallState":
                data = json.loads(envelope["data"])
                tool_call_id = data.get("id")
                if tool_call_id:
                    stack.redis.hdel(f"{stack._base_key}:toolcall_ref", tool_call_id)

        except Exception as exc:
            logger.warning(f"Failed to clean up state during rewind: {exc}")
