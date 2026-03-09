"""
Request expiration scheduled job service

This module provides a scheduled job that runs every 5 minutes to expire
pending requests that have passed their expiration time.

**Validates Requirements**: 12.1, 12.2, 12.3, 12.4, 12.5
"""
import asyncio
from datetime import datetime
from typing import List
from beanie.operators import And, LT

from app.models.request import Request, RequestStatus
from app.models.audit_log import ActionType, AuditLog
from app.utils.datetime import now_ist


class RequestExpirationService:
    """Service for handling request expiration"""
    
    async def expire_pending_requests(self) -> int:
        """
        Expire all pending requests that have passed their expiration time.
        
        This method:
        1. Queries all PENDING requests with expiresAt < current time (Requirement 12.2)
        2. Updates each request status to EXPIRED (Requirement 12.3)
        3. Creates audit log entries for expired requests (Requirement 12.4)
        4. Does NOT send notifications (Requirement 12.5)
        
        **Validates Requirements**: 12.2, 12.3, 12.4, 12.5
        
        Returns:
            Number of requests that were expired
        """
        try:
            current_time = now_ist()
            
            # Query all PENDING requests with expiresAt < current time
            # Validates Requirement 12.2
            expired_requests: List[Request] = await Request.find(
                And(
                    Request.status == RequestStatus.PENDING,
                    LT(Request.expiresAt, current_time)
                )
            ).to_list()
            
            expired_count = len(expired_requests)
            
            if expired_count > 0:
                print(f"Found {expired_count} expired requests to process")
                
                # Update each request status to EXPIRED and create audit log
                for request in expired_requests:
                    # Update status to EXPIRED
                    # Validates Requirement 12.3
                    request.status = RequestStatus.EXPIRED
                    await request.save()
                    
                    # Create audit log entry with action type REQUEST_EXPIRED
                    # Validates Requirement 12.4
                    audit_log = AuditLog(
                        userId=request.requesterId,
                        action=ActionType.REQUEST_EXPIRED,
                        resourceType="Request",
                        resourceId=str(request.id),
                        metadata={
                            "targetUserId": str(request.targetUserId),
                            "targetVehicle": request.targetVehicle,
                            "expiresAt": request.expiresAt.isoformat(),
                            "expiredAt": current_time.isoformat()
                        }
                    )
                    await audit_log.insert()
                
                print(f"Successfully expired {expired_count} requests")
            
            return expired_count
            
        except Exception as e:
            print(f"Error expiring requests: {e}")
            raise


# Service instance
request_expiration_service = RequestExpirationService()


def run_expiration_job():
    """
    Job function to be called by the scheduler.
    
    This function is called every 5 minutes by APScheduler.
    
    **Validates Requirement**: 12.1
    """
    try:
        print(f"[{now_ist().isoformat()}] Running request expiration job...")
        # Run async function in sync context
        expired_count = asyncio.run(request_expiration_service.expire_pending_requests())
        print(f"[{now_ist().isoformat()}] Request expiration job completed. Expired {expired_count} requests.")
    except Exception as e:
        print(f"[{now_ist().isoformat()}] Request expiration job failed: {e}")
