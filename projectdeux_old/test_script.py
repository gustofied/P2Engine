import sys
from src.tasks.task_definitions import add  # Import task from its definition module
from src.utils import start_celery_workers  # Import the utility function

def test_celery():
    """Test the Celery setup by running a simple addition task.

    Returns:
        bool: True if the test passes, False otherwise.
    """
    try:
        result = add.delay(2, 3)  # Send task to the default queue
        return result.get(timeout=10) == 5
    except Exception as e:
        print(f"Celery task failed: {e}")
        return False

def run_tests():
    """Run the Celery test suite with a worker process."""
    print("Starting tests...")

    # Define queues and unique run ID
    queues = {"default"}  # Adjust if your tasks use a different queue
    run_id = "test_run_" + str(int(time.time()))  # Unique run ID based on timestamp

    # Start Celery worker using the utility function
    worker_process = start_celery_workers(queues, run_id)

    # Check if worker started successfully
    if worker_process.poll() is not None:
        print(f"Worker failed to start. Check logs at worker_{run_id}.log")
        worker_process.terminate()
        sys.exit(1)

    # Run the Celery test
    if not test_celery():
        print("Celery test failed.")
        worker_process.terminate()
        sys.exit(1)

    # Gracefully terminate the worker
    worker_process.terminate()
    print("All tests passed successfully.")

if __name__ == "__main__":
    import time  # Imported at top level for use in run_id
    run_tests()