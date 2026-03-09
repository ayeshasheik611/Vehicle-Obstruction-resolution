"""
Push Notification Service
Validates: Requirements 10.1-10.11, 21.6, 21.7
"""
from firebase_admin import messaging
from typing import Dict, Any, Optional
from uuid import UUID
from datetime import datetime
import time
from loguru import logger

from app.services.device_token_service import device_token_service
from app.utils.vehicle_validation import mask_vehicle_number
from app.models.audit_log import ActionType, AuditLog
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
    """Service for sending push notifications via Firebase Cloud Messaging"""
    
    PERMANENT_ERROR_CODES = [
        "INVALID_ARGUMENT",
        "UNREGISTERED",
        "SENDER_ID_MISMATCH",
        "QUOTA_EXCEEDED"
    ]
    
    TEMPORARY_ERROR_CODES = [
        "UNAVAILABLE",
        "INTERNAL",
        "DEADLINE_EXCEEDED"
    ]
    
    @staticmethod
    async def send_call_request_notification(
        target_user_id: UUID,
        request_id: UUID,
        vehicle_number: str,
        requester_id: UUID
    ) -> NotificationResult:
        """Send push notification for a call request"""
        tokens = await device_token_service.get_active_tokens(target_user_id)
        
        if not tokens:
            error_msg = "No active device tokens found for user"
            logger.warning(f"{error_msg}: {target_user_id}")
            
            audit_log = AuditLog(
                userId=target_user_id,
                action=ActionType.NOTIFICATION_FAILED,
                resourceType="Request",
                resourceId=str(request_id),
                metadata={"error": error_msg, "reason": "no_tokens"}
            )
            await audit_log.insert()
            
            return NotificationResult(
                success=False,
                error_message=error_msg,
                failed_count=0
            )
        
        masked_vehicle = mask_vehicle_number(vehicle_number)
        
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
                await device_token_service.update_last_used(token.fcmToken)
                logger.info(f"Notification delivered to token {token.fcmToken[:20]}... (message_id: {message_id})")
            else:
                failed_count += 1
                if error_code in NotificationService.PERMANENT_ERROR_CODES:
                    await device_token_service.mark_token_inactive(token.fcmToken)
                    logger.warning(f"Marked token inactive due to permanent error: {error_code} - {token.fcmToken[:20]}...")
                else:
                    logger.error(f"Failed to deliver notification: {error_code} - {token.fcmToken[:20]}...")
        
        overall_success = delivered_count > 0
        
        if overall_success:
            audit_log = AuditLog(
                userId=target_user_id,
                action=ActionType.NOTIFICATION_SENT,
                resourceType="Request",
                resourceId=str(request_id),
                metadata={
                    "delivered_count": delivered_count,
                    "failed_count": failed_count,
                    "total_tokens": len(tokens),
                    "message_id": last_message_id
                }
            )
        else:
            audit_log = AuditLog(
                userId=target_user_id,
                action=ActionType.NOTIFICATION_FAILED,
                resourceType="Request",
                resourceId=str(request_id),
                metadata={
                    "delivered_count": delivered_count,
                    "failed_count": failed_count,
                    "total_tokens": len(tokens),
                    "reason": "all_deliveries_failed"
                }
            )
        await audit_log.insert()
        
        return NotificationResult(
            success=overall_success,
            message_id=last_message_id,
            error_message=None if overall_success else "All notification deliveries failed",
            delivered_count=delivered_count,
            failed_count=failed_count
        )
    
    @staticmethod
    async def send_response_notification(
        requester_id: UUID,
        request_id: UUID,
        response_type: str,
        vehicle_number: str
    ) -> NotificationResult:
        """Send push notification when a request receives a response"""
        tokens = await device_token_service.get_active_tokens(requester_id)
        
        if not tokens:
            error_msg = "No active device tokens found for requester"
            logger.warning(f"{error_msg}: {requester_id}")
            
            audit_log = AuditLog(
                userId=requester_id,
                action=ActionType.NOTIFICATION_FAILED,
                resourceType="Request",
                resourceId=str(request_id),
                metadata={"error": error_msg, "reason": "no_tokens"}
            )
            await audit_log.insert()
            
            return NotificationResult(
                success=False,
                error_message=error_msg,
                failed_count=0
            )
        
        masked_vehicle = mask_vehicle_number(vehicle_number)
        
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
                await device_token_service.update_last_used(token.fcmToken)
            else:
                failed_count += 1
                if error_code in NotificationService.PERMANENT_ERROR_CODES:
                    await device_token_service.mark_token_inactive(token.fcmToken)
        
        overall_success = delivered_count > 0
        
        if overall_success:
            audit_log = AuditLog(
                userId=requester_id,
                action=ActionType.NOTIFICATION_SENT,
                resourceType="Request",
                resourceId=str(request_id),
                metadata={
                    "notification_type": "response",
                    "response_type": response_type,
                    "delivered_count": delivered_count,
                    "failed_count": failed_count
                }
            )
        else:
            audit_log = AuditLog(
                userId=requester_id,
                action=ActionType.NOTIFICATION_FAILED,
                resourceType="Request",
                resourceId=str(request_id),
                metadata={
                    "notification_type": "response",
                    "failed_count": failed_count,
                    "reason": "all_deliveries_failed"
                }
            )
        await audit_log.insert()
        
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
        """Send notification with exponential backoff retry logic"""
        for attempt in range(max_retries):
            try:
                message_id = messaging.send(message)
                return (True, message_id, None)
                
            except messaging.UnregisteredError:
                return (False, None, "UNREGISTERED")
                
            except messaging.SenderIdMismatchError:
                return (False, None, "SENDER_ID_MISMATCH")
                
            except messaging.QuotaExceededError:
                return (False, None, "QUOTA_EXCEEDED")
                
            except messaging.InvalidArgumentError as e:
                logger.error(f"Invalid argument error: {e}")
                return (False, None, "INVALID_ARGUMENT")
                
            except (messaging.InternalError, messaging.UnavailableError) as e:
                if attempt < max_retries - 1:
                    backoff_time = 2 ** attempt
                    logger.warning(f"Temporary error on attempt {attempt + 1}/{max_retries}: {e}. Retrying in {backoff_time}s...")
                    time.sleep(backoff_time)
                else:
                    logger.error(f"Max retries reached. Last error: {e}")
                    error_code = "UNAVAILABLE" if isinstance(e, messaging.UnavailableError) else "INTERNAL"
                    return (False, None, error_code)
                    
            except Exception as e:
                logger.error(f"Unexpected error sending notification: {e}")
                return (False, None, "UNKNOWN_ERROR")
        
        return (False, None, "MAX_RETRIES_EXCEEDED")


# Service instance
notification_service = NotificationService()
