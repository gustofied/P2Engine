from typing import Dict, Type
from .base_tool import Tool
from .calculator_tool import CalculatorTool

class TestTool(Tool):
    def execute(self, **args):
        return f"Test tool executed with args: {args}"

class ToolRegistry:
    _tools: Dict[str, Type[Tool]] = {}

    @classmethod
    def register(cls, name: str, tool_class: Type[Tool]):
        """Register a tool by name."""
        cls._tools[name] = tool_class

    @classmethod
    def get(cls, name: str) -> Type[Tool]:
        """Get a tool class by name."""
        return cls._tools.get(name)

    @classmethod
    def list_tools(cls) -> list:
        """List all registered tool names."""
        return list(cls._tools.keys())

# Register tools at module load
ToolRegistry.register("calculator", CalculatorTool)
ToolRegistry.register("test_tool", TestTool)