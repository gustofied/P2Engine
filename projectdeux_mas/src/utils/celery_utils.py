import subprocess
import sys
import os
import datetime
import time
from src.utils.logging import central_logger

logger = central_logger

def start_celery_workers(queues, unique_run_id):
    """
    Start a Celery worker for the specified queues with a unique node name.
    
    Args:
        queues (set): Set of queue names to listen to (e.g., {"celery"}).
        unique_run_id (str): Unique identifier for the test run to ensure unique worker names.
    
    Returns:
        subprocess.Popen: The process object for the started worker.
    
    Raises:
        RuntimeError: If the worker fails to start after 3 attempts.
    """
    queue_list = ",".join(queues)
    python_exe = sys.executable
    celery_cmd = f"{python_exe} -m celery -A src.celery_app worker -Q {queue_list} --loglevel=info -n worker_{unique_run_id}@%h"
    log_file = os.path.join(os.getcwd(), f"worker_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.log")
    
    for attempt in range(3):
        try:
            with open(log_file, "w") as log:
                process = subprocess.Popen(celery_cmd, shell=True, stdout=log, stderr=log, cwd=os.getcwd())
            time.sleep(2)
            if process.poll() is None:
                print(f"Started Celery worker: {queue_list}")
                logger.log_interaction("Utils", "CeleryWorker", f"Started worker for queues {queue_list}", unique_run_id)
                return process
            print(f"Worker failed attempt {attempt + 1}. Retrying...")
            logger.log_error("Utils", f"Worker failed attempt {attempt + 1}", unique_run_id)
        except Exception as e:
            print(f"Error starting worker: {e}")
            logger.log_error("Utils", str(e), unique_run_id, context={"action": "start_celery_workers"})
        time.sleep(2)
    raise RuntimeError(f"Failed to start Celery worker after 3 attempts. Check {log_file}")