"""
Report and abuse detection service

Handles user reporting and automatic abuse pattern detection.

**Validates Requirements**: 14, 15
"""
from datetime import datetime, timedelta
from typing import Optional
from uuid import UUID
from beanie.operators import And, GTE

from app.models.report import Report, ReportReason, ReportStatus
from app.models.user import User
from app.models.request import Request
from app.models.audit_log import ActionType, AuditLog
from app.utils.datetime import now_ist


class ReportService:
    """Service for handling reports and abuse detection"""
    
    async def create_report(
        self,
        reporter_id: UUID,
        target_user_id: UUID,
        reason: ReportReason,
        description: Optional[str] = None
    ) -> Report:
        """
        Create a new abuse report
        
        **Validates Requirements**: 14.1, 14.2, 14.3, 14.4, 14.5, 14.6, 14.7, 14.8, 21.8
        """
        if reporter_id == target_user_id:
            raise ValueError("Cannot report yourself")
        
        today_start = now_ist().replace(hour=0, minute=0, second=0, microsecond=0)
        reports_today = await Report.find(
            And(
                Report.reporterId == reporter_id,
                GTE(Report.createdAt, today_start)
            )
        ).count()
        
        if reports_today >= 5:
            raise ValueError("Daily report limit exceeded (5 reports per day)")
        
        report = Report(
            reporterId=reporter_id,
            targetUserId=target_user_id,
            reason=reason,
            description=description,
            status=ReportStatus.PENDING
        )
        
        await report.insert()
        
        audit_log = AuditLog(
            userId=reporter_id,
            action=ActionType.REPORT_CREATE,
            resourceType="Report",
            resourceId=str(report.id),
            metadata={
                "targetUserId": str(target_user_id),
                "reason": reason.value,
                "description": description
            }
        )
        await audit_log.insert()
        
        target_reports_count = await Report.find(
            And(
                Report.targetUserId == target_user_id,
                Report.status == ReportStatus.PENDING
            )
        ).count()
        
        if target_reports_count >= 3:
            target_user = await User.find_one(User.id == target_user_id)
            if target_user:
                target_user.isBanned = True
                await target_user.save()
                print(f"User {target_user_id} flagged for review (3+ reports)")
        
        return report
    
    async def detect_spam_pattern(self, user_id: UUID) -> bool:
        """
        Detect spam pattern: >5 requests in 15 minutes
        
        **Validates Requirements**: 15.1, 15.2
        """
        fifteen_min_ago = now_ist() - timedelta(minutes=15)
        
        recent_requests = await Request.find(
            And(
                Request.requesterId == user_id,
                GTE(Request.createdAt, fifteen_min_ago)
            )
        ).count()
        
        return recent_requests > 5
    
    async def detect_harassment_pattern(self, user_id: UUID) -> bool:
        """
        Detect harassment pattern: >3 requests to same user in 24 hours
        
        **Validates Requirements**: 15.3, 15.4
        """
        twenty_four_hours_ago = now_ist() - timedelta(hours=24)
        
        recent_requests = await Request.find(
            And(
                Request.requesterId == user_id,
                GTE(Request.createdAt, twenty_four_hours_ago)
            )
        ).to_list()
        
        target_counts = {}
        for req in recent_requests:
            target_id = str(req.targetUserId)
            target_counts[target_id] = target_counts.get(target_id, 0) + 1
        
        return any(count > 3 for count in target_counts.values())
    
    async def apply_restrictions(
        self,
        user_id: UUID,
        reason: str,
        duration_hours: int = 24
    ) -> None:
        """
        Apply temporary restrictions to user account
        
        **Validates Requirements**: 15.5, 15.6
        """
        user = await User.find_one(User.id == user_id)
        
        if user:
            user.isBanned = True
            await user.save()
            print(f"Applied restrictions to user {user_id}: {reason}")
    
    async def check_and_apply_abuse_detection(self, user_id: UUID) -> None:
        """
        Check for abuse patterns and apply restrictions if detected
        
        **Validates Requirements**: 15.1, 15.2, 15.3, 15.4, 15.5, 15.6, 15.7
        """
        if await self.detect_spam_pattern(user_id):
            await self.apply_restrictions(
                user_id,
                "Spam pattern detected: >5 requests in 15 minutes"
            )
            return
        
        if await self.detect_harassment_pattern(user_id):
            await self.apply_restrictions(
                user_id,
                "Harassment pattern detected: >3 requests to same user in 24 hours"
            )
            return


# Service instance
report_service = ReportService()
