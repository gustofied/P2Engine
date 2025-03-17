import json
import pika
from celery import Celery
import litellm

app = Celery('tasks', broker='pyamqp://guest@localhost//')

def publish_task_complete(queue, task_id, result):
    connection = pika.BlockingConnection(pika.ConnectionParameters('localhost'))
    channel = connection.channel()
    channel.queue_declare(queue=queue)
    message = {"type": "task_complete", "task_id": task_id, "result": result}
    channel.basic_publish(exchange='', routing_key=queue, body=json.dumps(message))
    connection.close()

@app.task(bind=True)
def process_request(self, request_data, agent_event_queue):
    task_id = self.request.id
    prompt = request_data  # Assume request_data is a string prompt
    try:
        # Generate response with LiteLLM (configure with your API key if needed)
        response = litellm.completion(
            model="gpt-3.5-turbo",  # Adjust model as needed
            messages=[{"role": "user", "content": prompt}]
        ).choices[0].message.content
    except Exception as e:
        response = f"Error generating response: {str(e)}"
    publish_task_complete(agent_event_queue, task_id, response)