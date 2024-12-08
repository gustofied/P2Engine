# config.py
import os

# API keys and settings
API_KEY = os.getenv('XRPSCAN_API_KEY', 'your_api_key_here')
EMBEDDING_MODEL = 'azure_openai_embedding_model_name'
SIMILARITY_THRESHOLD = 0.7