"""
Report model for abuse reporting
"""
from beanie import Document
from pydantic import Field, UUID4
from datetime import datetime
from typing import Optional
from uuid import uuid4
from pymongo import IndexModel, ASCENDING
import enum


class ReportReason(str, enum.Enum):
    """Report reason enumeration"""
    SPAM = "SPAM"
    HARASSMENT = "HARASSMENT"
    FALSE_REQUEST = "FALSE_REQUEST"
    ABUSE = "ABUSE"
    OTHER = "OTHER"


class ReportStatus(str, enum.Enum):
    """Report status enumeration"""
    PENDING = "PENDING"
    UNDER_REVIEW = "UNDER_REVIEW"
    RESOLVED = "RESOLVED"
    DISMISSED = "DISMISSED"


class AdminAction(str, enum.Enum):
    """Admin action enumeration"""
    WARNING = "WARNING"
    TEMPORARY_BAN = "TEMPORARY_BAN"
    PERMANENT_BAN = "PERMANENT_BAN"
    NO_ACTION = "NO_ACTION"


class Report(Document):
    """
    Report model for abuse reporting
    Tracks user reports for spam, harassment, and other violations
    """
    
    # Primary key
    id: UUID4 = Field(default_factory=uuid4)
    
    # Foreign keys
    reporterId: UUID4
    targetUserId: UUID4
    
    # Report details
    reason: ReportReason
    description: Optional[str] = None
    
    # Status tracking
    status: ReportStatus = ReportStatus.PENDING
    
    # Timestamps
    createdAt: datetime = Field(default_factory=datetime.utcnow)
    reviewedAt: Optional[datetime] = None
    
    # Admin review
    reviewedBy: Optional[UUID4] = None
    action: Optional[AdminAction] = None
    
    class Settings:
        name = "reports"
        indexes = [
            IndexModel([("reporterId", ASCENDING)]),
            IndexModel([("targetUserId", ASCENDING)]),
            IndexModel([("status", ASCENDING)]),
            IndexModel([("createdAt", ASCENDING)]),
        ]
    
    def __repr__(self):
        return f"<Report(id={self.id}, reason={self.reason}, status={self.status}, reporterId={self.reporterId}, targetUserId={self.targetUserId})>"
