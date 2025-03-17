import sys
import os
import time
from src.custom_logging.central_logger import CentralLogger
from src.systems.scenario_manager import ScenarioManager
from src.utils import start_celery_workers
import atexit

def run_scenario(scenarios_dir: str, scenario_name: str) -> None:
    """Run a specified scenario from the scenarios directory."""
    # Initialize the scenario manager
    manager = ScenarioManager(scenarios_dir)
    
    # Load the scenario configuration
    scenario = manager.get_scenario(scenario_name)
    run_id = f"run_{scenario_name}_{int(time.time())}"
    
    # Initialize CentralLogger with run_id
    global central_logger
    central_logger = CentralLogger(run_id=run_id)
    atexit.register(central_logger.flush_logs)  # Register flush_logs on exit
    
    # Define queues for the workers
    queues = {f"agent_queue_{run_id}", f"tool_queue_{run_id}", "default"}
    
    # Start Celery workers dynamically
    worker_process = start_celery_workers(queues, run_id)
    
    # Create the system instance
    system = manager.load_system(scenario_name, run_id=run_id)
    
    # Run the system (handles logging, building, and executing the workflow)
    result = system.run()
    
    print(f"Scenario {scenario_name} completed with result: {result}")
    
    # Clean up by terminating the worker and confirming shutdown
    worker_process.terminate()
    time.sleep(1)  # Give it a moment to shut down
    if worker_process.poll() is None:
        worker_process.kill()  # Force kill if still running
        print(f"Forced termination of worker for {run_id}")
    else:
        print(f"Worker for {run_id} terminated successfully")

if __name__ == "__main__":
    scenarios_dir = "src/scenarios"
    scenario_name = "test_scenario"
    run_scenario(scenarios_dir, scenario_name)