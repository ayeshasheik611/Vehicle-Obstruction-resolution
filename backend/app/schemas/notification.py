"""
Notification API schemas
Validates: Requirements 16.1, 16.2, 16.3
"""
from pydantic import BaseModel, Field
from enum import Enum


class PlatformEnum(str, Enum):
    """Device platform enumeration"""
    IOS = "IOS"
    ANDROID = "ANDROID"


class RegisterDeviceRequest(BaseModel):
    """
    Request schema for device token registration
    
    Validates:
    - Requirement 16.1: Accept FCM token
    - Requirement 16.3: Accept platform type
    """
    fcmToken: str = Field(
        ...,
        min_length=1,
        max_length=255,
        description="Firebase Cloud Messaging token"
    )
    platform: PlatformEnum = Field(
        ...,
        description="Device platform (iOS or Android)"
    )
    
    class Config:
        json_schema_extra = {
            "example": {
                "fcmToken": "dGhpcyBpcyBhIGZha2UgdG9rZW4gZm9yIGV4YW1wbGU",
                "platform": "ANDROID"
            }
        }


class RegisterDeviceResponse(BaseModel):
    """
    Response schema for device token registration
    
    Validates:
    - Requirement 16.1: Confirm token storage
    """
    success: bool = Field(
        ...,
        description="Whether registration was successful"
    )
    message: str = Field(
        ...,
        description="Success or error message"
    )
    
    class Config:
        json_schema_extra = {
            "example": {
                "success": True,
                "message": "Device registered successfully"
            }
        }
