from .base_agent import BaseAgent
import os
from dotenv import load_dotenv

load_dotenv()  # Load .env at the module level

class LogAnalyzerAgent(BaseAgent):
    def __init__(self, entity_manager, component_manager, name="LogAnalyzer", model="openrouter/google/gemini-2.0-flash-001", api_key=None):
        """
        Initialize the LogAnalyzerAgent with an enhanced system prompt for generating detailed HTML summaries of system logs,
        including an article that presents only the final result from the log, along with comprehensive run details and a D3.js visualization.
        
        Args:
            entity_manager: Manager for entity data
            component_manager: Manager for component data
            name: Name of the agent (default: "LogAnalyzer")
            model: Model to use for analysis (default: "openrouter/google/gemini-2.0-flash-001")
            api_key: API key for the model (default: None, falls back to OPENROUTER_API_KEY from .env)
        """
        # Use provided api_key, fallback to .env
        api_key = api_key or os.getenv("OPENROUTER_API_KEY")
        if not api_key:
            raise ValueError("No API key provided and OPENROUTER_API_KEY not found in environment.")

        system_prompt = (
            "You are a log analysis specialist tasked with creating a visually appealing and detailed HTML summary of system logs. "
            "Your output must include:\n"
             "- A section with the resulting content, aka the result from the multi agent flow, what it resulted in. you have to trasnform into normal text\n"
            "- A header with the system name, execution time, and detailed run information (e.g., time spent, tasks executed, evaluation metrics).\n"
            "- A comprehensive narrative article that explains the final result from the log. Use the final 'result' field (which contains a 'final_result' array) to build an article with sections for a discussion summary, key messages (with sender, timestamp, and message), metadata (such as goal and problem), and agent interactions.\n"
            "- A section summarizing the system’s purpose or goal.\n"
            "- A section highlighting key events or interactions from the log, formatted clearly (using lists, paragraphs, etc.).\n"
            "- A section indicating the result or status with a styled indicator (e.g., a badge).\n"
            "- A 'Data Visualization' section featuring an SVG element (with id='visualization') for a D3.js graph. Use data derived from the log (such as interactions per agent) to create a suitable chart.\n"
            "- Use modern inline CSS for styling, including appealing colors, readable fonts (such as Arial), proper spacing, and a clean layout.\n"
            "- Include a <script> tag linking to 'https://d3js.org/d3.v7.min.js'.\n"
            "- Include another <script> tag containing D3.js code that extracts relevant data from the log and renders the visualization with labeled axes or legends as needed.\n"
            "- Ensure the entire HTML output is self-contained within a single <div class='playground-llm'></div>.\n"
            "Return only the raw HTML code without any additional text, comments, or formatting."
        )
        super().__init__(
            entity_manager=entity_manager,
            component_manager=component_manager,
            name=name,
            model=model,
            api_key=api_key,  # Pass the resolved api_key explicitly
            system_prompt=system_prompt
        )