TRANSITIONS = {
    ("UserMessage", None): "AssistantMessage",
    ("AssistantMessage", "ResponseReadyEvent"): "Finished",
    ("AssistantMessage", "ToolCallEvent"): "ToolCall",
    ("ToolCall", None): "WaitingForToolResult",
    ("WaitingForToolResult", "ToolResultEvent"): "ToolResult",
    ("ToolResult", None): "AssistantMessage",
    ("AssistantMessage", "AgentCallEvent"): "AgentCall",
    ("AgentCall", None): "WaitingForAgentResult",
    ("WaitingForAgentResult", "AgentResultEvent"): "AgentResult",
    ("AgentResult", None): "AssistantMessage",
    # Error handling transitions
    ("ToolCall", "ToolFailureEvent"): "ToolFailureState",
    ("AgentCall", "AgentFailureEvent"): "AgentFailureState",
    ("ToolFailureState", "RetryEvent"): "AssistantMessage",
    ("AgentFailureState", "RetryEvent"): "AssistantMessage",
    ("ToolFailureState", "StopEvent"): "Finished",
    ("AgentFailureState", "StopEvent"): "Finished",
    # Clarification transitions
    ("AssistantMessage", "ClarificationEvent"): "ClarificationState",
    ("ClarificationState", "UserMessageEvent"): "AssistantMessage",
}