from .tool_registry import ToolRegistry
from .calculator_tool import CalculatorTool
from .web_scraper_tool import WebScraperTool

ToolRegistry.register("calculator", CalculatorTool)
ToolRegistry.register("web_scraper", WebScraperTool)