"""
Push Notification Service
Validates: Requirements 10.1-10.11, 21.6, 21.7
"""
from sqlalchemy.orm import Session
from firebase_admin import messaging
from typing import Dict, Any, Optional
from uuid import UUID
from datetime import datetime
import time
from loguru import logger

from app.services.device_token_service import device_token_service
from app.services.audit_service import audit_service
from app.utils.vehicle_validation import mask_vehicle_number
from app.models.audit_log import ActionType
from app.utils.datetime import now_ist


class NotificationResult:
    """Result of notification sending operation"""
    
    def __init__(
        self,
        success: bool,
        message_id: Optional[str] = None,
        error_message: Optional[str] = None,
        delivered_count: int = 0,
        failed_count: int = 0
    ):
        self.success = success
        self.message_id = message_id
        self.error_message = error_message
        self.delivered_count = delivered_count
        self.failed_count = failed_count


class NotificationService:
    """
    Service for sending push notifications via Firebase Cloud Messaging
    
    Validates:
    - Requirement 10.1: Retrieve active FCM tokens for target user
    - Requirement 10.2: Return failure if no active tokens found
    - Requirement 10.3: Mask vehicle number before including in notification
    - Requirement 10.4: Prepare notification payload with title, body, and data
    - Requirement 10.5: Set notification priority to high
    - Requirement 10.6: Send notification to each active FCM token
    - Requirement 10.7: Update lastUsedAt on successful delivery
    - Requirement 10.8: Mark token inactive on permanent errors
    - Requirement 10.9: Retry up to 3 times with exponential backoff
    - Requirement 10.10: Create audit log entry with delivery status
    - Requirement 10.11: Return success if at least one notification delivered
    - Requirement 21.6: Log NOTIFICATION_SENT action
    - Requirement 21.7: Log NOTIFICATION_FAILED action
    """
    
    # Permanent error codes that should mark token as inactive
    PERMANENT_ERROR_CODES = [
        "INVALID_ARGUMENT",
        "UNREGISTERED",
        "SENDER_ID_MISMATCH",
        "QUOTA_EXCEEDED"
    ]
    
    # Temporary error codes that should trigger retry
    TEMPORARY_ERROR_CODES = [
        "UNAVAILABLE",
        "INTERNAL",
        "DEADLINE_EXCEEDED"
    ]
    
    @staticmethod
    def send_call_request_notification(
        db: Session,
        target_user_id: UUID,
        request_id: UUID,
        vehicle_number: str,
        requester_id: UUID
    ) -> NotificationResult:
        """
        Send push notification for a call request
        
        Validates:
        - Requirements 10.1-10.11: Complete notification delivery flow
        - Requirement 21.6: Audit log for successful delivery
        - Requirement 21.7: Audit log for failed delivery
        
        Args:
            db: Database session
            target_user_id: UUID of user to notify
            request_id: UUID of the call request
            vehicle_number: Vehicle number (will be masked)
            requester_id: UUID of user who created the request
            
        Returns:
            NotificationResult: Result of notification operation
        """
        # Step 1: Retrieve all active FCM tokens (Requirement 10.1)
        tokens = device_token_service.get_active_tokens(db, target_user_id)
        
        # Step 2: Check if tokens exist (Requirement 10.2)
        if not tokens:
            error_msg = "No active device tokens found for user"
            logger.warning(f"{error_msg}: {target_user_id}")
            
            # Create audit log for failure (Requirement 21.7)
            audit_service.log_action(
                db=db,
                user_id=target_user_id,
                action=ActionType.NOTIFICATION_FAILED,
                resource_type="Request",
                resource_id=request_id,
                metadata={"error": error_msg, "reason": "no_tokens"}
            )
            
            return NotificationResult(
                success=False,
                error_message=error_msg,
                failed_count=0
            )
        
        # Step 3: Mask vehicle number for privacy (Requirement 10.3)
        masked_vehicle = mask_vehicle_number(vehicle_number)
        
        # Step 4: Prepare notification payload (Requirement 10.4)
        notification_payload = messaging.Notification(
            title="Vehicle Call Request",
            body=f"Someone needs you to move vehicle {masked_vehicle}"
        )
        
        data_payload = {
            "type": "CALL_REQUEST",
            "requestId": str(request_id),
            "vehicleNumber": masked_vehicle,
            "timestamp": now_ist().isoformat()
        }
        
        # Step 5: Send to each device token (Requirement 10.6)
        delivered_count = 0
        failed_count = 0
        last_message_id = None
        
        for token in tokens:
            # Create message with high priority (Requirement 10.5)
            message = messaging.Message(
                notification=notification_payload,
                data=data_payload,
                token=token.fcmToken,
                android=messaging.AndroidConfig(
                    priority="high"
                ),
                apns=messaging.APNSConfig(
                    headers={"apns-priority": "10"}
                )
            )
            
            # Send with retry logic (Requirement 10.9)
            success, message_id, error_code = NotificationService._send_with_retry(
                message=message,
                max_retries=3
            )
            
            if success:
                delivered_count += 1
                last_message_id = message_id
                
                # Update lastUsedAt timestamp (Requirement 10.7)
                device_token_service.update_last_used(db, token.fcmToken)
                
                logger.info(
                    f"Notification delivered to token {token.fcmToken[:20]}... "
                    f"(message_id: {message_id})"
                )
            else:
                failed_count += 1
                
                # Check if error is permanent (Requirement 10.8)
                if error_code in NotificationService.PERMANENT_ERROR_CODES:
                    device_token_service.mark_token_inactive(db, token.fcmToken)
                    logger.warning(
                        f"Marked token inactive due to permanent error: "
                        f"{error_code} - {token.fcmToken[:20]}..."
                    )
                else:
                    logger.error(
                        f"Failed to deliver notification: {error_code} - "
                        f"{token.fcmToken[:20]}..."
                    )
        
        # Step 6: Determine overall success (Requirement 10.11)
        overall_success = delivered_count > 0
        
        # Step 7: Create audit log entry (Requirement 10.10, 21.6, 21.7)
        if overall_success:
            audit_service.log_action(
                db=db,
                user_id=target_user_id,
                action=ActionType.NOTIFICATION_SENT,
                resource_type="Request",
                resource_id=request_id,
                metadata={
                    "delivered_count": delivered_count,
                    "failed_count": failed_count,
                    "total_tokens": len(tokens),
                    "message_id": last_message_id
                }
            )
        else:
            audit_service.log_action(
                db=db,
                user_id=target_user_id,
                action=ActionType.NOTIFICATION_FAILED,
                resource_type="Request",
                resource_id=request_id,
                metadata={
                    "delivered_count": delivered_count,
                    "failed_count": failed_count,
                    "total_tokens": len(tokens),
                    "reason": "all_deliveries_failed"
                }
            )
        
        return NotificationResult(
            success=overall_success,
            message_id=last_message_id,
            error_message=None if overall_success else "All notification deliveries failed",
            delivered_count=delivered_count,
            failed_count=failed_count
        )
    
    @staticmethod
    def send_response_notification(
        db: Session,
        requester_id: UUID,
        request_id: UUID,
        response_type: str,
        vehicle_number: str
    ) -> NotificationResult:
        """
        Send push notification when a request receives a response
        
        Args:
            db: Database session
            requester_id: UUID of original requester
            request_id: UUID of the request
            response_type: Type of response (MESSAGE, ON_MY_WAY, CANNOT_MOVE)
            vehicle_number: Vehicle number (will be masked)
            
        Returns:
            NotificationResult: Result of notification operation
        """
        # Retrieve active tokens
        tokens = device_token_service.get_active_tokens(db, requester_id)
        
        if not tokens:
            error_msg = "No active device tokens found for requester"
            logger.warning(f"{error_msg}: {requester_id}")
            
            audit_service.log_action(
                db=db,
                user_id=requester_id,
                action=ActionType.NOTIFICATION_FAILED,
                resource_type="Request",
                resource_id=request_id,
                metadata={"error": error_msg, "reason": "no_tokens"}
            )
            
            return NotificationResult(
                success=False,
                error_message=error_msg,
                failed_count=0
            )
        
        # Mask vehicle number
        masked_vehicle = mask_vehicle_number(vehicle_number)
        
        # Prepare notification based on response type
        response_messages = {
            "MESSAGE": f"Vehicle {masked_vehicle} owner has responded to your request",
            "ON_MY_WAY": f"Vehicle {masked_vehicle} owner is on their way",
            "CANNOT_MOVE": f"Vehicle {masked_vehicle} owner cannot move right now"
        }
        
        notification_payload = messaging.Notification(
            title="Request Response",
            body=response_messages.get(response_type, "You received a response")
        )
        
        data_payload = {
            "type": "REQUEST_RESPONSE",
            "requestId": str(request_id),
            "responseType": response_type,
            "vehicleNumber": masked_vehicle,
            "timestamp": now_ist().isoformat()
        }
        
        # Send to each device token
        delivered_count = 0
        failed_count = 0
        last_message_id = None
        
        for token in tokens:
            message = messaging.Message(
                notification=notification_payload,
                data=data_payload,
                token=token.fcmToken,
                android=messaging.AndroidConfig(priority="high"),
                apns=messaging.APNSConfig(headers={"apns-priority": "10"})
            )
            
            success, message_id, error_code = NotificationService._send_with_retry(
                message=message,
                max_retries=3
            )
            
            if success:
                delivered_count += 1
                last_message_id = message_id
                device_token_service.update_last_used(db, token.fcmToken)
            else:
                failed_count += 1
                if error_code in NotificationService.PERMANENT_ERROR_CODES:
                    device_token_service.mark_token_inactive(db, token.fcmToken)
        
        overall_success = delivered_count > 0
        
        # Create audit log
        if overall_success:
            audit_service.log_action(
                db=db,
                user_id=requester_id,
                action=ActionType.NOTIFICATION_SENT,
                resource_type="Request",
                resource_id=request_id,
                metadata={
                    "notification_type": "response",
                    "response_type": response_type,
                    "delivered_count": delivered_count,
                    "failed_count": failed_count
                }
            )
        else:
            audit_service.log_action(
                db=db,
                user_id=requester_id,
                action=ActionType.NOTIFICATION_FAILED,
                resource_type="Request",
                resource_id=request_id,
                metadata={
                    "notification_type": "response",
                    "failed_count": failed_count,
                    "reason": "all_deliveries_failed"
                }
            )
        
        return NotificationResult(
            success=overall_success,
            message_id=last_message_id,
            error_message=None if overall_success else "All notification deliveries failed",
            delivered_count=delivered_count,
            failed_count=failed_count
        )
    
    @staticmethod
    def _send_with_retry(
        message: messaging.Message,
        max_retries: int = 3
    ) -> tuple[bool, Optional[str], Optional[str]]:
        """
        Send notification with exponential backoff retry logic
        
        Validates:
        - Requirement 10.9: Retry up to 3 times with exponential backoff
        
        Args:
            message: Firebase message to send
            max_retries: Maximum number of retry attempts
            
        Returns:
            Tuple of (success, message_id, error_code)
        """
        for attempt in range(max_retries):
            try:
                # Send the message
                message_id = messaging.send(message)
                return (True, message_id, None)
                
            except messaging.UnregisteredError:
                # Permanent error - token is invalid
                return (False, None, "UNREGISTERED")
                
            except messaging.SenderIdMismatchError:
                # Permanent error - wrong sender
                return (False, None, "SENDER_ID_MISMATCH")
                
            except messaging.QuotaExceededError:
                # Permanent error - quota exceeded
                return (False, None, "QUOTA_EXCEEDED")
                
            except messaging.InvalidArgumentError as e:
                # Permanent error - invalid argument
                logger.error(f"Invalid argument error: {e}")
                return (False, None, "INVALID_ARGUMENT")
                
            except (messaging.InternalError, messaging.UnavailableError) as e:
                # Temporary error - retry with backoff
                if attempt < max_retries - 1:
                    # Exponential backoff: 1s, 2s, 4s
                    backoff_time = 2 ** attempt
                    logger.warning(
                        f"Temporary error on attempt {attempt + 1}/{max_retries}: {e}. "
                        f"Retrying in {backoff_time}s..."
                    )
                    time.sleep(backoff_time)
                else:
                    # Max retries reached
                    logger.error(f"Max retries reached. Last error: {e}")
                    error_code = "UNAVAILABLE" if isinstance(e, messaging.UnavailableError) else "INTERNAL"
                    return (False, None, error_code)
                    
            except Exception as e:
                # Unknown error
                logger.error(f"Unexpected error sending notification: {e}")
                return (False, None, "UNKNOWN_ERROR")
        
        # Should not reach here, but just in case
        return (False, None, "MAX_RETRIES_EXCEEDED")


# Service instance
notification_service = NotificationService()
