"""
User model
Validates: Requirements 1.6, 22.1, 22.6, 24.1
"""
from beanie import Document, Indexed
from pydantic import Field
from datetime import datetime
from typing import Optional
from uuid import UUID, uuid4


class User(Document):
    """
    User model representing registered vehicle owners
    
    Validates:
    - Requirement 1.6: User record creation with unique UUID
    - Requirement 22.6: Unique vehicle numbers across all users
    - Requirement 24.1: Index on vehicleNumber for fast lookups
    """
    
    # Primary key
    id: UUID = Field(default_factory=uuid4)
    
    # Authentication fields
    vehicleNumber: Indexed(str, unique=True)
    passwordHash: str
    
    # FCM token for push notifications
    fcmToken: Optional[str] = None
    
    # Status flags
    isActive: bool = True
    isBanned: bool = False
    
    # Timestamps
    createdAt: datetime = Field(default_factory=datetime.utcnow)
    lastLoginAt: Optional[datetime] = None
    
    # Counters for rate limiting and abuse detection
    requestCount: int = 0
    reportCount: int = 0
    
    class Settings:
        name = "users"
        indexes = [
            "id",
            "vehicleNumber",
        ]
    
    def __repr__(self):
        return f"<User(id={self.id}, vehicleNumber={self.vehicleNumber})>"
