"""
Rate limiting service using Redis

This module provides rate limiting functionality to prevent abuse by enforcing
hourly and daily request limits per user.

**Validates Requirements**: 9.1, 9.2, 9.3, 9.4, 9.5, 9.6, 9.7, 9.8, 25.2
"""
from datetime import datetime, timedelta
from typing import Dict, Any
from uuid import UUID
import redis

from app.core.config import settings
from app.core.redis import get_redis
from app.utils.datetime import now_ist


class RateLimitStatus:
    """Rate limit status result"""
    
    def __init__(
        self,
        allowed: bool,
        remaining_requests: int,
        reset_time: datetime,
        hourly_count: int = 0,
        daily_count: int = 0
    ):
        self.allowed = allowed
        self.remaining_requests = remaining_requests
        self.reset_time = reset_time
        self.hourly_count = hourly_count
        self.daily_count = daily_count
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary representation"""
        return {
            "allowed": self.allowed,
            "remaining_requests": self.remaining_requests,
            "reset_time": self.reset_time.isoformat(),
            "hourly_count": self.hourly_count,
            "daily_count": self.daily_count
        }


class RateLimitService:
    """
    Service for managing rate limits using Redis.
    
    Uses Redis for distributed rate limiting with sliding window counters.
    
    **Validates Requirements**: 9.1, 9.2, 9.3, 9.4, 9.5, 9.6, 9.7, 9.8, 25.2
    """
    
    # Rate limit constants from settings
    MAX_REQUESTS_PER_HOUR = settings.RATE_LIMIT_HOURLY
    MAX_REQUESTS_PER_DAY = settings.RATE_LIMIT_DAILY
    
    # Redis key prefixes
    HOURLY_KEY_PREFIX = "rate_limit:hourly:"
    DAILY_KEY_PREFIX = "rate_limit:daily:"
    
    # TTL for Redis keys (with buffer)
    HOURLY_TTL = 3600 + 60  # 1 hour + 1 minute buffer
    DAILY_TTL = 86400 + 3600  # 24 hours + 1 hour buffer
    
    def __init__(self, redis_client: redis.Redis = None):
        """
        Initialize rate limit service.
        
        Args:
            redis_client: Redis client instance (uses default if not provided)
        """
        self.redis = redis_client or get_redis()
    
    def _get_hourly_key(self, user_id: UUID) -> str:
        """Generate Redis key for hourly rate limit"""
        return f"{self.HOURLY_KEY_PREFIX}{str(user_id)}"
    
    def _get_daily_key(self, user_id: UUID) -> str:
        """Generate Redis key for daily rate limit"""
        return f"{self.DAILY_KEY_PREFIX}{str(user_id)}"
    
    def check_rate_limit(self, user_id: UUID) -> RateLimitStatus:
        """
        Check if user is within rate limits.
        
        **Validates Requirements**: 9.1, 9.2, 9.3, 9.4, 9.5, 9.6, 9.7, 9.8
        
        This implements the rate limiting algorithm from the design document:
        - Counts requests in the last 60 minutes (hourly limit)
        - Counts requests in the last 24 hours (daily limit)
        - Returns allowed=false if either limit is exceeded
        - Calculates remaining requests as minimum of hourly and daily remaining
        
        Args:
            user_id: UUID of the user to check
            
        Returns:
            RateLimitStatus with allowed flag, remaining requests, and reset time
            
        Example:
            >>> service = RateLimitService()
            >>> status = service.check_rate_limit(user_id)
            >>> if status.allowed:
            ...     # Allow request
            ...     service.increment_request_count(user_id)
        """
        current_time = now_ist()
        
        # Get hourly and daily counts from Redis
        hourly_count = self._get_count(user_id, "hourly")
        daily_count = self._get_count(user_id, "daily")
        
        # Check hourly limit (Requirement 9.3, 9.4)
        if hourly_count >= self.MAX_REQUESTS_PER_HOUR:
            reset_time = current_time + timedelta(hours=1)
            return RateLimitStatus(
                allowed=False,
                remaining_requests=0,
                reset_time=reset_time,
                hourly_count=hourly_count,
                daily_count=daily_count
            )
        
        # Check daily limit (Requirement 9.5, 9.6)
        if daily_count >= self.MAX_REQUESTS_PER_DAY:
            reset_time = current_time + timedelta(days=1)
            return RateLimitStatus(
                allowed=False,
                remaining_requests=0,
                reset_time=reset_time,
                hourly_count=hourly_count,
                daily_count=daily_count
            )
        
        # Calculate remaining requests (Requirement 9.7, 9.8)
        remaining_hourly = self.MAX_REQUESTS_PER_HOUR - hourly_count
        remaining_daily = self.MAX_REQUESTS_PER_DAY - daily_count
        remaining = min(remaining_hourly, remaining_daily)
        
        # Reset time is when the hourly window expires
        reset_time = current_time + timedelta(hours=1)
        
        return RateLimitStatus(
            allowed=True,
            remaining_requests=remaining,
            reset_time=reset_time,
            hourly_count=hourly_count,
            daily_count=daily_count
        )
    
    def _get_count(self, user_id: UUID, window: str) -> int:
        """
        Get request count for a time window from Redis.
        
        **Validates Requirements**: 9.3, 9.5, 25.2
        
        Args:
            user_id: User ID
            window: "hourly" or "daily"
            
        Returns:
            Number of requests in the time window
        """
        try:
            if window == "hourly":
                key = self._get_hourly_key(user_id)
            else:
                key = self._get_daily_key(user_id)
            
            count = self.redis.get(key)
            return int(count) if count else 0
        except Exception as e:
            # Log error and return 0 to fail open (allow request)
            print(f"Redis get error for rate limit: {e}")
            return 0
    
    def increment_request_count(self, user_id: UUID) -> bool:
        """
        Increment request count for both hourly and daily windows.
        
        **Validates Requirements**: 9.3, 9.5, 25.2
        
        This should be called after a request is successfully created.
        Uses Redis INCR for atomic increment and sets TTL if key is new.
        
        Args:
            user_id: User ID
            
        Returns:
            True if successful, False otherwise
        """
        try:
            hourly_key = self._get_hourly_key(user_id)
            daily_key = self._get_daily_key(user_id)
            
            # Use pipeline for atomic operations
            pipe = self.redis.pipeline()
            
            # Increment hourly counter
            pipe.incr(hourly_key)
            pipe.expire(hourly_key, self.HOURLY_TTL)
            
            # Increment daily counter
            pipe.incr(daily_key)
            pipe.expire(daily_key, self.DAILY_TTL)
            
            # Execute all commands atomically
            pipe.execute()
            
            return True
        except Exception as e:
            print(f"Redis increment error for rate limit: {e}")
            return False
    
    def reset_user_limits(self, user_id: UUID) -> bool:
        """
        Reset rate limits for a user (admin function).
        
        Args:
            user_id: User ID
            
        Returns:
            True if successful, False otherwise
        """
        try:
            hourly_key = self._get_hourly_key(user_id)
            daily_key = self._get_daily_key(user_id)
            
            self.redis.delete(hourly_key, daily_key)
            return True
        except Exception as e:
            print(f"Redis delete error for rate limit reset: {e}")
            return False
    
    def get_user_stats(self, user_id: UUID) -> Dict[str, Any]:
        """
        Get current rate limit statistics for a user.
        
        Args:
            user_id: User ID
            
        Returns:
            Dictionary with hourly and daily counts
        """
        hourly_count = self._get_count(user_id, "hourly")
        daily_count = self._get_count(user_id, "daily")
        
        return {
            "hourly_count": hourly_count,
            "daily_count": daily_count,
            "hourly_limit": self.MAX_REQUESTS_PER_HOUR,
            "daily_limit": self.MAX_REQUESTS_PER_DAY,
            "hourly_remaining": max(0, self.MAX_REQUESTS_PER_HOUR - hourly_count),
            "daily_remaining": max(0, self.MAX_REQUESTS_PER_DAY - daily_count)
        }


# Singleton instance
_rate_limit_service = None


def get_rate_limit_service() -> RateLimitService:
    """
    Get singleton instance of RateLimitService.
    
    Returns:
        RateLimitService instance
    """
    global _rate_limit_service
    if _rate_limit_service is None:
        _rate_limit_service = RateLimitService()
    return _rate_limit_service
