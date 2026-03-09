"""
AuditLog model for action tracking
Validates: Requirements 24.8, 24.9
"""
from sqlalchemy import Column, String, DateTime, ForeignKey, Enum, Index, JSON
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from datetime import datetime
import uuid
import enum

from app.core.database import Base


class ActionType(enum.Enum):
    """Action type enumeration for audit logging"""
    USER_REGISTER = "USER_REGISTER"
    USER_LOGIN = "USER_LOGIN"
    VEHICLE_IDENTIFY = "VEHICLE_IDENTIFY"
    VEHICLE_IDENTIFIED = "VEHICLE_IDENTIFIED"
    REQUEST_CREATE = "REQUEST_CREATE"
    REQUEST_RESPOND = "REQUEST_RESPOND"
    REQUEST_EXPIRED = "REQUEST_EXPIRED"
    NOTIFICATION_SENT = "NOTIFICATION_SENT"
    NOTIFICATION_FAILED = "NOTIFICATION_FAILED"
    REPORT_CREATE = "REPORT_CREATE"


class AuditLog(Base):
    """
    AuditLog model for tracking all user actions
    
    Validates:
    - Requirement 24.8: Index on userId for user action queries
    - Requirement 24.9: Index on timestamp for time-based queries
    """
    __tablename__ = "audit_logs"
    
    # Primary key
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    
    # Foreign key to user
    userId = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)
    
    # Action details
    action = Column(Enum(ActionType), nullable=False)
    resourceType = Column(String(50), nullable=True)
    resourceId = Column(String(100), nullable=True)  # Changed from UUID to String to support vehicle numbers
    
    # Request metadata
    ipAddress = Column(String(45), nullable=True)  # IPv6 max length
    userAgent = Column(String(500), nullable=True)
    
    # Timestamp
    timestamp = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)
    
    # Additional metadata as JSON (using extra_data to avoid SQLAlchemy reserved name)
    extra_data = Column("metadata", JSON, nullable=True)
    
    # Relationships
    user = relationship("User", back_populates="audit_logs")
    
    def __repr__(self):
        return f"<AuditLog(id={self.id}, action={self.action}, userId={self.userId}, timestamp={self.timestamp})>"
