"""
Notification endpoints
Validates: Requirements 16.1, 16.2, 16.3
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from loguru import logger

from app.core.database import get_db
from app.api.dependencies import get_current_user
from app.schemas.notification import RegisterDeviceRequest, RegisterDeviceResponse
from app.services.device_token_service import device_token_service
from app.models.user import User
from app.models.device_token import Platform


router = APIRouter()


@router.post("/register", response_model=RegisterDeviceResponse, status_code=status.HTTP_200_OK)
async def register_device(
    request_data: RegisterDeviceRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Register a device token for push notifications
    
    Validates:
    - Requirement 16.1: Store FCM token in device_tokens table
    - Requirement 16.2: Allow multiple device tokens per user
    - Requirement 16.3: Record platform type (iOS/Android)
    
    Args:
        request_data: Device registration request with FCM token and platform
        current_user: Authenticated user from JWT token
        db: Database session
        
    Returns:
        RegisterDeviceResponse with success status and message
        
    Raises:
        HTTPException 400: Invalid FCM token
        HTTPException 401: Unauthorized (invalid token)
        HTTPException 500: Server error
    """
    try:
        # Validate FCM token is not empty
        if not request_data.fcmToken or len(request_data.fcmToken.strip()) == 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="FCM token cannot be empty"
            )
        
        # Convert platform enum to model enum
        platform = Platform[request_data.platform.value]
        
        # Register or update device token (Requirement 16.1, 16.2, 16.3)
        device_token = device_token_service.register_device_token(
            db=db,
            user_id=current_user.id,
            fcm_token=request_data.fcmToken,
            platform=platform
        )
        
        logger.info(
            f"Device token registered for user {current_user.id} "
            f"(platform: {request_data.platform})"
        )
        
        return RegisterDeviceResponse(
            success=True,
            message="Device registered successfully"
        )
        
    except ValueError as e:
        # Invalid platform enum value
        logger.error(f"Invalid platform value: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid platform value: {str(e)}"
        )
        
    except Exception as e:
        # Unexpected error
        logger.error(f"Failed to register device token: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to register device token"
        )
