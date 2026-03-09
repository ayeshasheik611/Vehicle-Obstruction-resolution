"""
Authentication utilities for password hashing and JWT token management.

This module provides core authentication functions:
- Password hashing with bcrypt (10 salt rounds)
- JWT token generation with 7-day expiration
- JWT token validation and decoding

**Validates Requirements**: 1.5, 1.7, 18.1, 18.2, 18.6, 19.1, 19.2, 19.4, 19.5
"""
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
from passlib.context import CryptContext
from jose import JWTError, jwt
from app.core.config import settings
from app.utils.datetime import now_ist


# Password hashing context with bcrypt
# Using 10 salt rounds as per requirement 19.1
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto", bcrypt__rounds=10)


def hash_password(password: str) -> str:
    """
    Hash a password using bcrypt with 10 salt rounds.
    
    **Validates Requirements**: 1.5, 19.1, 19.2
    
    Args:
        password: Plain text password to hash
        
    Returns:
        Hashed password string
        
    Example:
        >>> hashed = hash_password("mypassword123")
        >>> len(hashed) > 0
        True
    """
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    Verify a plain password against a hashed password using bcrypt.
    
    **Validates Requirements**: 19.4
    
    Args:
        plain_password: Plain text password to verify
        hashed_password: Hashed password to compare against
        
    Returns:
        True if password matches, False otherwise
        
    Example:
        >>> hashed = hash_password("mypassword123")
        >>> verify_password("mypassword123", hashed)
        True
        >>> verify_password("wrongpassword", hashed)
        False
    """
    return pwd_context.verify(plain_password, hashed_password)


def create_access_token(data: Dict[str, Any], expires_delta: Optional[timedelta] = None) -> str:
    """
    Generate a JWT token with 7-day expiration.
    
    **Validates Requirements**: 1.7, 18.1, 18.6
    
    Args:
        data: Dictionary containing user data to encode in token (should include userId and vehicleNumber)
        expires_delta: Optional custom expiration time delta. Defaults to 7 days.
        
    Returns:
        Encoded JWT token string
        
    Example:
        >>> token = create_access_token({"userId": "123", "vehicleNumber": "ABC1234"})
        >>> len(token) > 0
        True
    """
    to_encode = data.copy()
    
    # Set expiration to 7 days as per requirement 18.1
    if expires_delta:
        expire = now_ist() + expires_delta
    else:
        expire = now_ist() + timedelta(days=settings.ACCESS_TOKEN_EXPIRE_DAYS)
    
    to_encode.update({"exp": expire})
    
    # Encode JWT token with secret key and algorithm
    encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
    return encoded_jwt


def decode_access_token(token: str) -> Optional[Dict[str, Any]]:
    """
    Validate and decode a JWT token.
    
    **Validates Requirements**: 18.2, 18.5
    
    Args:
        token: JWT token string to decode
        
    Returns:
        Dictionary containing decoded token payload if valid, None if invalid or expired
        
    Example:
        >>> token = create_access_token({"userId": "123", "vehicleNumber": "ABC1234"})
        >>> payload = decode_access_token(token)
        >>> payload is not None
        True
        >>> payload.get("userId")
        '123'
    """
    try:
        # Decode and verify JWT token signature and expiration
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        return payload
    except JWTError:
        # Token is invalid, expired, or signature verification failed
        return None


def extract_user_id_from_token(token: str) -> Optional[str]:
    """
    Extract user ID from a JWT token.
    
    **Validates Requirements**: 18.5
    
    Args:
        token: JWT token string
        
    Returns:
        User ID string if token is valid, None otherwise
        
    Example:
        >>> token = create_access_token({"userId": "123", "vehicleNumber": "ABC1234"})
        >>> user_id = extract_user_id_from_token(token)
        >>> user_id
        '123'
    """
    payload = decode_access_token(token)
    if payload:
        return payload.get("userId")
    return None
