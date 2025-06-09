import redis

from infra.config_loader import settings


def get_redis():
    return redis.Redis(
        host=settings().redis.host,
        port=settings().redis.port,
        db=settings().redis.db,
        decode_responses=True,
    )
