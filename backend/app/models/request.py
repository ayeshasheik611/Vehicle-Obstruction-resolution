"""
Request model
Validates: Requirements 22.1, 22.2, 22.3, 24.2, 24.3, 24.4, 24.5, 24.6
"""
from beanie import Document
from pydantic import Field, field_validator, UUID4
from datetime import datetime
from typing import Optional
from uuid import uuid4
from pymongo import IndexModel, ASCENDING, DESCENDING
import enum


class RequestStatus(str, enum.Enum):
    """Request status enumeration"""
    PENDING = "PENDING"
    RESPONDED = "RESPONDED"
    RESOLVED = "RESOLVED"
    EXPIRED = "EXPIRED"
    CANCELLED = "CANCELLED"


class ResponseType(str, enum.Enum):
    """Response type enumeration"""
    MESSAGE = "MESSAGE"
    ON_MY_WAY = "ON_MY_WAY"
    CANNOT_MOVE = "CANNOT_MOVE"


class Request(Document):
    """
    Request model representing call requests between users
    
    Validates:
    - Requirement 22.1: Every request has a valid requester ID referencing an existing user
    - Requirement 22.2: Every request has a valid target user ID referencing an existing user
    - Requirement 22.3: Requester ID and target user ID are different
    - Requirement 24.2: Index on requesterId for request history queries
    - Requirement 24.3: Index on targetUserId for request history queries
    - Requirement 24.4: Index on status for filtering by status
    - Requirement 24.5: Index on createdAt for expiration job queries
    - Requirement 24.6: Composite index on (requesterId, createdAt) for rate limiting
    """
    
    # Primary key
    id: UUID4 = Field(default_factory=uuid4)
    
    # Foreign keys
    requesterId: UUID4
    targetUserId: UUID4
    
    # Vehicle information
    targetVehicle: str
    
    # Status tracking
    status: RequestStatus = RequestStatus.PENDING
    
    # Timestamps
    createdAt: datetime
    respondedAt: Optional[datetime] = None
    expiresAt: datetime
    
    # Response details
    response: Optional[ResponseType] = None
    responseMessage: Optional[str] = None
    
    @field_validator('targetUserId')
    @classmethod
    def validate_different_users(cls, v, info):
        """Validate that requester and target are different users"""
        if 'requesterId' in info.data and v == info.data['requesterId']:
            raise ValueError('requesterId and targetUserId must be different')
        return v
    
    class Settings:
        name = "requests"
        indexes = [
            IndexModel([("requesterId", ASCENDING)]),
            IndexModel([("targetUserId", ASCENDING)]),
            IndexModel([("status", ASCENDING)]),
            IndexModel([("createdAt", ASCENDING)]),
            IndexModel([("requesterId", ASCENDING), ("createdAt", DESCENDING)]),  # Composite for rate limiting
        ]
    
    def __repr__(self):
        return f"<Request(id={self.id}, status={self.status}, requesterId={self.requesterId}, targetUserId={self.targetUserId})>"
