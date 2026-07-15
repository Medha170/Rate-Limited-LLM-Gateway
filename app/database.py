import logging
from redis.asyncio import Redis
from app.config import settings

logger = logging.getLogger("gateway")

# This will hold our active connection pool
redis_client: Redis = None

def get_redis_client() -> Redis:
    """
    Returns the global Redis client.
    """
    global redis_client
    if redis_client is None:
        # Connect to Redis using host and port from config
        redis_client = Redis(
            host=settings.REDIS_HOST,
            port=settings.REDIS_PORT,
            decode_responses=True # This ensures data comes back as strings instead of raw bytes
        )
    return redis_client