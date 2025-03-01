import os
from celery import Celery
from src.entities.entity_manager import EntityManager

BROKER_URL = os.environ.get("CELERY_BROKER_URL", "amqp://guest:guest@localhost:5672//")
RESULT_BACKEND = os.environ.get("CELERY_RESULT_BACKEND", "rpc://")

app = Celery(
    "multi_agent_system",
    broker=BROKER_URL,
    backend=RESULT_BACKEND,
)

# Global EntityManager (simplified; ideally use dependency injection in production)
entity_manager = EntityManager()

app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    worker_concurrency=4,
    include=["src.tasks.celery_tasks"]
)