"""
Redis configuration for caching and rate limiting
"""
import redis
from typing import Optional

from app.core.config import settings

# Create Redis connection pool
redis_pool = redis.ConnectionPool.from_url(
    settings.REDIS_URL,
    max_connections=settings.REDIS_MAX_CONNECTIONS,
    decode_responses=True,
)

# Create Redis client
redis_client = redis.Redis(connection_pool=redis_pool)


def get_redis() -> redis.Redis:
    """Get Redis client instance"""
    return redis_client


async def set_cache(key: str, value: str, ttl: int) -> bool:
    """
    Set a value in Redis cache with TTL
    
    Args:
        key: Cache key
        value: Value to cache
        ttl: Time to live in seconds
        
    Returns:
        True if successful, False otherwise
    """
    try:
        redis_client.setex(key, ttl, value)
        return True
    except Exception as e:
        print(f"Redis set error: {e}")
        return False


async def get_cache(key: str) -> Optional[str]:
    """
    Get a value from Redis cache
    
    Args:
        key: Cache key
        
    Returns:
        Cached value or None if not found
    """
    try:
        return redis_client.get(key)
    except Exception as e:
        print(f"Redis get error: {e}")
        return None


async def delete_cache(key: str) -> bool:
    """
    Delete a key from Redis cache
    
    Args:
        key: Cache key
        
    Returns:
        True if successful, False otherwise
    """
    try:
        redis_client.delete(key)
        return True
    except Exception as e:
        print(f"Redis delete error: {e}")
        return False
