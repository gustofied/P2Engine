# src/redis_client.py
import redis
from src.config import RESULT_BACKEND  # Absolute import
try:
    redis_client = redis.Redis.from_url(RESULT_BACKEND)
    redis_client.ping()  # Test connection
except redis.ConnectionError as e:
    print(f"Failed to connect to Redis at {RESULT_BACKEND}: {e}")
    raise