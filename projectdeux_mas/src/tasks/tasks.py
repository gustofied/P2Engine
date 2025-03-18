import json
import pika
from src.celery_app import app
from src.utils.llm_client import LLMClient

def publish_task_complete(queue, task_id, result):
    connection = pika.BlockingConnection(pika.ConnectionParameters('localhost'))
    channel = connection.channel()
    channel.queue_declare(queue=queue, durable=True)
    message = {"type": "task_complete", "task_id": task_id, "result": result}
    channel.basic_publish(exchange='', routing_key=queue, body=json.dumps(message))
    connection.close()

@app.task(bind=True)
def process_request(self, request_data, agent_event_queue, model=None):
    task_id = self.request.id
    print(f"Task {task_id} started with data: {request_data}")
    prompt = request_data
    try:
        llm_client = LLMClient(model=model) if model else LLMClient()
        print(f"Querying LLM with model: {llm_client.model}")
        messages = [{"role": "user", "content": prompt}]
        response = llm_client.query(messages)
        print(f"Task {task_id} got response: {response}")
    except Exception as e:
        response = f"Error generating response: {str(e)}"
        print(f"Task {task_id} failed: {response}")
    publish_task_complete(agent_event_queue, task_id, response)
    print(f"Task {task_id} published task_complete")