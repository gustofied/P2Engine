import uuid
from integrations.llm.llm_client import LLMClient
from custom_logging.litellm_logger import my_custom_logging_fn
from custom_logging.central_logger import central_logger

# --- Behavior Functions (Mixins) ---

def default_format_messages(user_input):
    """Default behavior: format messages with a generic prompt."""
    return [
        {"role": "system", "content": "You are a helpful assistant."},
        {"role": "user", "content": user_input}
    ]

def default_use_tool(user_input, tools):
    """
    Default tool usage behavior:
    If the input contains "calculate" and 'calculator' is available,
    perform a simple arithmetic evaluation.
    """
    if "calculate" in user_input.lower() and "calculator" in tools:
        calc_input = user_input.lower().split("calculate")[-1].strip()
        # Allow only digits and basic math operators.
        calc_input = "".join(c for c in calc_input if c.isdigit() or c in "+-*/()")
        try:
            result = eval(calc_input)
            return str(result)
        except Exception as e:
            return f"Error using calculator: {str(e)}"
    return None

# --- Composable Agent Class ---

class ComposableAgent:
    def __init__(self, name, llm_client, behaviors=None, tools=None):
        self.id = str(uuid.uuid4())
        self.name = name
        self.llm = llm_client
        # behaviors: a dict mapping behavior names to functions.
        self.behaviors = behaviors or {}
        self.tools = tools or []

    def format_messages(self, user_input):
        formatter = self.behaviors.get("format_messages", default_format_messages)
        return formatter(user_input)

    def use_tool(self, user_input):
        tool_fn = self.behaviors.get("use_tool", default_use_tool)
        return tool_fn(user_input, self.tools)

    def interact(self, user_input):
        # First, check if a tool can handle the input.
        tool_output = self.use_tool(user_input)
        if tool_output is not None:
            central_logger.log_interaction(self.name, "Tool", f"Tool output: {tool_output}")
            return tool_output

        # Otherwise, format the message and query the LLM.
        messages = self.format_messages(user_input)
        response = self.llm.query(
            messages=messages,
            metadata={"agent_name": self.name, "agent_id": self.id}
        )
        central_logger.log_interaction(self.name, "LLM", f"LLM response: {response}")
        return response

# --- Agent Factory for Dynamic Spawning ---

class AgentFactory:
    def __init__(self, llm_client_factory):
        """
        llm_client_factory: a function that takes (model, api_key)
        and returns an LLMClient instance.
        """
        self.llm_client_factory = llm_client_factory

    def create_agent(self, name, model="gpt-3.5-turbo", api_key=None, behaviors=None, tools=None):
        llm_client = self.llm_client_factory(model, api_key)
        return ComposableAgent(name=name, llm_client=llm_client, behaviors=behaviors, tools=tools)

    def spawn_agent_from_config(self, config):
        """
        Create an agent from a configuration dict.
        Expected keys: name, model, api_key, behaviors, tools.
        """
        return self.create_agent(
            name=config.get("name", "UnnamedAgent"),
            model=config.get("model", "gpt-3.5-turbo"),
            api_key=config.get("api_key"),
            behaviors=config.get("behaviors"),
            tools=config.get("tools", [])
        )

def default_llm_client_factory(model, api_key):
    # Uses your existing LLMClient implementation.
    return LLMClient(model=model, api_key=api_key, logger_fn=my_custom_logging_fn)

# --- Example Usage (for manual testing) ---

if __name__ == "__main__":
    factory = AgentFactory(default_llm_client_factory)

    # Create a simple agent that can use a calculator.
    simple_agent = factory.create_agent(
        name="SimpleAgent",
        model="gpt-3.5-turbo",
        api_key="your_api_key_here",  # Replace with a valid API key.
        tools=["calculator"]
    )
    print("SimpleAgent response:", simple_agent.interact("Calculate 3+4"))

    # Create a critic agent with a custom message formatter.
    critic_config = {
        "name": "CriticAgent",
        "model": "gpt-4",
        "api_key": "your_api_key_here",
        "behaviors": {
            "format_messages": lambda msg: [
                {"role": "system", "content": "You are a critic analyzing the conversation."},
                {"role": "user", "content": msg}
            ]
        },
        "tools": []
    }
    critic_agent = factory.spawn_agent_from_config(critic_config)
    print("CriticAgent response:", critic_agent.interact("What improvements are needed?"))
