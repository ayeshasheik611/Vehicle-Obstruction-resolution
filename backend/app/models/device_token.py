"""
DeviceToken model
Validates: Requirements 22.7, 24.7
"""
from beanie import Document, Indexed
from pydantic import Field
from datetime import datetime
from typing import Optional
from uuid import UUID, uuid4
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
    id: UUID = Field(default_factory=uuid4)
    
    # Foreign key to user
    userId: Indexed(UUID)
    
    # FCM token
    fcmToken: Indexed(str, unique=True)
    
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
            "id",
            "userId",
            "fcmToken",
        ]
    
    def __repr__(self):
        return f"<DeviceToken(id={self.id}, userId={self.userId}, platform={self.platform}, isActive={self.isActive})>"
