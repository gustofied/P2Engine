# main.py
import os
import yaml
import argparse
import subprocess
import atexit
import time
import sys
import datetime
from dotenv import load_dotenv
from src.systems.scenario_manager import ScenarioManager
from src.systems.scenario_loader import load_system
from src.custom_logging.central_logger import central_logger
from src.agents.log_analyzer_agent import LogAnalyzerAgent
from src.entities.entity_manager import EntityManager
from src.entities.component_manager import ComponentManager
from celery_app import app as celery_app  # Grab the shared Celery app instance

# Load up those env vars from the .env file (think API keys, broker URLs, etc.)
load_dotenv()

def get_unique_queues(scenario):
    """
    Pulls out unique queue names from the scenario’s task sequence.

    Args:
        scenario (dict): The scenario config with all the task deets.

    Returns:
        set: Unique queue names used in the scenario.
    """
    queues = set()
    # Grab the task sequence, default to empty list if it’s missing
    task_sequence = scenario.get("task_sequence", [])
    for task in task_sequence:
        # Snag the queue name, fall back to "default" if it ain’t there
        queue = task.get("queue", "default")
        queues.add(queue)
    return queues

def start_celery_workers(queues):
    """
    Fires up Celery workers in the background and pipes their output to a timestamped log file.

    Args:
        queues (set): Set of queue names the worker’s gonna listen to.

    Returns:
        subprocess.Popen: Handle to the worker process so we can kill it later.
    """
    # Smash those queue names into a comma-separated string for Celery’s -Q flag
    queue_list = ",".join(queues)
    # Use the same Python as this script to keep the env tight
    python_exe = sys.executable
    # Build the Celery command: run the worker with our queues and info-level logging
    celery_cmd = f"{python_exe} -m celery -A celery_app worker -Q {queue_list} --loglevel=info"
    # Make a dope timestamped log file name (e.g., worker_20250304_123456.log)
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    log_file = os.path.join(os.getcwd(), f"worker_{timestamp}.log")
    # Open the log file and kick off the worker, sending stdout/stderr there
    with open(log_file, "w") as log:
        process = subprocess.Popen(
            celery_cmd,
            shell=True,
            stdout=log,
            stderr=log,
            cwd=os.getcwd()
        )
    # Let you know where the logs are at
    print(f"Started Celery worker for queues: {queue_list}. Logs dropping at {log_file}")
    return process

def format_scenario_log(scenario_log):
    """
    Turns the scenario log into a clean, readable string for analysis.

    Args:
        scenario_log (dict): The log data from the scenario run.

    Returns:
        str: Nice formatted string with all the log goodies.
    """
    if not scenario_log:
        return "No log data available, brah."
    
    # Pull out interactions and format ‘em
    interactions = scenario_log.get("interactions", [])
    interactions_text = "\n".join([
        f"{i['timestamp']} - {i['from']} to {i['to']}: {i['message']}"
        for i in interactions
    ]) if interactions else "No interactions recorded."
    
    # Slam together a full summary
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
    """
    The big kahuna: runs your multi-agent scenario with dynamic Celery workers.

    Handles args, spins up workers, runs the scenario, and drops an HTML summary.
    """
    # Set up the arg parser for command-line vibes
    parser = argparse.ArgumentParser(description="Run a multi-agent scenario with dynamic workers.")
    parser.add_argument("--scenarios", required=True, help="Path to scenarios directory")
    parser.add_argument("--scenario", required=True, help="Name of the scenario to run")
    args = parser.parse_args()

    # Make sure logs flush when we bounce
    atexit.register(central_logger.flush_logs)

    # Load up the scenario you asked for
    manager = ScenarioManager(args.scenarios)
    scenario = manager.get_scenario(args.scenario)

    # Get the queues and fire up the Celery worker
    queues = get_unique_queues(scenario)
    worker_process = start_celery_workers(queues)
    # Chill for 5 secs so the worker can handshake with the broker
    time.sleep(5)

    try:
        # Load and run the scenario system
        system = load_system(scenario)
        result = system.run(**scenario.get("run_params", {}))
        print(f"Scenario done, brah. Result: {result}")

        # Set up the managers and log analyzer
        entity_manager = EntityManager()
        component_manager = ComponentManager()
        analyzer_agent = LogAnalyzerAgent(
            entity_manager=entity_manager,
            component_manager=component_manager,
            api_key=os.getenv("OPENROUTER_API_KEY")
        )

        # Format the logs and cook up an HTML summary
        scenario_log = central_logger.get_logs()
        formatted_log = format_scenario_log(scenario_log)
        prompt = f"Analyze this system log and generate an HTML summary:\n{formatted_log}"
        html_summary = analyzer_agent.interact(prompt)

        # Drop the summary into a file
        with open("summary.html", "w") as f:
            f.write(html_summary)
        print("Generated HTML Summary:\n", html_summary)
        print("Summary saved to summary.html, check it out!")

    except Exception as e:
        # Catch any screw-ups and let you know
        print(f"Error, brah: {e}")
    finally:
        # Kill the worker when we’re done
        if worker_process:
            worker_process.terminate()
            print("Shut down the Celery worker process")

if __name__ == "__main__":
    main()