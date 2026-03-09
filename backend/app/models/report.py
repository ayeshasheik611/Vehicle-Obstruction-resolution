"""
Report model for abuse reporting
"""
from beanie import Document, Indexed
from pydantic import Field
from datetime import datetime
from typing import Optional
from uuid import UUID, uuid4
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
    id: UUID = Field(default_factory=uuid4)
    
    # Foreign keys
    reporterId: Indexed(UUID)
    targetUserId: Indexed(UUID)
    
    # Report details
    reason: ReportReason
    description: Optional[str] = None
    
    # Status tracking
    status: Indexed(ReportStatus) = ReportStatus.PENDING
    
    # Timestamps
    createdAt: Indexed(datetime) = Field(default_factory=datetime.utcnow)
    reviewedAt: Optional[datetime] = None
    
    # Admin review
    reviewedBy: Optional[UUID] = None
    action: Optional[AdminAction] = None
    
    class Settings:
        name = "reports"
        indexes = [
            "id",
            "reporterId",
            "targetUserId",
            "status",
            "createdAt",
        ]
    
    def __repr__(self):
        return f"<Report(id={self.id}, reason={self.reason}, status={self.status}, reporterId={self.reporterId}, targetUserId={self.targetUserId})>"
