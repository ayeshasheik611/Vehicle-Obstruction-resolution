"""
Authentication request and response schemas
Validates: Requirements 1.1, 1.2, 1.3, 1.4, 1.8
"""
from pydantic import BaseModel, Field, field_validator
from typing import Optional
from uuid import UUID


class RegisterRequest(BaseModel):
    """
    User registration request schema
    
    Validates:
    - Requirement 1.1: Vehicle number and password input
    - Requirement 1.4: Password length validation
    """
    vehicleNumber: str = Field(..., min_length=1, max_length=20, description="Vehicle registration number")
    password: str = Field(..., min_length=8, description="Password (minimum 8 characters)")
    
    @field_validator('vehicleNumber')
    @classmethod
    def validate_vehicle_number(cls, v: str) -> str:
        """Remove whitespace and convert to uppercase"""
        if not v or not v.strip():
            raise ValueError("Vehicle number cannot be empty")
        return v.strip().upper()
    
    @field_validator('password')
    @classmethod
    def validate_password(cls, v: str) -> str:
        """Validate password length"""
        if len(v) < 8:
            raise ValueError("Password must be at least 8 characters long")
        return v


class RegisterResponse(BaseModel):
    """
    User registration response schema
    
    Validates:
    - Requirement 1.8: Return JWT token and user ID
    """
    success: bool
    token: str
    userId: UUID
    message: str
    
    class Config:
        from_attributes = True


class LoginRequest(BaseModel):
    """User login request schema"""
    vehicleNumber: str = Field(..., min_length=1, max_length=20)
    password: str = Field(..., min_length=1)
    fcmToken: Optional[str] = Field(None, description="Firebase Cloud Messaging token")
    
    @field_validator('vehicleNumber')
    @classmethod
    def validate_vehicle_number(cls, v: str) -> str:
        """Remove whitespace and convert to uppercase"""
        if not v or not v.strip():
            raise ValueError("Vehicle number cannot be empty")
        return v.strip().upper()


class LoginResponse(BaseModel):
    """User login response schema"""
    success: bool
    token: str
    userId: UUID
    vehicleNumber: str
    message: str
    
    class Config:
        from_attributes = True
