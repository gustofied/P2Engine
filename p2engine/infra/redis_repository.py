from typing import List, Optional

import redis

from agents.interfaces import IRepository


class RedisRepository(IRepository):
    def __init__(self, redis_client: redis.Redis):
        self.redis = redis_client

    def set(self, key: str, value: str) -> None:
        self.redis.set(key, value)

    def get(self, key: str) -> Optional[str]:
        result = self.redis.get(key)
        return result if result else None

    def delete(self, key: str) -> None:
        self.redis.delete(key)

    def keys(self, pattern: str) -> List[str]:
        return [key.decode() if isinstance(key, bytes) else key for key in self.redis.keys(pattern)]
