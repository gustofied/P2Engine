import pytest
from single_agents.composable_agent import ComposableAgent, AgentFactory, default_llm_client_factory

# Dummy LLM client for testing.
class DummyLLMClient:
    def __init__(self, model, api_key, logger_fn):
        self.model = model
        self.api_key = api_key
        self.logger_fn = logger_fn

    def query(self, messages, metadata):
        # Simply return the user input for testing purposes.
        for m in messages:
            if m["role"] == "user":
                return f"Echo: {m['content']}"
        return "No input"

def dummy_llm_client_factory(model, api_key):
    return DummyLLMClient(model, api_key, None)

def test_composable_agent_tool_usage():
    agent = ComposableAgent(
        name="TestAgent",
        llm_client=dummy_llm_client_factory("dummy", None),
        tools=["calculator"]
    )
    # Test that the tool handles arithmetic.
    response = agent.interact("Calculate 10+5")
    assert response == "15"

def test_composable_agent_default_behavior():
    agent = ComposableAgent(
        name="TestAgent",
        llm_client=dummy_llm_client_factory("dummy", None),
        tools=[]
    )
    response = agent.interact("Hello")
    assert response == "Echo: Hello"

def test_agent_factory_spawn():
    factory = AgentFactory(dummy_llm_client_factory)
    config = {
        "name": "SpawnedAgent",
        "model": "dummy",
        "api_key": None,
        "behaviors": {
            "format_messages": lambda msg: [
                {"role": "system", "content": "Custom prompt."},
                {"role": "user", "content": msg}
            ]
        },
        "tools": []
    }
    agent = factory.spawn_agent_from_config(config)
    response = agent.interact("Test message")
    assert response == "Echo: Test message"

if __name__ == "__main__":
    pytest.main(["-v"])
