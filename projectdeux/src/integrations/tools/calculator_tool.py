from .base_tool import Tool

class CalculatorTool(Tool):
    def execute(self, expression: str):
        """Evaluate the given mathematical expression."""
        try:
            result = eval(expression)
            return str(result)
        except Exception as e:
            return f"Error in calculation: {str(e)}"