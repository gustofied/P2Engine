# src/integrations/tools/tool_registry.py
from typing import Dict, Type
from .base_tool import Tool  # Assume base_tool.py defines a Tool base class

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