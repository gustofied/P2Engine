# src/integrations/tools/calculator_tool.py
from .base_tool import Tool

class CalculatorTool(Tool):
    def execute(self, expression: str):
        return str(eval(expression))  # Simple evaluation for testing; use cautiously in production