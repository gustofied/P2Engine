import argparse
import atexit
import os
from dotenv import load_dotenv
from src.systems.scenario_manager import ScenarioManager
from src.systems.scenario_loader import load_system
from src.custom_logging.central_logger import central_logger
from src.agents.log_analyzer_agent import LogAnalyzerAgent
from src.entities.entity_manager import EntityManager
from src.entities.component_manager import ComponentManager
from celery_app import app as celery_app  # Import the Celery app

# Load environment variables from .env file
load_dotenv()

def format_scenario_log(scenario_log):
    """Format a scenario log into a string for analysis.

    This function concatenates key information and interactions from the scenario log.
    The agent is expected to extract the 'result' field and present it in a user-friendly article format.

    Args:
        scenario_log (dict): The log data to format.

    Returns:
        str: A formatted string representation of the scenario log.
    """
    if not scenario_log:
        return "No log data available."
    
    interactions = scenario_log.get("interactions", [])
    interactions_text = "\n".join([
        f"{i['timestamp']} - {i['from']} to {i['to']}: {i['message']}"
        for i in interactions
    ]) if interactions else "No interactions recorded."
    
    return f"""
System Name: {scenario_log.get('system_name', 'Unknown')}
Start Time: {scenario_log.get('start_time', 'N/A')}
Problem: {scenario_log.get('problem', 'N/A')}
Goal: {scenario_log.get('goal', 'N/A')}
Expected Result: {scenario_log.get('expected_result', 'N/A')}
Interactions:
{interactions_text}
Result: {scenario_log.get('result', 'N/A')}
Time Spent: {scenario_log.get('time_spent', 'N/A')} seconds
Evaluation: {scenario_log.get('evaluation', 'N/A')}
Reward: {scenario_log.get('reward', 'N/A')}
    """.strip()

def main():
    # Parse command-line arguments
    parser = argparse.ArgumentParser(description="Run a multi-agent scenario and generate a summary.")
    parser.add_argument("--scenarios", required=True, help="Path to scenarios directory")
    parser.add_argument("--scenario", required=True, help="Name of the scenario to run")
    args = parser.parse_args()

    # Register log flushing on exit
    atexit.register(central_logger.flush_logs)

    # Run the scenario
    manager = ScenarioManager(args.scenarios)
    scenario = manager.get_scenario(args.scenario)
    system = load_system(scenario)
    result = system.run(**scenario.get("run_params", {}))
    print("Scenario completed. Result:", result)

    # Initialize the LogAnalyzerAgent
    entity_manager = EntityManager()
    component_manager = ComponentManager()
    analyzer_agent = LogAnalyzerAgent(
        entity_manager=entity_manager,
        component_manager=component_manager,
        api_key=os.getenv("DEEPSEEK_API_KEY")
    )

    # Get and format the latest log
    scenario_log = central_logger.get_logs()
    formatted_log = format_scenario_log(scenario_log)

    # Generate HTML summary using the agent
    prompt = f"Analyze this system log and generate an HTML summary:\n{formatted_log}"
    html_summary = analyzer_agent.interact(prompt)

    # Save and display the HTML summary
    with open("summary.html", "w") as f:
        f.write(html_summary)
    print("Generated HTML Summary:\n", html_summary)
    print("Summary saved to summary.html")

if __name__ == "__main__":
    main()