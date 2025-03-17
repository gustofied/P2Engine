# src/redis_client.py
from config import RESULT_BACKEND
import redis

try:
    redis_client = redis.Redis.from_url(RESULT_BACKEND)
    redis_client.ping()  # Test connection
except redis.ConnectionError as e:
    print(f"Failed to connect to Redis at {RESULT_BACKEND}: {e}")
    raise