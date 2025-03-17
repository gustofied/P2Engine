# celery_app.py
import datetime
from celery import Celery
import os
from dotenv import load_dotenv

load_dotenv()

BROKER_URL = os.environ.get("CELERY_BROKER_URL", "amqp://127.0.0.1")
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
        "src.tasks.task_definitions",
        "src.tasks.task_registry",  # Added to register generic_task
        "src.integrations.tools",
        "src.states.advanced",
    ],
    broker_connection_retry_on_startup=True,
)

def log_celery_interaction(sender, receiver, message, run_id=None):
    from src.custom_logging.central_logger import central_logger
    if run_id:
        central_logger.log_interaction(sender, receiver, message, run_id)
    else:
        print(f"[{datetime.datetime.now()}] {sender} -> {receiver}: {message}")

try:
    app.broker_connection().ensure_connection(max_retries=3)
    log_celery_interaction("Celery", "System", "Successfully connected to RabbitMQ", "startup")
except Exception as e:
    log_celery_interaction("Celery", "System", f"Failed to connect to RabbitMQ: {str(e)}", "startup")
    raise

log_celery_interaction("Celery", "System", f"Broker: {BROKER_URL}")
log_celery_interaction("Celery", "System", f"Result Backend: {RESULT_BACKEND}")
log_celery_interaction("Celery", "System", f"Registered tasks: {app.conf.include}")