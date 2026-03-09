"""
User model
Validates: Requirements 1.6, 22.1, 22.6, 24.1
"""
from beanie import Document
from pydantic import Field, UUID4
from datetime import datetime
from typing import Optional
from uuid import uuid4
from pymongo import IndexModel, ASCENDING


class User(Document):
    """
    User model representing registered vehicle owners
    
    Validates:
    - Requirement 1.6: User record creation with unique UUID
    - Requirement 22.6: Unique vehicle numbers across all users
    - Requirement 24.1: Index on vehicleNumber for fast lookups
    """
    
    # Primary key
    id: UUID4 = Field(default_factory=uuid4)
    
    # Authentication fields
    vehicleNumber: str
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
            IndexModel([("vehicleNumber", ASCENDING)], unique=True),
        ]
    
    def __repr__(self):
        return f"<User(id={self.id}, vehicleNumber={self.vehicleNumber})>"
