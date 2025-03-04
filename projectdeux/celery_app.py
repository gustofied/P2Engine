# celery_app.py
from celery import Celery
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configuration from environment variables
BROKER_URL = os.environ.get("CELERY_BROKER_URL", "amqp://guest:guest@localhost:5672//")
RESULT_BACKEND = os.environ.get("CELERY_RESULT_BACKEND", "redis://localhost:6379/0")

# Initialize the Celery app
app = Celery(
    "multi_agent_system",
    broker=BROKER_URL,
    backend=RESULT_BACKEND,
)

# Update Celery configuration
app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    worker_concurrency=4,
    include=["src.tasks.task_registry"],  # Ensure tasks are registered
)

# Debugging: Print configuration
print(f"Broker: {BROKER_URL}")
print(f"Result Backend: {RESULT_BACKEND}")