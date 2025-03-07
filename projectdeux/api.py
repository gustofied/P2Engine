# api.py
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from dotenv import load_dotenv
from src.systems.scenario_manager import ScenarioManager
from src.systems.scenario_loader import load_system
from src.custom_logging.central_logger import central_logger
from src.agents.log_analyzer_agent import LogAnalyzerAgent
from src.entities.entity_manager import EntityManager
from src.entities.component_manager import ComponentManager
import os
import atexit
from fastapi.middleware.cors import CORSMiddleware
import redis
import traceback
import uuid  # Added for run_id generation
from celery_app import app as celery_app  # Import shared Celery app

# Load environment variables
load_dotenv()

# Initialize FastAPI app
app = FastAPI()

# Enable CORS for Svelte frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Define the request model
class ScenarioRequest(BaseModel):
    scenario_name: str
    scenarios_dir: str = "src/scenarios"

def format_scenario_log(scenario_log):
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

@app.get("/list-scenarios")
async def list_scenarios(scenarios_dir: str = "src/scenarios"):
    try:
        manager = ScenarioManager(scenarios_dir)
        scenarios = manager.list_scenarios()
        return {"scenarios": scenarios}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/run-scenario")
async def run_scenario(request: ScenarioRequest):
    try:
        # Generate a unique run_id for this request
        run_id = str(uuid.uuid4())
        
        # Verify Celery result backend
        result_backend = os.environ.get("CELERY_RESULT_BACKEND", "redis://localhost:6379/0")
        print(f"Using RESULT_BACKEND: {result_backend}")

        # Test Redis connectivity
        try:
            r = redis.Redis.from_url(result_backend)
            print(f"Redis ping: {r.ping()}")  # Should print True
        except redis.ConnectionError as e:
            print(f"Redis connection failed: {e}")
            raise HTTPException(status_code=500, detail=f"Redis connection failed: {str(e)}")

        # Register log flushing on exit
        atexit.register(central_logger.flush_logs)

        # Run the scenario with the run_id
        manager = ScenarioManager(request.scenarios_dir)
        scenario = manager.get_scenario(request.scenario_name)
        system = load_system(scenario, run_id=run_id)  # Pass run_id to load_system
        result = system.run(**scenario.get("run_params", {}))
        print(f"Scenario completed. Result: {result}")

        # Initialize analyzer agent
        entity_manager = EntityManager()
        component_manager = ComponentManager()
        analyzer_agent = LogAnalyzerAgent(
            entity_manager=entity_manager,
            component_manager=component_manager,
            api_key=os.getenv("OPENROUTER_API_KEY")
        )

        # Generate HTML summary
        scenario_log = central_logger.get_logs()
        formatted_log = format_scenario_log(scenario_log)
        prompt = f"Analyze this system log and generate an HTML summary:\n{formatted_log}"
        html_summary = analyzer_agent.interact(prompt)

        return {"html_summary": html_summary}

    except Exception as e:
        print(f"Error occurred: {e}")
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Scenario failed: {str(e)}")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000, reload=True)