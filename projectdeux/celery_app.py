from src.tasks.task_registry import TASK_REGISTRY  # Import the task registry
import os
from celery import Celery
from src.entities.entity_manager import EntityManager

# Configuration from environment variables
BROKER_URL = os.environ.get("CELERY_BROKER_URL", "amqp://guest:guest@localhost:5672//")
RESULT_BACKEND = os.environ.get("CELERY_RESULT_BACKEND", "redis://localhost:6379/0")

# Initialize the Celery app
app = Celery(
    "multi_agent_system",
    broker=BROKER_URL,
    backend=RESULT_BACKEND,
)

# Global EntityManager (simplified; consider dependency injection for production)
entity_manager = EntityManager()

# Update Celery configuration
app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    worker_concurrency=4,
    include=["src.tasks.task_registry"],  # Point to where tasks are defined
)

# Optionally, import tasks explicitly to ensure they’re registered
# from src.tasks.task_registry import tell_joke, react_to_jokes, evaluate_jokes