import json
import pika
import redis
from celery import Celery

# Initialize Redis
r = redis.Redis(host='localhost', port=6379, db=0)

# Initialize Celery
app = Celery('tasks', broker='pyamqp://guest@localhost//')

# Agent configuration
agent_id = "1"
queue_name = f"agent.{agent_id}.events"

# Set up RabbitMQ connection and queue
connection = pika.BlockingConnection(pika.ConnectionParameters('localhost'))
channel = connection.channel()
channel.queue_declare(queue=queue_name)

# Event handling callback
def callback(ch, method, properties, body):
    message = json.loads(body)
    # Get current state from Redis, default to "Idle" if not set
    state = r.get(f"agent:{agent_id}:state")
    if state is None:
        state = "Idle"
        r.set(f"agent:{agent_id}:state", state)
    state = state.decode('utf-8')  # Redis returns bytes

    if message["type"] == "user_request" and state == "Idle":
        print(f"Received user_request: {message['data']}")
        r.set(f"agent:{agent_id}:state", "Processing")
        # Trigger Celery task
        task = process_request.delay(message["data"], queue_name)
        r.set(f"agent:{agent_id}:task_id", task.id)
        print(f"Started task {task.id}")
    elif message["type"] == "task_complete" and state == "Processing":
        current_task_id = r.get(f"agent:{agent_id}:task_id")
        if current_task_id is not None:
            current_task_id = current_task_id.decode('utf-8')
            if message["task_id"] == current_task_id:
                print(f"Task {message['task_id']} completed with result: {message['result']}")
                r.set(f"agent:{agent_id}:state", "Idle")
                r.delete(f"agent:{agent_id}:task_id")
    else:
        print(f"Ignored message: {message} in state {state}")

# Start consuming events
channel.basic_consume(queue=queue_name, on_message_callback=callback, auto_ack=True)
print(f"Agent {agent_id} is listening on {queue_name}")
try:
    channel.start_consuming()
except KeyboardInterrupt:
    connection.close()
    print("Agent stopped.")