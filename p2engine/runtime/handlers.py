# runtime/handlers.py
from __future__ import annotations

import logging
import time
import uuid
from typing import Callable, Dict, List, Type

from agents.impl.llm_agent import LLMAgent
from agents.interfaces import IAgent
from infra.artifacts.bus import get_bus
from infra.async_utils import run_async
from infra.side_effect_executor import _settle_wait
from infra.utils.session_helpers import current_episode_id
from orchestrator.interactions.render import render_for_llm
from orchestrator.interactions.stack import InteractionStack, StackEntry
from orchestrator.interactions.states.agent_call import AgentCallState
from orchestrator.interactions.states.agent_result import AgentResultState
from orchestrator.interactions.states.assistant_message import AssistantMessageState
from orchestrator.interactions.states.base import BaseState
from orchestrator.interactions.states.finished import FinishedState
from orchestrator.interactions.states.tool_call import ToolCallState
from orchestrator.interactions.states.tool_result import ToolResultState
from orchestrator.interactions.states.user_input_request import UserInputRequestState
from orchestrator.interactions.states.user_message import UserMessageState
from orchestrator.interactions.states.user_response import UserResponseState
from orchestrator.interactions.states.waiting import WaitingState
from orchestrator.schemas.schemas import AskSchema, FunctionCallSchema, ReplySchema
from runtime.constants import MAX_REFLECTIONS, MIN_AGENT_RESPONSE_SEC, TOOL_TIMEOUT_SEC
from runtime.effects import BaseEffect, PublishSystemReply, PushToAgent
from runtime.helpers import mark_finished, materialise_response
from services.services import ServiceContainer

logger = logging.getLogger(__name__)

container = ServiceContainer()
template_manager = container.get_template_manager()

_HANDLERS: Dict[Type[BaseState], Callable] = {}


def handler(state_cls: Type[BaseState]):
    def wrapper(fn):
        _HANDLERS[state_cls] = fn
        return fn

    return wrapper


@handler(UserMessageState)
def handle_user_message(
    entry: StackEntry,
    stack: InteractionStack,
    agent: IAgent,
    conversation_id: str,
    agent_id: str,
) -> List[BaseEffect]:
    ask = AskSchema(history=render_for_llm(stack), conversation_id=conversation_id)
    response = run_async(agent.run(ask))
    return materialise_response(stack, response, conversation_id, agent_id)


@handler(ToolResultState)
def handle_tool_result(
    entry: StackEntry,
    stack: InteractionStack,
    agent: IAgent,
    conversation_id: str,
    agent_id: str,
) -> List[BaseEffect]:
    if entry.state.tool_name == "delegate":
        return []

    ask = AskSchema(history=render_for_llm(stack), conversation_id=conversation_id)
    response = run_async(agent.run(ask))
    effects = materialise_response(stack, response, conversation_id, agent_id)

    tool_name = entry.state.tool_name
    from orchestrator.registries import tool_registry

    tool = tool_registry.get_tool_by_name(tool_name)
    if tool and tool.config.reflect:
        template = template_manager.get_template("reflection/tool.j2")
        reflection_prompt = template.render(
            tool_name=tool_name,
            arguments=entry.state.arguments,
            result=entry.state.result,
        )
        stack.push(UserMessageState(text=reflection_prompt, meta=f"reflection:{tool_name}"))
    return effects


