"""
Request Service
Handles call request creation, response, history, and expiration

Validates: Requirements 8.1-8.13, 11.1-11.10, 12.1-12.5, 13.1-13.7
"""
from uuid import UUID
from datetime import datetime, timedelta
from typing import Optional, List, Tuple
from loguru import logger
from beanie.operators import Or, And, LT

from app.models.request import Request, RequestStatus, ResponseType
from app.models.user import User
from app.services.rate_limit_service import get_rate_limit_service
from app.services.notification_service import notification_service
from app.models.audit_log import ActionType, AuditLog
from app.utils.vehicle_validation import mask_vehicle_number
from app.utils.datetime import now_ist


class RequestService:
    """Service for managing call requests between users"""
    
    REQUEST_EXPIRY_MINUTES = 30
    
    async def create_request(
        self,
        requester_id: UUID,
        target_vehicle: str,
        message: Optional[str] = None
    ) -> Tuple[bool, str, Optional[Request]]:
        """Create a call request to a vehicle owner"""
        rate_limit_service = get_rate_limit_service()
        rate_limit_status = rate_limit_service.check_rate_limit(requester_id)
        
        if not rate_limit_status.allowed:
            logger.warning(f"Rate limit exceeded for user {requester_id}")
            return (False, f"Rate limit exceeded. Try again at {rate_limit_status.reset_time.isoformat()}", None)
        
        normalized_vehicle = target_vehicle.strip().upper()
        target_user = await User.find_one(User.vehicleNumber == normalized_vehicle)
        
        if not target_user:
            logger.info(f"Vehicle not found: {normalized_vehicle}")
            return (False, "Vehicle not registered in system", None)
        
        if requester_id == target_user.id:
            logger.warning(f"User {requester_id} attempted self-request")
            return (False, "Cannot send request to your own vehicle", None)
        
        if target_user.isBanned:
            logger.info(f"Target user {target_user.id} is banned")
            return (False, "Unable to send request to this user", None)
        
        current_time = now_ist()
        expiry_time = current_time + timedelta(minutes=self.REQUEST_EXPIRY_MINUTES)
        
        request = Request(
            requesterId=requester_id,
            targetUserId=target_user.id,
            targetVehicle=normalized_vehicle,
            status=RequestStatus.PENDING,
            createdAt=current_time,
            expiresAt=expiry_time,
            responseMessage=message
        )
        
        try:
            await request.insert()
            logger.info(f"Request created: {request.id} from {requester_id} to {target_user.id}")
        except Exception as e:
            logger.error(f"Failed to create request: {e}")
            return (False, "Failed to create request. Please try again.", None)
        
        try:
            notification_result = await notification_service.send_call_request_notification(
                target_user_id=target_user.id,
                request_id=request.id,
                vehicle_number=normalized_vehicle,
                requester_id=requester_id
            )
            
            if not notification_result.success:
                logger.warning(f"Notification failed for request {request.id}: {notification_result.error_message}")
        except Exception as e:
            logger.error(f"Notification error for request {request.id}: {e}")
        
        rate_limit_service.increment_request_count(requester_id)
        
        try:
            audit_log = AuditLog(
                userId=requester_id,
                action=ActionType.REQUEST_CREATE,
                resourceType="Request",
                resourceId=str(request.id),
                metadata={
                    "target_user_id": str(target_user.id),
                    "target_vehicle": normalized_vehicle,
                    "expires_at": expiry_time.isoformat()
                }
            )
            await audit_log.insert()
        except Exception as e:
            logger.error(f"Failed to create audit log: {e}")
        
        return (True, "Request sent successfully", request)
    
    async def respond_to_request(
        self,
        request_id: UUID,
        user_id: UUID,
        response_type: ResponseType,
        response_message: Optional[str] = None
    ) -> Tuple[bool, str, Optional[Request]]:
        """Respond to a call request"""
        request = await Request.find_one(Request.id == request_id)
        
        if not request:
            return (False, "Request not found", None)
        
        if request.targetUserId != user_id:
            logger.warning(f"User {user_id} attempted to respond to request {request_id} belonging to {request.targetUserId}")
            return (False, "Unauthorized to respond to this request", None)
        
        if request.status != RequestStatus.PENDING:
            return (False, f"Request is already {request.status.value}", None)
        
        current_time = now_ist()
        if current_time >= request.expiresAt:
            request.status = RequestStatus.EXPIRED
            await request.save()
            logger.info(f"Request {request_id} has expired")
            return (False, "Request has expired", None)
        
        request.status = RequestStatus.RESPONDED
        request.respondedAt = current_time
        request.response = response_type
        if response_message:
            request.responseMessage = response_message
        
        try:
            await request.save()
            logger.info(f"Request {request_id} responded with {response_type.value}")
        except Exception as e:
            logger.error(f"Failed to update request: {e}")
            return (False, "Failed to record response. Please try again.", None)
        
        try:
            notification_result = await notification_service.send_response_notification(
                requester_id=request.requesterId,
                request_id=request.id,
                response_type=response_type.value,
                vehicle_number=request.targetVehicle
            )
            
            if not notification_result.success:
                logger.warning(f"Response notification failed for request {request_id}: {notification_result.error_message}")
        except Exception as e:
            logger.error(f"Notification error for response {request_id}: {e}")
        
        try:
            audit_log = AuditLog(
                userId=user_id,
                action=ActionType.REQUEST_RESPOND,
                resourceType="Request",
                resourceId=str(request.id),
                metadata={
                    "response_type": response_type.value,
                    "requester_id": str(request.requesterId)
                }
            )
            await audit_log.insert()
        except Exception as e:
            logger.error(f"Failed to create audit log: {e}")
        
        return (True, "Response recorded successfully", request)
    
    async def get_request_history(
        self,
        user_id: UUID,
        status_filter: Optional[RequestStatus] = None,
        limit: int = 20,
        offset: int = 0
    ) -> Tuple[List[dict], int, bool]:
        """Get request history for a user"""
        query_filter = Or(Request.requesterId == user_id, Request.targetUserId == user_id)
        
        if status_filter:
            query_filter = And(query_filter, Request.status == status_filter)
        
        total_count = await Request.find(query_filter).count()
        requests = await Request.find(query_filter).sort(-Request.createdAt).skip(offset).limit(limit).to_list()
        has_more = (offset + len(requests)) < total_count
        
        results = []
        for request in requests:
            request_type = "Sent" if request.requesterId == user_id else "Received"
            masked_vehicle = mask_vehicle_number(request.targetVehicle)
            
            results.append({
                "id": request.id,
                "type": request_type,
                "vehicleNumber": masked_vehicle,
                "status": request.status,
                "createdAt": request.createdAt,
                "expiresAt": request.expiresAt,
                "respondedAt": request.respondedAt,
                "response": request.response,
                "responseMessage": request.responseMessage
            })
        
        return (results, total_count, has_more)
    
    async def expire_old_requests(self) -> int:
        """Expire old pending requests (scheduled job)"""
        current_time = now_ist()
        
        expired_requests = await Request.find(
            And(Request.status == RequestStatus.PENDING, LT(Request.expiresAt, current_time))
        ).to_list()
        
        expired_count = 0
        
        for request in expired_requests:
            request.status = RequestStatus.EXPIRED
            await request.save()
            expired_count += 1
            
            try:
                audit_log = AuditLog(
                    userId=request.requesterId,
                    action=ActionType.REQUEST_EXPIRED,
                    resourceType="Request",
                    resourceId=str(request.id),
                    metadata={
                        "target_user_id": str(request.targetUserId),
                        "expired_at": current_time.isoformat()
                    }
                )
                await audit_log.insert()
            except Exception as e:
                logger.error(f"Failed to create audit log for expired request: {e}")
        
        logger.info(f"Expired {expired_count} requests")
        return expired_count


request_service = RequestService()
