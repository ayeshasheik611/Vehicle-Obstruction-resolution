"""
DeviceToken model
Validates: Requirements 22.7, 24.7
"""
from beanie import Document
from pydantic import Field, UUID4
from datetime import datetime
from typing import Optional
from uuid import uuid4
from pymongo import IndexModel, ASCENDING
import enum


class Platform(str, enum.Enum):
    """Device platform enumeration"""
    IOS = "IOS"
    ANDROID = "ANDROID"


class DeviceToken(Document):
    """
    DeviceToken model for FCM token management
    
    Validates:
    - Requirement 22.7: FCM tokens are unique across all device tokens
    - Requirement 24.7: Index on userId for token retrieval
    """
    
    # Primary key
    id: UUID4 = Field(default_factory=uuid4)
    
    # Foreign key to user
    userId: UUID4
    
    # FCM token
    fcmToken: str
    
    # Platform information
    platform: Platform
    
    # Status
    isActive: bool = True
    
    # Timestamps
    createdAt: datetime = Field(default_factory=datetime.utcnow)
    lastUsedAt: Optional[datetime] = None
    
    class Settings:
        name = "device_tokens"
        indexes = [
            IndexModel([("userId", ASCENDING)]),
            IndexModel([("fcmToken", ASCENDING)], unique=True),
        ]
    
    def __repr__(self):
        return f"<DeviceToken(id={self.id}, userId={self.userId}, platform={self.platform}, isActive={self.isActive})>"
