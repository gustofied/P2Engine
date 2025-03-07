# src/utils.py
import subprocess
import sys
import os
import datetime

def start_celery_workers(queues):
    """
    Start a Celery worker for the specified queues.
    
    Args:
        queues (set): Set of queue names to listen to.
    
    Returns:
        subprocess.Popen: The process object for the started worker.
    """
    queue_list = ",".join(queues)
    python_exe = sys.executable
    celery_cmd = f"{python_exe} -m celery -A celery_app worker -Q {queue_list} --loglevel=info"
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    log_file = os.path.join(os.getcwd(), f"worker_{timestamp}.log")
    with open(log_file, "w") as log:
        process = subprocess.Popen(
            celery_cmd,
            shell=True,
            stdout=log,
            stderr=log,
            cwd=os.getcwd()
        )
    print(f"Started Celery worker for queues: {queue_list}. Logs at {log_file}")
    return process