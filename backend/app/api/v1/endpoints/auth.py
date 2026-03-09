"""
Authentication endpoints

This module provides user registration and login endpoints.

**Validates Requirements**: 1.1, 1.2, 1.3, 1.4, 1.5, 1.6, 1.7, 1.8, 1.9, 2.1, 2.2, 2.3, 2.4, 2.5, 2.6, 2.7, 2.8, 2.9, 21.1, 21.2
"""
from fastapi import APIRouter, Depends, HTTPException, status, Request
from datetime import datetime

from app.schemas.auth import RegisterRequest, RegisterResponse, LoginRequest, LoginResponse
from app.models.user import User
from app.models.audit_log import ActionType, AuditLog
from app.utils.auth import hash_password, create_access_token, verify_password
from app.utils.vehicle_validation import validate_vehicle_format, normalize_vehicle_number, get_format_requirements
from app.utils.datetime import now_ist


router = APIRouter()


@router.post("/register", response_model=RegisterResponse, status_code=status.HTTP_201_CREATED)
async def register(
    request: Request,
    register_data: RegisterRequest,
):
    """
    Register a new user with vehicle number and password.
    
    **Validates Requirements**:
    - 1.1: Validate vehicle number format using regex patterns
    - 1.2: Check vehicle uniqueness in database
    - 1.3: Reject registration if vehicle already exists
    - 1.4: Validate password length (minimum 8 characters)
    - 1.5: Hash password using bcrypt with 10 salt rounds
    - 1.6: Create user record with unique UUID
    - 1.7: Generate JWT token with 7-day expiration
    - 1.8: Return JWT token and user ID
    - 1.9: Create audit log entry for registration
    - 21.1: Audit log with action type USER_REGISTER
    
    Args:
        request: FastAPI request object (for audit logging)
        register_data: Registration request data (vehicle number and password)
        db: Database session
        
    Returns:
        RegisterResponse with success status, JWT token, user ID, and message
        
    Raises:
        HTTPException 400: Invalid vehicle number format
        HTTPException 409: Vehicle number already registered
        HTTPException 500: Server error
    """
    # Step 1: Normalize vehicle number
    normalized_vehicle = normalize_vehicle_number(register_data.vehicleNumber)
    
    # Step 2: Validate vehicle number format (Requirement 1.1)
    if not validate_vehicle_format(normalized_vehicle):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "error": "Invalid vehicle number format",
                "requirements": get_format_requirements()
            }
        )
    
    # Step 3: Check vehicle uniqueness in database (Requirement 1.2)
    existing_user = await User.find_one(User.vehicleNumber == normalized_vehicle)
    
    if existing_user:
        # Requirement 1.3: Reject registration if vehicle already exists
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Vehicle number already registered"
        )
    
    # Step 4: Password validation is handled by Pydantic schema (Requirement 1.4)
    # The RegisterRequest schema validates minimum 8 characters
    
    # Step 5: Hash password using bcrypt (Requirement 1.5)
    password_hash = hash_password(register_data.password)
    
    # Step 6: Create user record with unique UUID (Requirement 1.6)
    new_user = User(
        vehicleNumber=normalized_vehicle,
        passwordHash=password_hash,
        isActive=True,
        isBanned=False
    )
    
    try:
        await new_user.insert()
    except Exception as e:
        # Handle race condition where vehicle was registered between check and insert
        if "duplicate" in str(e).lower():
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Vehicle number already registered"
            )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create user account"
        )
    
    # Step 7: Generate JWT token with 7-day expiration (Requirement 1.7)
    token_data = {
        "userId": str(new_user.id),
        "vehicleNumber": new_user.vehicleNumber
    }
    access_token = create_access_token(data=token_data)
    
    # Step 8: Create audit log entry (Requirement 1.9, 21.1)
    try:
        audit_log = AuditLog(
            userId=new_user.id,
            action=ActionType.USER_REGISTER,
            resourceType="User",
            resourceId=str(new_user.id),
            ipAddress=request.client.host if request.client else None,
            userAgent=request.headers.get("user-agent"),
            metadata={
                "vehicleNumber": new_user.vehicleNumber,
                "success": True
            }
        )
        await audit_log.insert()
    except Exception as e:
        # Log the error but don't fail the registration
        print(f"Failed to create audit log: {e}")
    
    # Step 9: Return response (Requirement 1.8)
    return RegisterResponse(
        success=True,
        token=access_token,
        userId=new_user.id,
        message="Registration successful"
    )


