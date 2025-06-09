import select
import sys
import time as _t
import uuid
from dataclasses import dataclass

from cli.utils.compat import get_redis
from infra.logging.logging_config import logger
from infra.session import get_session
from orchestrator.interactions.states.assistant_message import AssistantMessageState
from orchestrator.interactions.states.finished import FinishedState
from orchestrator.interactions.states.tool_call import ToolCallState
from orchestrator.interactions.states.tool_result import ToolResultState
from orchestrator.interactions.states.user_message import UserMessageState
from orchestrator.interactions.states.user_response import UserResponseState
from runtime.tasks.tasks import enqueue_session_tick


@dataclass
class ConversationStarted:
    conv_id: str
    agent_id: str


# TTL for CLI flag
CLI_FLAG_TTL = 3600


def start_chat(engine, agent_id: str, conv_name: str) -> ConversationStarted:
    """Start a new conversation with an agent."""
    r = get_redis(engine)

    # Create new conversation ID
    conv_id = f"chat_{uuid.uuid4()}"

    # Store conversation metadata
    r.set(f"conversation:{conv_name}:id", conv_id)
    r.set(f"conversation:{conv_name}:agent_id", agent_id)
    r.set(f"conversation:{conv_id}:delivery", "ticked")
    r.set(f"conversation:{conv_name}:delivery", "ticked")

    # Mark as CLI conversation
    r.set(f"conversation:{conv_id}:is_cli", "true")
    r.setex(f"conversation:{conv_id}:is_cli", CLI_FLAG_TTL, "true")

    # Initialize session
    session = get_session(conv_id, r)
    session.register_agent(agent_id)

    logger.info(f"Session primed for conversation {conv_id}")

    return ConversationStarted(conv_id, agent_id)


def resume_chat(engine, conv_name: str):
    """Resume an existing conversation."""
    r = get_redis(engine)

    # Get conversation metadata
    conv_id = r.get(f"conversation:{conv_name}:id")
    agent_id = r.get(f"conversation:{conv_name}:agent_id")

    if not conv_id or not agent_id:
        raise ValueError("conversation_not_found")

    # Decode if bytes
    conv_id = conv_id.decode() if isinstance(conv_id, (bytes, bytearray)) else conv_id
    agent_id = agent_id.decode() if isinstance(agent_id, (bytes, bytearray)) else agent_id

    # Restore branch context
    branch_key = f"stack:{conv_id}:{agent_id}:branch"
    current_branch = r.get(branch_key)
    if current_branch:
        current_branch = current_branch.decode() if isinstance(current_branch, bytes) else current_branch
        logger.info(f"Resuming conversation {conv_id} on branch {current_branch}")

    # Set delivery mode
    r.set(f"conversation:{conv_id}:delivery", "ticked")

    # Initialize session
    session = get_session(conv_id, r)
    session.register_agent(agent_id)

    logger.info(f"Session primed for conversation {conv_id}")

    return conv_id, agent_id


def send_user_message(engine, conv_id: str, agent_id: str, text: str):
    """Send a user message in the conversation."""
    r = get_redis(engine)

    # Refresh CLI flag
    r.set(f"conversation:{conv_id}:is_cli", "true")
    r.setex(f"conversation:{conv_id}:is_cli", CLI_FLAG_TTL, "true")

    # Get session and stack
    session = get_session(conv_id, r)
    stack = session.stack_for(agent_id)

    # Check current state
    top_state = stack.current().state if stack.current() else None

    # Handle synthetic seed messages
    if isinstance(top_state, UserMessageState) and top_state.text == "<!-- synthetic seed -->":
        stack.pop()
        top_state = stack.current().state if stack.current() else None

    # Handle child finished messages
    if isinstance(top_state, UserMessageState) and top_state.text == "__child_finished__":
        stack.pop()
        top_state = stack.current().state if stack.current() else None

    # Check if we're waiting for a response
    if isinstance(top_state, UserMessageState):
        # Check if we have any response in the last few entries
        has_response = any(isinstance(e.state, (AssistantMessageState, ToolCallState, ToolResultState)) for e in stack.iter_last_n(3))

        if not has_response:
            print("⚠️  Previous message still pending. Please wait for a response or rewind.")
            return

    # Handle finished state
    if isinstance(top_state, FinishedState):
        new_branch = stack.fork(stack.length() - 1)
        print(f"ℹ️  Previous branch finished; forked to {new_branch}")

    # Push the new message
    stack.push(UserMessageState(text=text))

    # Clear round counter for this branch
    branch_id = stack.current_branch()
    r.delete(f"round_by_branch:{conv_id}:{agent_id}:{branch_id}")

    # Enqueue processing
    enqueue_session_tick(conv_id)


def poll_response(engine, conv_id: str, timeout: int = 60):
    """Poll for assistant response."""
    r = get_redis(engine)
    key = f"response:{conv_id}"

    def _read_once():
        resp = r.get(key)
        if resp:
            r.delete(key)
            # Refresh CLI flag
            r.set(f"conversation:{conv_id}:is_cli", "true")
            r.setex(f"conversation:{conv_id}:is_cli", CLI_FLAG_TTL, "true")
            return resp.decode() if isinstance(resp, (bytes, bytearray)) else resp
        return None

    # Try immediate read
    if (result := _read_once()) is not None or timeout <= 0:
        return result

    # Poll with timeout
    deadline = _t.time() + timeout
    while _t.time() < deadline:
        _t.sleep(0.1)
        if (result := _read_once()) is not None:
            return result

        # Check for user interrupt
        if sys.stdin in select.select([sys.stdin], [], [], 0.0)[0]:
            break

    return None


def inject_user_response(engine, conv_id: str, agent_id: str, text: str):
    """Inject a user response (for user input requests)."""
    r = get_redis(engine)

    session = get_session(conv_id, r)
    stack = session.stack_for(agent_id)

    # Push user response
    stack.push(UserResponseState(text=text))

    # Enqueue processing
    enqueue_session_tick(conv_id)
