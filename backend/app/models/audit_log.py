"""
AuditLog model for action tracking
Validates: Requirements 24.8, 24.9
"""
from beanie import Document, Indexed
from pydantic import Field
from datetime import datetime
from typing import Optional, Dict, Any
from uuid import UUID, uuid4
import enum


class ActionType(str, enum.Enum):
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


class AuditLog(Document):
    """
    AuditLog model for tracking all user actions
    
    Validates:
    - Requirement 24.8: Index on userId for user action queries
    - Requirement 24.9: Index on timestamp for time-based queries
    """
    
    # Primary key
    id: UUID = Field(default_factory=uuid4)
    
    # Foreign key to user
    userId: Indexed(Optional[UUID]) = None
    
    # Action details
    action: ActionType
    resourceType: Optional[str] = None
    resourceId: Optional[str] = None  # String to support vehicle numbers
    
    # Request metadata
    ipAddress: Optional[str] = None
    userAgent: Optional[str] = None
    
    # Timestamp
    timestamp: Indexed(datetime) = Field(default_factory=datetime.utcnow)
    
    # Additional metadata
    metadata: Optional[Dict[str, Any]] = None
    
    class Settings:
        name = "audit_logs"
        indexes = [
            "id",
            "userId",
            "timestamp",
        ]
    
    def __repr__(self):
        return f"<AuditLog(id={self.id}, action={self.action}, userId={self.userId}, timestamp={self.timestamp})>"
