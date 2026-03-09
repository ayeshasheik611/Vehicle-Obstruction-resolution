# Rate Limiting Service

## Overview

The Rate Limiting Service provides distributed rate limiting functionality using Redis to prevent abuse and spam in the FreeWay Community application.

**Validates Requirements**: 9.1, 9.2, 9.3, 9.4, 9.5, 9.6, 9.7, 9.8, 25.2

## Features

- **Hourly Rate Limit**: Maximum 10 requests per hour per user
- **Daily Rate Limit**: Maximum 50 requests per day per user
- **Distributed Counters**: Uses Redis for distributed rate limiting across multiple servers
- **Atomic Operations**: Uses Redis pipelines for atomic counter updates
- **Automatic Expiry**: Redis keys automatically expire after time windows

## Usage

### Basic Usage

```python
from app.services.rate_limit_service import get_rate_limit_service

# Get service instance
rate_limit_service = get_rate_limit_service()

# Check if user is within rate limits
status = rate_limit_service.check_rate_limit(user_id)

if status.allowed:
    # Process the request
    # ...
    
    # Increment counter after successful request
    rate_limit_service.increment_request_count(user_id)
else:
    # Return rate limit error
    return {
        "error": "Rate limit exceeded",
        "remaining": status.remaining_requests,
        "reset_time": status.reset_time
    }
```

### In API Endpoints

```python
from fastapi import HTTPException, status
from app.services.rate_limit_service import get_rate_limit_service

@app.post("/api/request/create")
async def create_request(user_id: UUID):
    # Check rate limit
    rate_limit_service = get_rate_limit_service()
    rate_status = rate_limit_service.check_rate_limit(user_id)
    
    if not rate_status.allowed:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail={
                "message": "Rate limit exceeded",
                "remaining": rate_status.remaining_requests,
                "reset_time": rate_status.reset_time.isoformat()
            }
        )
    
    # Process request...
    
    # Increment counter
    rate_limit_service.increment_request_count(user_id)
    
    return {"success": True}
```

## API Reference

### RateLimitService

#### `check_rate_limit(user_id: UUID) -> RateLimitStatus`

Check if a user is within rate limits.

**Parameters:**
- `user_id`: UUID of the user to check

**Returns:**
- `RateLimitStatus` object with:
  - `allowed`: Boolean indicating if request is allowed
  - `remaining_requests`: Number of requests remaining
  - `reset_time`: DateTime when the rate limit resets
  - `hourly_count`: Current hourly request count
  - `daily_count`: Current daily request count

#### `increment_request_count(user_id: UUID) -> bool`

Increment the request count for a user. Should be called after a request is successfully processed.

**Parameters:**
- `user_id`: UUID of the user

**Returns:**
- `True` if successful, `False` otherwise

#### `reset_user_limits(user_id: UUID) -> bool`

Reset rate limits for a user (admin function).

**Parameters:**
- `user_id`: UUID of the user

**Returns:**
- `True` if successful, `False` otherwise

#### `get_user_stats(user_id: UUID) -> Dict[str, Any]`

Get current rate limit statistics for a user.

**Parameters:**
- `user_id`: UUID of the user

**Returns:**
- Dictionary with hourly and daily counts and limits

## Configuration

Rate limits are configured in `app/core/config.py`:

```python
# Rate limiting
RATE_LIMIT_HOURLY = 10  # Maximum requests per hour
RATE_LIMIT_DAILY = 50   # Maximum requests per day
```

Redis connection is configured via environment variables:

```bash
REDIS_URL=redis://localhost:6379/0
REDIS_MAX_CONNECTIONS=50
```

## Redis Keys

The service uses the following Redis key patterns:

- **Hourly**: `rate_limit:hourly:{user_id}`
- **Daily**: `rate_limit:daily:{user_id}`

Keys automatically expire:
- Hourly keys: 1 hour + 1 minute buffer
- Daily keys: 24 hours + 1 hour buffer

## Algorithm

The rate limiting algorithm follows the design specification:

1. Get current hourly and daily request counts from Redis
2. Check if hourly count >= 10 (hourly limit)
3. Check if daily count >= 50 (daily limit)
4. Calculate remaining requests as min(hourly_remaining, daily_remaining)
5. Return status with allowed flag and remaining count

## Testing

Run the unit tests:

```bash
cd backend
python -m pytest tests/test_rate_limit_service.py -v
```

All tests use a mock Redis client for fast, isolated testing.

## Error Handling

The service is designed to "fail open" - if Redis is unavailable, it returns 0 for counts, allowing requests to proceed. This prevents Redis outages from blocking all traffic.

However, in production, you should monitor Redis availability and alert on failures.

## Performance

- Uses Redis pipelines for atomic operations
- Minimal Redis operations per request (2 GET operations for check, 4 operations for increment)
- Keys automatically expire to prevent memory buildup
- Supports distributed deployment across multiple servers

## Requirements Validation

This service validates the following requirements:

- **9.1**: Maximum of 10 requests per hour per user
- **9.2**: Maximum of 50 requests per day per user
- **9.3**: Count requests in last 60 minutes
- **9.4**: Return rate limit status with allowed false when hourly limit reached
- **9.5**: Count requests in last 24 hours
- **9.6**: Return rate limit status with allowed false when daily limit reached
- **9.7**: Calculate remaining requests as minimum of hourly and daily remaining
- **9.8**: Return rate limit status with allowed true and remaining count when within limits
- **25.2**: Cache rate limit counters in Redis with appropriate TTL