@handler(WaitingState)
def handle_waiting(
    entry: StackEntry,
    stack: InteractionStack,
    agent: IAgent,
    conversation_id: str,
    agent_id: str,
) -> List[BaseEffect]:
    state: WaitingState = entry.state
    if not state.is_expired():
        return []

    if state.kind == "agent" and state.correlation_id:
        guard_key = f"expect_agent_result:{conversation_id}:{agent_id}:{state.correlation_id}"
        if stack.redis.exists(guard_key):
            logger.debug(
                {
                    "message": "Waiting grace window – guard key still live",
                    "conversation_id": conversation_id,
                    "agent_id": agent_id,
                    "correlation_id": state.correlation_id,
                    "deadline": state.deadline,
                }
            )
            return []

    if state.kind == "tool" and state.correlation_id:
        dedup_key = f"dedup:{conversation_id}:{agent_id}:{stack.current_branch()}:{state.correlation_id}"
        stack.redis.delete(dedup_key)

    logger.warning(
        {
            "message": "Timeout while waiting",
            "kind": state.kind,
            "agent_id": agent_id,
            "conversation_id": conversation_id,
            "correlation_id": state.correlation_id,
        }
    )

    if state.kind == "agent":
        timeout_result: BaseState = AgentResultState(
            correlation_id=state.correlation_id,
            result={"status": "timeout", "message": "Agent response timeout"},
        )
    else:
        tool_name = "unknown"
        if state.correlation_id:
            for prev in stack.iter_last_n(50):
                if isinstance(prev.state, ToolCallState) and prev.state.id == state.correlation_id:
                    tool_name = prev.state.function_name
                    break
        timeout_result = ToolResultState(
            tool_call_id=state.correlation_id or "unknown",
            tool_name=tool_name,
            result={
                "status": "timeout",
                "message": "Tool call exceeded the time-out limit",
            },
        )

    stack.pop()
    stack.push(timeout_result)

    if stack.get_parent_agent_id() is None:
        mark_finished(stack)

    return [PublishSystemReply(conversation_id, "")]


@handler(AgentCallState)
def handle_agent_call(
    entry: StackEntry,
    stack: InteractionStack,
    agent: IAgent,
    conversation_id: str,
    agent_id: str,
) -> List[BaseEffect]:
    state: AgentCallState = entry.state

    stack.push(AssistantMessageState(content="Hang on, checking that for you…"))

    correlation_id = uuid.uuid4().hex
    deadline = time.time() + max(TOOL_TIMEOUT_SEC, MIN_AGENT_RESPONSE_SEC, 300)

    stack.redis.set(
        f"child_to_parent:{conversation_id}:{state.agent_id}",
        agent_id,
        ex=86_400,
    )
    stack.redis.set(
        f"agent_call_correlation:{conversation_id}:{state.agent_id}",
        correlation_id,
        ex=86_400,
    )

    stack.push(
        WaitingState(
            kind="agent",
            deadline=deadline,
            correlation_id=correlation_id,
        )
    )

    parent_ref = stack.redis.get(f"stack:{conversation_id}:{agent_id}:last_agentcall_ref")
    if parent_ref:
        stack.redis.hset(
            f"stack:{conversation_id}:{agent_id}:agentcall_ref",
            correlation_id,
            parent_ref,
        )
        stack.redis.delete(f"stack:{conversation_id}:{agent_id}:last_agentcall_ref")

    guard_key = f"expect_agent_result:{conversation_id}:{agent_id}:{correlation_id}"
    ttl = int(deadline - time.time() + 5)
    stack.redis.setex(guard_key, ttl, "1")

    return [
        PushToAgent(
            conversation_id=conversation_id,
            target_agent_id=state.agent_id,
            message=state.message,
            sender_agent_id=agent_id,
            correlation_id=correlation_id,
        )
    ]

@handler(AgentResultState)
def handle_agent_result(
    entry: StackEntry,
    stack: InteractionStack,
    agent: IAgent,
    conversation_id: str,
    agent_id: str,
) -> List[BaseEffect]:
    _settle_wait(stack, entry.state.correlation_id)

    sub_resp = (entry.state.result or {}).get("content", "").strip()
    if sub_resp:
        stack.push(AssistantMessageState(content=sub_resp))
        mark_finished(stack)
        return [PublishSystemReply(conversation_id, sub_resp)]

    history = render_for_llm(stack, exclude_types=[AgentResultState])
    ask = AskSchema(history=history, conversation_id=conversation_id)
    response = run_async(agent.run(ask))

    effects = materialise_response(stack, response, conversation_id, agent_id)
    mark_finished(stack)
    return effects


