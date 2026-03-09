"""
DeviceToken model
Validates: Requirements 22.7, 24.7
"""
from sqlalchemy import Column, String, Boolean, DateTime, ForeignKey, Enum, Index
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from datetime import datetime
import uuid
import enum

from app.core.database import Base


class Platform(enum.Enum):
    """Device platform enumeration"""
    IOS = "IOS"
    ANDROID = "ANDROID"


class DeviceToken(Base):
    """
    DeviceToken model for FCM token management
    
    Validates:
    - Requirement 22.7: FCM tokens are unique across all device tokens
    - Requirement 24.7: Index on userId for token retrieval
    """
    __tablename__ = "device_tokens"
    
    # Primary key
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    
    # Foreign key to user
    userId = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    
    # FCM token
    fcmToken = Column(String(255), unique=True, nullable=False)
    
    # Platform information
    platform = Column(Enum(Platform), nullable=False)
    
    # Status
    isActive = Column(Boolean, default=True, nullable=False)
    
    # Timestamps
    createdAt = Column(DateTime, default=datetime.utcnow, nullable=False)
    lastUsedAt = Column(DateTime, nullable=True)
    
    # Relationships
    user = relationship("User", back_populates="device_tokens")
    
    def __repr__(self):
        return f"<DeviceToken(id={self.id}, userId={self.userId}, platform={self.platform}, isActive={self.isActive})>"
