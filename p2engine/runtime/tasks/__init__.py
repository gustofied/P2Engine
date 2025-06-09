from importlib import import_module

# keep explicit imports so Celery discovers every task module
import_module("runtime.tasks.tasks")
import_module("runtime.tasks.evals")
import_module("runtime.tasks.delegate_bridge")
import_module("runtime.tasks.rollout_tasks")