@router.post("/login", response_model=LoginResponse, status_code=status.HTTP_200_OK)
async def login(
    request: Request,
    login_data: LoginRequest,
):
    """
    Authenticate a user with vehicle number and password.
    
    **Validates Requirements**:
    - 2.1: Validate credentials against stored records
    - 2.2: Verify password hash using bcrypt comparison
    - 2.3: Reject login if account is banned (403 Forbidden)
    - 2.4: Reject login if account is inactive
    - 2.5: Generate new JWT token with 7-day expiration on success
    - 2.6: Update FCM token if provided
    - 2.7: Update lastLoginAt timestamp
    - 2.8: Return error message without revealing whether user exists
    - 2.9: Create audit log entry for login
    - 21.2: Audit log with action type USER_LOGIN
    
    Args:
        request: FastAPI request object (for audit logging)
        login_data: Login request data (vehicle number, password, optional FCM token)
        db: Database session
        
    Returns:
        LoginResponse with success status, JWT token, user ID, vehicle number, and message
        
    Raises:
        HTTPException 401: Invalid credentials
        HTTPException 403: Account banned
        HTTPException 500: Server error
    """
    # Step 1: Normalize vehicle number
    normalized_vehicle = normalize_vehicle_number(login_data.vehicleNumber)
    
    # Step 2: Query user by vehicle number (Requirement 2.1)
    user = await User.find_one(User.vehicleNumber == normalized_vehicle)
    
    # Step 3: Check if user exists and verify password (Requirement 2.2)
    # Return generic error message to avoid revealing whether user exists (Requirement 2.8)
    if not user or not verify_password(login_data.password, user.passwordHash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials"
        )
    
    # Step 4: Check if account is banned (Requirement 2.3)
    if user.isBanned:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account has been banned"
        )
    
    # Step 5: Check if account is inactive (Requirement 2.4)
    if not user.isActive:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Account is inactive"
        )
    
    # Step 6: Update FCM token if provided (Requirement 2.6)
    if login_data.fcmToken:
        user.fcmToken = login_data.fcmToken
    
    # Step 7: Update lastLoginAt timestamp (Requirement 2.7)
    user.lastLoginAt = now_ist()
    
    try:
        await user.save()
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update user login information"
        )
    
    # Step 8: Generate new JWT token with 7-day expiration (Requirement 2.5)
    token_data = {
        "userId": str(user.id),
        "vehicleNumber": user.vehicleNumber
    }
    access_token = create_access_token(data=token_data)
    
    # Step 9: Create audit log entry (Requirement 2.9, 21.2)
    try:
        audit_log = AuditLog(
            userId=user.id,
            action=ActionType.USER_LOGIN,
            resourceType="User",
            resourceId=str(user.id),
            ipAddress=request.client.host if request.client else None,
            userAgent=request.headers.get("user-agent"),
            metadata={
                "vehicleNumber": user.vehicleNumber,
                "fcmTokenUpdated": login_data.fcmToken is not None,
                "success": True
            }
        )
        await audit_log.insert()
    except Exception as e:
        # Log the error but don't fail the login
        print(f"Failed to create audit log: {e}")
    
    # Step 10: Return response
    return LoginResponse(
        success=True,
        token=access_token,
        userId=user.id,
        vehicleNumber=user.vehicleNumber,
        message="Login successful"
    )
