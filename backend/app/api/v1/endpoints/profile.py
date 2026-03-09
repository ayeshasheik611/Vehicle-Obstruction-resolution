"""
Profile endpoints for user information and rate limits
"""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.api.dependencies import get_current_user
from app.models.user import User
from app.services.rate_limit_service import get_rate_limit_service
from app.core.config import settings
from pydantic import BaseModel


router = APIRouter()


class RateLimitInfo(BaseModel):
    """Rate limit information"""
    hourly_limit: int
    hourly_remaining: int
    daily_limit: int
    daily_remaining: int
    reset_time: str


class ProfileResponse(BaseModel):
    """Profile response"""
    success: bool
    userId: str
    vehicleNumber: str
    isActive: bool
    requestCount: int
    reportCount: int
    rateLimits: RateLimitInfo


@router.get("/me", response_model=ProfileResponse)
async def get_profile(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get current user profile with rate limit information
    """
    from app.models.request import Request
    from app.utils.datetime import now_ist
    from datetime import timedelta
    from sqlalchemy import func
    
    # Get rate limit status from Redis
    rate_limit_service = get_rate_limit_service()
    rate_status = rate_limit_service.check_rate_limit(current_user.id)
    
    # Calculate actual request counts from database
    current_time = now_ist()
    one_hour_ago = current_time - timedelta(hours=1)
    one_day_ago = current_time - timedelta(days=1)
    
    # Count requests in the last hour
    hourly_count = db.query(func.count(Request.id)).filter(
        Request.requesterId == current_user.id,
        Request.createdAt >= one_hour_ago
    ).scalar() or 0
    
    # Count requests in the last 24 hours
    daily_count = db.query(func.count(Request.id)).filter(
        Request.requesterId == current_user.id,
        Request.createdAt >= one_day_ago
    ).scalar() or 0
    
    # Calculate remaining requests
    hourly_remaining = max(0, settings.RATE_LIMIT_HOURLY - hourly_count)
    daily_remaining = max(0, settings.RATE_LIMIT_DAILY - daily_count)
    
    return ProfileResponse(
        success=True,
        userId=str(current_user.id),
        vehicleNumber=current_user.vehicleNumber,
        isActive=current_user.isActive,
        requestCount=current_user.requestCount,
        reportCount=current_user.reportCount,
        rateLimits=RateLimitInfo(
            hourly_limit=settings.RATE_LIMIT_HOURLY,
            hourly_remaining=hourly_remaining,
            daily_limit=settings.RATE_LIMIT_DAILY,
            daily_remaining=daily_remaining,
            reset_time=rate_status.reset_time.isoformat() if rate_status.reset_time else ""
        )
    )
