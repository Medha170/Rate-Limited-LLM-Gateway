import logging
from redis.asyncio import Redis, ConnectionError as RedisConnectionError
from app.config import settings

# Get our logger so we can see errors in the console
logger = logging.getLogger("gateway")

async def is_rate_limited(redis_client: Redis, user_id: str) -> bool:
    """
    Checks if a user has exceeded their daily message budget.
    Requirement 2: Accurate under concurrency.
    Requirement 3: Fails open if Redis is down.
    """
    # Create a unique key for each user, e.g., "rate_limit:user123"
    key = f"rate_limit:{user_id}"
    
    try:
        # 1. Atomically increment the user's request count
        current_count = await redis_client.incr(key)
        
        # 2. If this is their first request of the day, set an expiration
        # 86400 seconds = 24 hours
        if current_count == 1:
            await redis_client.expire(key, 86400)
            
        # 3. Check if they went over the daily budget limit
        if current_count > settings.DAILY_REQUEST_LIMIT:
            return True # Yes, they are throttled!
            
        return False # No, they are allowed to proceed
        
    except (RedisConnectionError, Exception) as e:
        # REQUIREMENT 3: FAIL OPEN
        # Log the error so developers can see it, but don't crash the request!
        logger.error(f"⚠️ Redis is DOWN or unreachable: {str(e)}. Failing open to keep service running.")
        return False # Allow the user through since we fail open