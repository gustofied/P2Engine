from typing import Dict, Type
from .base_tool import Tool
from .calculator_tool import CalculatorTool
from .web_scraper_tool import WebScraperTool

class TestTool(Tool):
    def execute(self, **args):
        """Execute a test tool with given arguments."""
        return f"Test tool executed with args: {args}"

class ToolRegistry:
    _tools: Dict[str, Type[Tool]] = {}

    @classmethod
    def register(cls, name: str, tool_class: Type[Tool]):
        """Register a tool with a given name."""
        cls._tools[name] = tool_class

    @classmethod
    def get(cls, name: str) -> Type[Tool]:
        """Retrieve a tool class by name."""
        return cls._tools.get(name)

    @classmethod
    def list_tools(cls) -> list:
        """List all registered tool names."""
        return list(cls._tools.keys())

# Register tools at module load
ToolRegistry.register("calculator", CalculatorTool)
ToolRegistry.register("web_scraper", WebScraperTool)
ToolRegistry.register("test_tool", TestTool)