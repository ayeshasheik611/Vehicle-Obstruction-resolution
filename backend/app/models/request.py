"""
Request model
Validates: Requirements 22.1, 22.2, 22.3, 24.2, 24.3, 24.4, 24.5, 24.6
"""
from sqlalchemy import Column, String, DateTime, ForeignKey, Enum, Index, CheckConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from datetime import datetime
import uuid
import enum

from app.core.database import Base
from app.utils.datetime import now_ist


class RequestStatus(enum.Enum):
    """Request status enumeration"""
    PENDING = "PENDING"
    RESPONDED = "RESPONDED"
    RESOLVED = "RESOLVED"
    EXPIRED = "EXPIRED"
    CANCELLED = "CANCELLED"


class ResponseType(enum.Enum):
    """Response type enumeration"""
    MESSAGE = "MESSAGE"
    ON_MY_WAY = "ON_MY_WAY"
    CANNOT_MOVE = "CANNOT_MOVE"


class Request(Base):
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
    __tablename__ = "requests"
    
    # Primary key
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    
    # Foreign keys
    requesterId = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    targetUserId = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    
    # Vehicle information
    targetVehicle = Column(String(20), nullable=False)
    
    # Status tracking
    status = Column(Enum(RequestStatus), default=RequestStatus.PENDING, nullable=False, index=True)
    
    # Timestamps
    createdAt = Column(DateTime, default=now_ist, nullable=False, index=True)
    respondedAt = Column(DateTime, nullable=True)
    expiresAt = Column(DateTime, nullable=False)
    
    # Response details
    response = Column(Enum(ResponseType), nullable=True)
    responseMessage = Column(String(500), nullable=True)
    
    # Relationships
    requester = relationship("User", foreign_keys=[requesterId], back_populates="sent_requests")
    target_user = relationship("User", foreign_keys=[targetUserId], back_populates="received_requests")
    
    # Constraints
    __table_args__ = (
        CheckConstraint('"requesterId" != "targetUserId"', name='check_different_users'),
        Index('idx_requester_created', 'requesterId', 'createdAt'),  # Composite index for rate limiting
    )
    
    def __repr__(self):
        return f"<Request(id={self.id}, status={self.status}, requesterId={self.requesterId}, targetUserId={self.targetUserId})>"
