from openai import OpenAI
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

client = OpenAI(api_key='KEY')

def generate_embeddings_batch(texts, batch_size=10):
    embeddings = []
    for i in range(0, len(texts), batch_size):
        batch = texts[i:i + batch_size]
        try:
            response = client.embeddings.create(model="text-embedding-3-large", input=batch)
            embeddings.extend([item.embedding for item in response.data])
        except Exception as e:
            logger.error(f"Embedding generation failed: {e}")
    return embeddings