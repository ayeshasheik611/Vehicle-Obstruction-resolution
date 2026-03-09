"""
User model
Validates: Requirements 1.6, 22.1, 22.6, 24.1
"""
from sqlalchemy import Column, String, Boolean, DateTime, Integer, Index
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from datetime import datetime
import uuid

from app.core.database import Base


class User(Base):
    """
    User model representing registered vehicle owners
    
    Validates:
    - Requirement 1.6: User record creation with unique UUID
    - Requirement 22.6: Unique vehicle numbers across all users
    - Requirement 24.1: Index on vehicleNumber for fast lookups
    """
    __tablename__ = "users"
    
    # Primary key
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    
    # Authentication fields
    vehicleNumber = Column(String(20), unique=True, nullable=False, index=True)
    passwordHash = Column(String(255), nullable=False)
    
    # FCM token for push notifications
    fcmToken = Column(String(255), nullable=True)
    
    # Status flags
    isActive = Column(Boolean, default=True, nullable=False)
    isBanned = Column(Boolean, default=False, nullable=False)
    
    # Timestamps
    createdAt = Column(DateTime, default=datetime.utcnow, nullable=False)
    lastLoginAt = Column(DateTime, nullable=True)
    
    # Counters for rate limiting and abuse detection
    requestCount = Column(Integer, default=0, nullable=False)
    reportCount = Column(Integer, default=0, nullable=False)
    
    # Relationships
    vehicles = relationship("Vehicle", back_populates="owner", cascade="all, delete-orphan")
    sent_requests = relationship("Request", foreign_keys="Request.requesterId", back_populates="requester")
    received_requests = relationship("Request", foreign_keys="Request.targetUserId", back_populates="target_user")
    device_tokens = relationship("DeviceToken", back_populates="user", cascade="all, delete-orphan")
    reports_made = relationship("Report", foreign_keys="Report.reporterId", back_populates="reporter")
    reports_received = relationship("Report", foreign_keys="Report.targetUserId", back_populates="target_user")
    audit_logs = relationship("AuditLog", back_populates="user")
    
    def __repr__(self):
        return f"<User(id={self.id}, vehicleNumber={self.vehicleNumber})>"
