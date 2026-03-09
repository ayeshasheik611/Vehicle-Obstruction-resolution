"""
Request Service
Handles call request creation, response, history, and expiration

Validates: Requirements 8.1-8.13, 11.1-11.10, 12.1-12.5, 13.1-13.7
"""
from sqlalchemy.orm import Session
from sqlalchemy import or_, and_
from uuid import UUID
from datetime import datetime, timedelta
from typing import Optional, List, Tuple
from loguru import logger

from app.models.request import Request, RequestStatus, ResponseType
from app.models.user import User
from app.services.rate_limit_service import get_rate_limit_service
from app.services.notification_service import notification_service
from app.services.audit_service import audit_service
from app.models.audit_log import ActionType
from app.utils.vehicle_validation import mask_vehicle_number
from app.utils.datetime import now_ist


class RequestService:
    """
    Service for managing call requests between users
    
    Validates:
    - Requirements 8.1-8.13: Call request creation
    - Requirements 11.1-11.10: Request response
    - Requirements 12.1-12.5: Request expiration
    - Requirements 13.1-13.7: Request history
    """
    
    # Request expiration time in minutes
    REQUEST_EXPIRY_MINUTES = 30
    
    def create_request(
        self,
        db: Session,
        requester_id: UUID,
        target_vehicle: str,
        message: Optional[str] = None
    ) -> Tuple[bool, str, Optional[Request]]:
        """
        Create a call request to a vehicle owner
        
        Validates:
        - Requirement 8.1: Check user's rate limit status
        - Requirement 8.2: Reject if rate limit exceeded
        - Requirement 8.3: Query database for target vehicle owner
        - Requirement 8.4: Reject if target vehicle not registered
        - Requirement 8.5: Reject if requester equals target user
        - Requirement 8.6: Reject if target user is banned
        - Requirement 8.7: Generate unique UUID for request
        - Requirement 8.8: Set expiry time to 30 minutes
        - Requirement 8.9: Create request record with PENDING status
        - Requirement 8.10: Store request in database
        - Requirement 8.11: Send push notification to target user
        - Requirement 8.12: Increment rate limit counter
        - Requirement 8.13: Create audit log entry
        
        Args:
            db: Database session
            requester_id: UUID of user creating the request
            target_vehicle: Vehicle number to send request to
            message: Optional message from requester
            
        Returns:
            Tuple of (success, message, request_object)
        """
        # Step 1: Check rate limit (Requirement 8.1)
        rate_limit_service = get_rate_limit_service()
        rate_limit_status = rate_limit_service.check_rate_limit(requester_id)
        
        # Step 2: Reject if rate limit exceeded (Requirement 8.2)
        if not rate_limit_status.allowed:
            logger.warning(f"Rate limit exceeded for user {requester_id}")
            return (
                False,
                f"Rate limit exceeded. Try again at {rate_limit_status.reset_time.isoformat()}",
                None
            )
        
        # Step 3: Query database for target vehicle owner (Requirement 8.3)
        # Normalize vehicle number
        normalized_vehicle = target_vehicle.strip().upper()
        target_user = db.query(User).filter(
            User.vehicleNumber == normalized_vehicle
        ).first()
        
        # Step 4: Reject if target vehicle not registered (Requirement 8.4)
        if not target_user:
            logger.info(f"Vehicle not found: {normalized_vehicle}")
            return (
                False,
                "Vehicle not registered in system",
                None
            )
        
        # Step 5: Reject if requester equals target user (Requirement 8.5)
        if requester_id == target_user.id:
            logger.warning(f"User {requester_id} attempted self-request")
            return (
                False,
                "Cannot send request to your own vehicle",
                None
            )
        
        # Step 6: Reject if target user is banned (Requirement 8.6)
        if target_user.isBanned:
            logger.info(f"Target user {target_user.id} is banned")
            return (
                False,
                "Unable to send request to this user",
                None
            )
        
        # Step 7: Generate unique UUID for request (Requirement 8.7)
        # Step 8: Set expiry time to 30 minutes (Requirement 8.8)
        current_time = now_ist()
        expiry_time = current_time + timedelta(minutes=self.REQUEST_EXPIRY_MINUTES)
        
        # Step 9: Create request record with PENDING status (Requirement 8.9)
        request = Request(
            requesterId=requester_id,
            targetUserId=target_user.id,
            targetVehicle=normalized_vehicle,
            status=RequestStatus.PENDING,
            createdAt=current_time,
            expiresAt=expiry_time,
            responseMessage=message
        )
        
        # Step 10: Store request in database (Requirement 8.10)
        try:
            db.add(request)
            db.commit()
            db.refresh(request)
            
            logger.info(
                f"Request created: {request.id} from {requester_id} to {target_user.id}"
            )
            
        except Exception as e:
            db.rollback()
            logger.error(f"Failed to create request: {e}")
            return (
                False,
                "Failed to create request. Please try again.",
                None
            )
        
        # Step 11: Send push notification to target user (Requirement 8.11)
        try:
            notification_result = notification_service.send_call_request_notification(
                db=db,
                target_user_id=target_user.id,
                request_id=request.id,
                vehicle_number=normalized_vehicle,
                requester_id=requester_id
            )
            
            if not notification_result.success:
                logger.warning(
                    f"Notification failed for request {request.id}: "
                    f"{notification_result.error_message}"
                )
                # Continue anyway - request is created
                
        except Exception as e:
            logger.error(f"Notification error for request {request.id}: {e}")
            # Continue anyway - request is created
        
        # Step 12: Increment rate limit counter (Requirement 8.12)
        rate_limit_service.increment_request_count(requester_id)
        
        # Step 13: Create audit log entry (Requirement 8.13)
        try:
            audit_service.log_action(
                db=db,
                user_id=requester_id,
                action=ActionType.REQUEST_CREATE,
                resource_type="Request",
                resource_id=request.id,
                metadata={
                    "target_user_id": str(target_user.id),
                    "target_vehicle": normalized_vehicle,
                    "expires_at": expiry_time.isoformat()
                }
            )
        except Exception as e:
            logger.error(f"Failed to create audit log: {e}")
            # Continue anyway
        
        return (
            True,
            "Request sent successfully",
            request
        )
    
    def respond_to_request(
        self,
        db: Session,
        request_id: UUID,
        user_id: UUID,
        response_type: ResponseType,
        response_message: Optional[str] = None
    ) -> Tuple[bool, str, Optional[Request]]:
        """
        Respond to a call request
        
        Validates:
        - Requirement 11.1: Validate request ID exists
        - Requirement 11.2: Verify responding user is target user
        - Requirement 11.3: Check request status is PENDING
        - Requirement 11.4: Check request has not expired
        - Requirement 11.5: Reject if expired with 410 Gone
        - Requirement 11.6: Update request status to RESPONDED
        - Requirement 11.7: Set respondedAt timestamp
        - Requirement 11.8: Store response type
        - Requirement 11.9: Send notification to requester
        - Requirement 11.10: Create audit log entry
        
        Args:
            db: Database session
            request_id: UUID of the request
            user_id: UUID of user responding
            response_type: Type of response
            response_message: Optional response message
            
        Returns:
            Tuple of (success, message, request_object)
        """
        # Step 1: Validate request ID exists (Requirement 11.1)
        request = db.query(Request).filter(Request.id == request_id).first()
        
        if not request:
            return (False, "Request not found", None)
        
        # Step 2: Verify responding user is target user (Requirement 11.2)
        if request.targetUserId != user_id:
            logger.warning(
                f"User {user_id} attempted to respond to request {request_id} "
                f"belonging to {request.targetUserId}"
            )
            return (False, "Unauthorized to respond to this request", None)
        
        # Step 3: Check request status is PENDING (Requirement 11.3)
        if request.status != RequestStatus.PENDING:
            return (
                False,
                f"Request is already {request.status.value}",
                None
            )
        
        # Step 4: Check request has not expired (Requirement 11.4)
        current_time = now_ist()
        if current_time >= request.expiresAt:
            # Step 5: Reject if expired (Requirement 11.5)
            # Update status to EXPIRED
            request.status = RequestStatus.EXPIRED
            db.commit()
            
            logger.info(f"Request {request_id} has expired")
            return (False, "Request has expired", None)
        
        # Step 6: Update request status to RESPONDED (Requirement 11.6)
        request.status = RequestStatus.RESPONDED
        
        # Step 7: Set respondedAt timestamp (Requirement 11.7)
        request.respondedAt = current_time
        
        # Step 8: Store response type (Requirement 11.8)
        request.response = response_type
        if response_message:
            request.responseMessage = response_message
        
        try:
            db.commit()
            db.refresh(request)
            
            logger.info(
                f"Request {request_id} responded with {response_type.value}"
            )
            
        except Exception as e:
            db.rollback()
            logger.error(f"Failed to update request: {e}")
            return (False, "Failed to record response. Please try again.", None)
        
        # Step 9: Send notification to requester (Requirement 11.9)
        try:
            notification_result = notification_service.send_response_notification(
                db=db,
                requester_id=request.requesterId,
                request_id=request.id,
                response_type=response_type.value,
                vehicle_number=request.targetVehicle
            )
            
            if not notification_result.success:
                logger.warning(
                    f"Response notification failed for request {request_id}: "
                    f"{notification_result.error_message}"
                )
                # Continue anyway - response is recorded
                
        except Exception as e:
            logger.error(f"Notification error for response {request_id}: {e}")
            # Continue anyway
        
        # Step 10: Create audit log entry (Requirement 11.10)
        try:
            audit_service.log_action(
                db=db,
                user_id=user_id,
                action=ActionType.REQUEST_RESPOND,
                resource_type="Request",
                resource_id=request.id,
                metadata={
                    "response_type": response_type.value,
                    "requester_id": str(request.requesterId)
                }
            )
        except Exception as e:
            logger.error(f"Failed to create audit log: {e}")
            # Continue anyway
        
        return (True, "Response recorded successfully", request)
    
    def get_request_history(
        self,
        db: Session,
        user_id: UUID,
        status_filter: Optional[RequestStatus] = None,
        limit: int = 20,
        offset: int = 0
    ) -> Tuple[List[dict], int, bool]:
        """
        Get request history for a user
        
        Validates:
        - Requirement 13.1: Accept optional status filter
        - Requirement 13.2: Accept limit parameter (default 20)
        - Requirement 13.3: Accept offset parameter (default 0)
        - Requirement 13.4: Retrieve requests where user is requester or target
        - Requirement 13.5: Mask vehicle numbers in results
        - Requirement 13.6: Indicate whether request was sent or received
        - Requirement 13.7: Return total count and hasMore flag
        
        Args:
            db: Database session
            user_id: UUID of user
            status_filter: Optional status to filter by
            limit: Maximum number of results
            offset: Number of results to skip
            
        Returns:
            Tuple of (requests_list, total_count, has_more)
        """
        # Build query (Requirement 13.4)
        query = db.query(Request).filter(
            or_(
                Request.requesterId == user_id,
                Request.targetUserId == user_id
            )
        )
        
        # Apply status filter if provided (Requirement 13.1)
        if status_filter:
            query = query.filter(Request.status == status_filter)
        
        # Get total count (Requirement 13.7)
        total_count = query.count()
        
        # Apply pagination (Requirement 13.2, 13.3)
        requests = query.order_by(Request.createdAt.desc()).offset(offset).limit(limit).all()
        
        # Calculate hasMore flag (Requirement 13.7)
        has_more = (offset + len(requests)) < total_count
        
        # Format results (Requirement 13.5, 13.6)
        results = []
        for request in requests:
            # Determine if sent or received (Requirement 13.6)
            request_type = "Sent" if request.requesterId == user_id else "Received"
            
            # Mask vehicle number (Requirement 13.5)
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
    
    def expire_old_requests(self, db: Session) -> int:
        """
        Expire old pending requests (scheduled job)
        
        Validates:
        - Requirement 12.1: Run scheduled job every 5 minutes
        - Requirement 12.2: Query PENDING requests with expiresAt < current time
        - Requirement 12.3: Update status to EXPIRED
        - Requirement 12.4: Create audit log entries
        - Requirement 12.5: Do not send notifications
        
        Args:
            db: Database session
            
        Returns:
            Number of requests expired
        """
        current_time = now_ist()
        
        # Step 1: Query expired requests (Requirement 12.2)
        expired_requests = db.query(Request).filter(
            and_(
                Request.status == RequestStatus.PENDING,
                Request.expiresAt < current_time
            )
        ).all()
        
        expired_count = 0
        
        # Step 2: Update each request to EXPIRED (Requirement 12.3)
        for request in expired_requests:
            request.status = RequestStatus.EXPIRED
            expired_count += 1
            
            # Step 3: Create audit log entry (Requirement 12.4)
            try:
                audit_service.log_action(
                    db=db,
                    user_id=request.requesterId,
                    action=ActionType.REQUEST_EXPIRED,
                    resource_type="Request",
                    resource_id=request.id,
                    metadata={
                        "target_user_id": str(request.targetUserId),
                        "expired_at": current_time.isoformat()
                    }
                )
            except Exception as e:
                logger.error(f"Failed to create audit log for expired request: {e}")
        
        # Commit all changes
        try:
            db.commit()
            logger.info(f"Expired {expired_count} requests")
        except Exception as e:
            db.rollback()
            logger.error(f"Failed to expire requests: {e}")
            return 0
        
        # Requirement 12.5: Do not send notifications
        return expired_count


# Service instance
request_service = RequestService()