@handler(FinishedState)
def handle_finished(
    entry: StackEntry,
    stack: InteractionStack,
    agent: IAgent,
    conversation_id: str,
    agent_id: str,
) -> List[BaseEffect]:
    once_key = f"finished_once:{conversation_id}:{agent_id}:{stack.current_branch()}"
    if not stack.redis.setnx(once_key, "1"):
        return []
    stack.redis.expire(once_key, 86_400)

    parent_agent_id: str | None = stack.get_parent_agent_id()
    correlation_id: str | None = stack.get_correlation_id() if parent_agent_id else None

    if parent_agent_id and correlation_id:
        try:
            final_answer = stack.get_last_assistant_msg() or ""
            from runtime.tasks.celery_app import app as celery_app

            celery_app.send_task(
                "runtime.tasks.delegate_bridge.bubble_up_delegate",
                args=[
                    conversation_id,
                    parent_agent_id,
                    agent_id,
                    correlation_id,
                    final_answer,
                ],
                queue="ticks",
            )
        except Exception as exc:
            logger.error(
                {
                    "message": "delegate_bridge_enqueue_failed",
                    "conversation_id": conversation_id,
                    "agent_id": agent_id,
                    "parent_agent_id": parent_agent_id,
                    "error": str(exc),
                },
                exc_info=True,
            )

    try:
        from infra.evals.registry import registry

        judge = registry.get("gpt4_judge")
        bus = get_bus()

        last_ref_key = f"stack:{conversation_id}:{agent_id}:last_assistant_ref"
        target_ref: str | None = stack.redis.get(last_ref_key)
        if not target_ref:
            raise RuntimeError("Unable to locate assistant artefact for judging")

        traj = render_for_llm(stack, last_n=50)

        bus.create_evaluation_for(
            target_ref,
            evaluator_id=judge.id,
            judge_version=judge.version,
            payload={
                "traj": traj,
                "parent_agent_id": parent_agent_id,
                "correlation_id": correlation_id,
                "child_agent_id": agent_id,
            },
        )
    except KeyError:
        logger.error(
            {
                "message": "auto_evaluation_skipped",
                "conversation_id": conversation_id,
                "agent_id": agent_id,
                "error": "evaluator_not_found",
            }
        )
    except Exception as exc:
        logger.error(
            {
                "message": "failed_to_enqueue_evaluation",
                "conversation_id": conversation_id,
                "agent_id": agent_id,
                "error": str(exc),
            },
            exc_info=True,
        )

    if isinstance(agent, LLMAgent):
        cfg = agent.config

        if cfg.enable_self_reflection:
            reflection_count = sum(
                1
                for e in stack.iter_last_n(stack.length())
                if isinstance(e.state, AssistantMessageState) and e.state.meta and e.state.meta.startswith("reflection")
            )
            if reflection_count < MAX_REFLECTIONS:
                last_msg = stack.get_last_assistant_msg() or ""
                template = template_manager.get_template("reflection/self.j2")
                prompt = template.render(response=last_msg)
                stack.push(UserMessageState(text=prompt, meta="reflection"))
                return []

        if cfg.reflection_agent_id:
            last_msg = stack.get_last_assistant_msg() or "No response"
            critique = f"Critique the following response: {last_msg}"
            corr = uuid.uuid4().hex

            stack.push(AgentCallState(agent_id=cfg.reflection_agent_id, message=critique))
            stack.push(
                WaitingState(
                    kind="agent",
                    deadline=time.time() + TOOL_TIMEOUT_SEC,
                    correlation_id=corr,
                )
            )
            return [
                PushToAgent(
                    conversation_id=conversation_id,
                    target_agent_id=cfg.reflection_agent_id,
                    message=critique,
                    sender_agent_id=agent_id,
                    correlation_id=corr,
                )
            ]

    return []


@handler(UserInputRequestState)
def handle_user_input_req(*_) -> List[BaseEffect]:
    return []


@handler(UserResponseState)
def handle_user_response(
    entry: StackEntry,
    stack: InteractionStack,
    agent: IAgent,
    conversation_id: str,
    agent_id: str,
) -> List[BaseEffect]:
    ask = AskSchema(history=render_for_llm(stack), conversation_id=conversation_id)
    response = run_async(agent.run(ask))
    return materialise_response(stack, response, conversation_id, agent_id)
