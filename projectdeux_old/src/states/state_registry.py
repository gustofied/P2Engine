import yaml
from importlib import import_module

class StateRegistry:
    def __init__(self, config_path: str):
        """Initialize with a config path to load states and tools from YAML."""
        with open(config_path, 'r') as file:
            self.config = yaml.safe_load(file)
        self.states = {}
        self.tools = {}
        self._load_states()
        self._load_tools()

    def _load_states(self):
        """Dynamically import state classes from the YAML config."""
        for state in self.config.get('states', []):
            module_name, class_name = state['class'].rsplit('.', 1)
            module = import_module(module_name)
            state_class = getattr(module, class_name)
            self.states[state['name']] = state_class

    def _load_tools(self):
        """Dynamically import tool classes from the YAML config."""
        for tool in self.config.get('tools', []):
            module_name, class_name = tool['class'].rsplit('.', 1)
            module = import_module(module_name)
            tool_class = getattr(module, class_name)
            self.tools[tool['name']] = tool_class

    def get_state_class(self, state_name: str):
        """Retrieve a state class by name."""
        state_class = self.states.get(state_name)
        if not state_class:
            raise ValueError(f"State '{state_name}' not found in registry.")
        return state_class

    def get_tool_class(self, tool_name: str):
        """Retrieve a tool class by name."""
        tool_class = self.tools.get(tool_name)
        if not tool_class:
            raise ValueError(f"Tool '{tool_name}' not found in registry.")
        return tool_class