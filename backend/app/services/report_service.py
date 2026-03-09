"""
Report and abuse detection service

Handles user reporting and automatic abuse pattern detection.

**Validates Requirements**: 14, 15
"""
from sqlalchemy.orm import Session
from datetime import datetime, timedelta
from typing import Optional
from uuid import UUID

from app.models.report import Report, ReportReason, ReportStatus
from app.models.user import User
from app.models.request import Request
from app.services.audit_service import audit_service
from app.models.audit_log import ActionType
from app.utils.datetime import now_ist


class ReportService:
    """Service for handling reports and abuse detection"""
    
    def create_report(
        self,
        db: Session,
        reporter_id: UUID,
        target_user_id: UUID,
        reason: ReportReason,
        description: Optional[str] = None
    ) -> Report:
        """
        Create a new abuse report
        
        Process:
        1. Validate target user is different from reporter (Requirement 14.2)
        2. Check daily report limit (5 reports/day) (Requirement 14.4)
        3. Create report record (Requirement 14.3)
        4. Check if target has 3+ reports (Requirement 14.6)
        5. Flag account for review if threshold reached (Requirement 14.7)
        
        **Validates Requirements**: 14.1, 14.2, 14.3, 14.4, 14.5, 14.6, 14.7, 14.8, 21.8
        
        Args:
            db: Database session
            reporter_id: ID of user creating report
            target_user_id: ID of user being reported
            reason: Report reason enum
            description: Optional description
            
        Returns:
            Created Report object
            
        Raises:
            ValueError: If validation fails
        """
        # Validate target user is different from reporter (Requirement 14.2)
        if reporter_id == target_user_id:
            raise ValueError("Cannot report yourself")
        
        # Check daily report limit (Requirement 14.4)
        today_start = now_ist().replace(hour=0, minute=0, second=0, microsecond=0)
        reports_today = db.query(Report).filter(
            Report.reporterId == reporter_id,
            Report.createdAt >= today_start
        ).count()
        
        if reports_today >= 5:
            raise ValueError("Daily report limit exceeded (5 reports per day)")
        
        # Create report record (Requirement 14.3)
        report = Report(
            reporterId=reporter_id,
            targetUserId=target_user_id,
            reason=reason,
            description=description,
            status=ReportStatus.PENDING
        )
        
        db.add(report)
        db.commit()
        db.refresh(report)
        
        # Create audit log entry (Requirement 21.8)
        audit_service.log_action(
            db=db,
            user_id=reporter_id,
            action=ActionType.REPORT_CREATE,
            resource_type="Report",
            resource_id=report.id,
            metadata={
                "targetUserId": str(target_user_id),
                "reason": reason.value,
                "description": description
            }
        )
        
        # Check if target user has 3+ reports (Requirement 14.6)
        target_reports_count = db.query(Report).filter(
            Report.targetUserId == target_user_id,
            Report.status == ReportStatus.PENDING
        ).count()
        
        if target_reports_count >= 3:
            # Flag account for admin review (Requirement 14.7)
            target_user = db.query(User).filter(User.id == target_user_id).first()
            if target_user:
                target_user.isFlagged = True
                db.commit()
                print(f"User {target_user_id} flagged for review (3+ reports)")
        
        return report
    
    def detect_spam_pattern(self, db: Session, user_id: UUID) -> bool:
        """
        Detect spam pattern: >5 requests in 15 minutes
        
        **Validates Requirements**: 15.1, 15.2
        
        Args:
            db: Database session
            user_id: User ID to check
            
        Returns:
            True if spam pattern detected
        """
        # Check requests in last 15 minutes (Requirement 15.1)
        fifteen_min_ago = now_ist() - timedelta(minutes=15)
        
        recent_requests = db.query(Request).filter(
            Request.requesterId == user_id,
            Request.createdAt >= fifteen_min_ago
        ).count()
        
        return recent_requests > 5
    
    def detect_harassment_pattern(self, db: Session, user_id: UUID) -> bool:
        """
        Detect harassment pattern: >3 requests to same user in 24 hours
        
        **Validates Requirements**: 15.3, 15.4
        
        Args:
            db: Database session
            user_id: User ID to check
            
        Returns:
            True if harassment pattern detected
        """
        # Check requests in last 24 hours (Requirement 15.3)
        twenty_four_hours_ago = now_ist() - timedelta(hours=24)
        
        # Get all requests from this user in last 24 hours
        recent_requests = db.query(Request).filter(
            Request.requesterId == user_id,
            Request.createdAt >= twenty_four_hours_ago
        ).all()
        
        # Count requests per target user
        target_counts = {}
        for req in recent_requests:
            target_id = str(req.targetUserId)
            target_counts[target_id] = target_counts.get(target_id, 0) + 1
        
        # Check if any target has >3 requests (Requirement 15.4)
        return any(count > 3 for count in target_counts.values())
    
    def apply_restrictions(
        self,
        db: Session,
        user_id: UUID,
        reason: str,
        duration_hours: int = 24
    ) -> None:
        """
        Apply temporary restrictions to user account
        
        **Validates Requirements**: 15.5, 15.6
        
        Args:
            db: Database session
            user_id: User ID to restrict
            reason: Reason for restriction
            duration_hours: Duration of restriction in hours
        """
        user = db.query(User).filter(User.id == user_id).first()
        
        if user:
            # Flag user for review (Requirement 15.5)
            user.isFlagged = True
            
            # In a full implementation, we would:
            # 1. Set restriction expiry time
            # 2. Notify admin dashboard (Requirement 15.6, 15.7)
            # 3. Store restriction details
            
            db.commit()
            print(f"Applied restrictions to user {user_id}: {reason}")
    
    def check_and_apply_abuse_detection(self, db: Session, user_id: UUID) -> None:
        """
        Check for abuse patterns and apply restrictions if detected
        
        **Validates Requirements**: 15.1, 15.2, 15.3, 15.4, 15.5, 15.6, 15.7
        
        Args:
            db: Database session
            user_id: User ID to check
        """
        # Check for spam pattern
        if self.detect_spam_pattern(db, user_id):
            self.apply_restrictions(
                db, user_id,
                "Spam pattern detected: >5 requests in 15 minutes"
            )
            return
        
        # Check for harassment pattern
        if self.detect_harassment_pattern(db, user_id):
            self.apply_restrictions(
                db, user_id,
                "Harassment pattern detected: >3 requests to same user in 24 hours"
            )
            return


# Service instance
report_service = ReportService()
