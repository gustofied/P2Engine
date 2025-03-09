from celery import Celery
import os
from dotenv import load_dotenv
from src.custom_logging.central_logger import central_logger

load_dotenv()

BROKER_URL = os.environ.get("CELERY_BROKER_URL", "amqp://guest:guest@localhost:5672//")
RESULT_BACKEND = os.environ.get("CELERY_RESULT_BACKEND", "redis://localhost:6379/0")

app = Celery(
    "multi_agent_system",
    broker=BROKER_URL,
    backend=RESULT_BACKEND,
)

app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    worker_concurrency=4,
    include=[
        "src.tasks.task_registry",
        "src.agents.states_advanced",
        "src.integrations.tools",
    ],
    # Removed task_queues to allow dynamic queues
)

# Log configuration
central_logger.log_interaction("Celery", "System", f"Broker: {BROKER_URL}")
central_logger.log_interaction("Celery", "System", f"Result Backend: {RESULT_BACKEND}")
central_logger.log_interaction("Celery", "System", f"Registered tasks: {app.conf.include}")