TRANSITIONS = {
    ("UserMessage", "UserMessageEvent"): "AssistantMessage",
    ("AssistantMessage", "ResponseReadyEvent"): "Finished",
    ("AssistantMessage", "ClarificationEvent"): "ClarificationState",
    ("AssistantMessage", "ToolCallEvent"): "ToolCall",  # Already present
    ("AssistantMessage", "AgentCallEvent"): "AgentCall",
    ("ClarificationState", "UserMessageEvent"): "AssistantMessage",
    ("ToolCall", "ToolResultEvent"): "ToolResult",
    ("ToolCall", "ToolFailureEvent"): "ToolFailureState",
    ("WaitingForToolResult", "ToolResultEvent"): "ToolResult",
    ("WaitingForToolResult", "TimeoutEvent"): "TimeoutState",
    ("AgentCall", "AgentResultEvent"): "AgentResult",
    ("WaitingForAgentResult", "AgentResultEvent"): "AgentResult",
    ("WaitingForAgentResult", "TimeoutEvent"): "TimeoutState",
    ("ToolFailureState", "RetryEvent"): "AssistantMessage",
    ("ToolFailureState", "TimeoutEvent"): "TimeoutState",
    ("AgentFailureState", "RetryEvent"): "AssistantMessage",
    ("AgentFailureState", "TimeoutEvent"): "TimeoutState",
}