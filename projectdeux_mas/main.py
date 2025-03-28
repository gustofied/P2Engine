import datetime
import json
import pika
import subprocess
import threading
import time
from src.agents.agent import start_agent
from src.utils.celery_utils import start_celery_workers

def purge_queues():
    """Delete queues after run to prevent accumulation."""
    queues_to_delete = ['agent.1.events', 'celery']
    connection = pika.BlockingConnection(pika.ConnectionParameters('localhost'))
    channel = connection.channel()
    for queue in queues_to_delete:
        try:
            channel.queue_delete(queue=queue)
            print(f"Deleted queue: {queue}")
        except Exception as e:
            print(f"Error deleting queue {queue}: {e}")
    connection.close()

if __name__ == "__main__":
    # Unique run ID for worker naming
    unique_run_id = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
    queues = {"celery"}

    # Start Celery worker in a subprocess
    worker_process = start_celery_workers(queues, unique_run_id)

    # Start the agent in a separate thread
    agent_thread = threading.Thread(target=start_agent)
    agent_thread.start()

    # Wait for agent and worker to initialize
    time.sleep(2)

    # Send test message
    connection = pika.BlockingConnection(pika.ConnectionParameters('localhost'))
    channel = connection.channel()
    queue_name = 'agent.1.events'
    try:
        channel.queue_declare(queue=queue_name, durable=True)
    except pika.exceptions.ChannelClosedByBroker as e:
        if "PRECONDITION_FAILED - inequivalent arg 'durable'" in str(e):
            print(f"Queue '{queue_name}' exists with different properties. Recreating...")
            channel.queue_delete(queue=queue_name)
            channel.queue_declare(queue=queue_name, durable=True)
        else:
            raise
    message = {"type": "user_request", "data": "Tell me a joke."}
    channel.basic_publish(exchange='', routing_key=queue_name, body=json.dumps(message))
    print(f"Sent test message to {queue_name}: {message}")
    connection.close()

    # Keep main thread running
    try:
        print("Running... Press Ctrl+C to stop.")
        agent_thread.join()
    except KeyboardInterrupt:
        print("Shutting down...")
        worker_process.teaimport sys
import asyncio
import threading
from p2mas.systems.ops.logging import setup_logging
from p2mas.config import load_simulation_config
from p2mas.di import DependencyContainer
from p2mas.engine.simulations.base import GenericSimulation
from p2mas.systems.core.orchestration.flow_orchestrator import FlowOrchestrator
from p2mas.utils.event_listeners import CompletionListener

async def run_simulation(container, config):
    loop = asyncio.get_running_loop()
    simulation = GenericSimulation(container, config)
    
    # Setup agents and start their consumption tasks
    await simulation.setup()
    
    # Start the orchestrator as an asyncio task
    orchestrator = FlowOrchestrator(container, config)
    orchestrator_task = asyncio.create_task(orchestrator.run())
    
    # Run the simulation to initiate steps
    expected_completions = await simulation.run()
    
    # Set up completion listener in a separate thread
    completion_event = asyncio.Event()
    listener = CompletionListener(container, set(expected_completions), timeout=120)
    
    def on_completion(_):
        loop.call_soon_threadsafe(completion_event.set)
    
    listener_thread = threading.Thread(target=listener.listen, args=(on_completion,))
    listener_thread.start()
    
    # Wait for completion
    await completion_event.wait()
    
    # Cleanup
    await simulation.teardown()
    orchestrator_task.cancel()
    listener_thread.join()

def main():
    log_dir = sys.argv[1] if len(sys.argv) > 1 else 'logs'
    setup_logging(log_dir=log_dir)
    container = DependencyContainer()
    config = load_simulation_config()
    from p2mas.engine.systems import start_background_systems
    start_background_systems(container)
    asyncio.run(run_simulation(container, config))

if __name__ == "__main__":
    main()rminate()
        purge_queues()
        print("Stopped.")