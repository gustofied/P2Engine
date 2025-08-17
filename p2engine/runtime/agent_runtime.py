from __future__ import annotations

from typing import List, Optional, Tuple

from agents.interfaces import IAgent
from orchestrator.interactions.stack import InteractionStack
from orchestrator.interactions.states.base import BaseState
from orchestrator.interactions.states.user_message import UserMessageState
from runtime.effects import BaseEffect
from runtime.handlers import _HANDLERS


class AgentRuntime:
    """
    Runtime wrapper that lets an agent advance exactly **one** step on its
    interaction-stack and returns any side-effects that should be executed by
    the task-runner.
    """

    _SEED_MARKER = "<!-- synthetic"

    def __init__(
        self,
        agent: IAgent,
        conversation_id: str,
        agent_id: str,
        stack: InteractionStack,
    ) -> None:
        self.agent = agent
        self.conversation_id = conversation_id
        self.agent_id = agent_id
        self.stack = stack

    def step(self) -> Tuple[Optional[BaseState], List[BaseEffect]]:
        """
        Advance the agent by one turn.

        - Strips any leftover synthetic-seed messages that may still be at the
          top of the branch (a corner-case after the refactor).
        - Dispatches to the correct state-handler.
        - Returns a tuple of (ignored_state, effects).
        """
        self._strip_seeds()

        if self.stack.length() == 0:
            return None, []

        cur_entry = self.stack.current()
        if cur_entry is None:
            return None, []

        if self.stack.length() == 1 and not isinstance(cur_entry.state, UserMessageState):
            raise RuntimeError("First state must be UserMessage, found " f"{type(cur_entry.state).__name__}")

        handler = _HANDLERS.get(type(cur_entry.state))
        if handler is None:  
            return None, []

        effects: List[BaseEffect] = handler(
            cur_entry,
            self.stack,
            self.agent,
            self.conversation_id,
            self.agent_id,
        )
        return None, effects


    def _strip_seeds(self) -> None:
        """
        Pops up to two consecutive synthetic-seed messages that may have been
        left on the stack after branch-forks or races.  Safe to call even if
        there are none.
        """
        for _ in range(2):
            cur = self.stack.current()
            if (
                cur
                and isinstance(cur.state, UserMessageState)
                and isinstance(cur.state.text, str)
                and cur.state.text.startswith(self._SEED_MARKER)
            ):
                self.stack.pop()
            else:
                break
