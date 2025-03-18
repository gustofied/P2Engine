import json
import pika
import redis
from src.celery_app import app as celery_app
from src.components.components import StateComponent, ModelComponent

class EventProcessorSystem:
    def __init__(self, agent_id, queue_name):
        self.agent_id = agent_id
        self.queue_name = queue_name
        self.redis_client = redis.Redis(host='localhost', port=6379, db=0)

    def process_event(self, entity, ch, method, properties, body):
        message = json.loads(body)
        state_comp = entity["components"].get("state")
        model_comp = entity["components"].get("model")

        if message["type"] == "user_request" and state_comp.state == "Idle":
            print(f"Agent {self.agent_id} received user_request: {message['data']}")
            state_comp.state = "Processing"
            self.redis_client.set(f"agent:{self.agent_id}:state", state_comp.state.encode('utf-8'))
            
            model = model_comp.model if model_comp else None
            task = celery_app.send_task('process_request', args=[message["data"], self.queue_name, model])
            self.redis_client.set(f"agent:{self.agent_id}:task_id", task.id.encode('utf-8'))
            print(f"Started task {task.id}")

        elif message["type"] == "task_complete" and state_comp.state == "Processing":
            current_task_id = self.redis_client.get(f"agent:{self.agent_id}:task_id")
            if current_task_id and message["task_id"] == current_task_id.decode('utf-8'):
                print(f"Task {message['task_id']} completed with result: {message['result']}")
                state_comp.state = "Idle"
                self.redis_client.set(f"agent:{self.agent_id}:state", state_comp.state.encode('utf-8'))
                self.redis_client.delete(f"agent:{self.agent_id}:task_id")

        ch.basic_ack(delivery_tag=method.delivery_tag)

    def start(self, entity):
        connection = pika.BlockingConnection(pika.ConnectionParameters('localhost'))
        channel = connection.channel()
        try:
            # Attempt to declare the queue with durable=True
            channel.queue_declare(queue=self.queue_name, durable=True)
        except pika.exceptions.ChannelClosedByBroker as e:
            if "PRECONDITION_FAILED - inequivalent arg 'durable'" in str(e):
                print(f"Queue '{self.queue_name}' exists with different properties. Deleting and recreating...")
                # Reopen the channel since it was closed by the exception
                channel = connection.channel()
                channel.queue_delete(queue=self.queue_name)  # Delete the existing queue
                channel.queue_declare(queue=self.queue_name, durable=True)  # Recreate with durable=True
            else:
                raise  # Re-raise if it's a different error
        channel.basic_qos(prefetch_count=1)
        channel.basic_consume(queue=self.queue_name, on_message_callback=lambda ch, method, props, body: self.process_event(entity, ch, method, props, body))
        print(f"Agent {self.agent_id} listening on {self.queue_name}...")
        channel.start_consuming()