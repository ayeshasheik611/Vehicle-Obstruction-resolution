"""
Report model for abuse reporting
"""
from sqlalchemy import Column, String, DateTime, ForeignKey, Enum, Index
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from datetime import datetime
import uuid
import enum

from app.core.database import Base


class ReportReason(enum.Enum):
    """Report reason enumeration"""
    SPAM = "SPAM"
    HARASSMENT = "HARASSMENT"
    FALSE_REQUEST = "FALSE_REQUEST"
    ABUSE = "ABUSE"
    OTHER = "OTHER"


class ReportStatus(enum.Enum):
    """Report status enumeration"""
    PENDING = "PENDING"
    UNDER_REVIEW = "UNDER_REVIEW"
    RESOLVED = "RESOLVED"
    DISMISSED = "DISMISSED"


class AdminAction(enum.Enum):
    """Admin action enumeration"""
    WARNING = "WARNING"
    TEMPORARY_BAN = "TEMPORARY_BAN"
    PERMANENT_BAN = "PERMANENT_BAN"
    NO_ACTION = "NO_ACTION"


class Report(Base):
    """
    Report model for abuse reporting
    Tracks user reports for spam, harassment, and other violations
    """
    __tablename__ = "reports"
    
    # Primary key
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    
    # Foreign keys
    reporterId = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    targetUserId = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    
    # Report details
    reason = Column(Enum(ReportReason), nullable=False)
    description = Column(String(1000), nullable=True)
    
    # Status tracking
    status = Column(Enum(ReportStatus), default=ReportStatus.PENDING, nullable=False, index=True)
    
    # Timestamps
    createdAt = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)
    reviewedAt = Column(DateTime, nullable=True)
    
    # Admin review
    reviewedBy = Column(UUID(as_uuid=True), nullable=True)
    action = Column(Enum(AdminAction), nullable=True)
    
    # Relationships
    reporter = relationship("User", foreign_keys=[reporterId], back_populates="reports_made")
    target_user = relationship("User", foreign_keys=[targetUserId], back_populates="reports_received")
    
    def __repr__(self):
        return f"<Report(id={self.id}, reason={self.reason}, status={self.status}, reporterId={self.reporterId}, targetUserId={self.targetUserId})>"
