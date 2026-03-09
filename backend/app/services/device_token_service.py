"""
Device Token Management Service
Validates: Requirements 16.1, 16.2, 16.3, 16.4, 16.5, 16.6
"""
from sqlalchemy.orm import Session
from sqlalchemy import and_
from datetime import datetime, timedelta
from typing import List, Optional
from uuid import UUID
from loguru import logger

from app.models.device_token import DeviceToken, Platform
from app.core.database import get_db
from app.utils.datetime import now_ist


class DeviceTokenService:
    """
    Service for managing FCM device tokens
    
    Validates:
    - Requirement 16.1: Store FCM tokens in device_tokens table
    - Requirement 16.2: Allow multiple device tokens per user
    - Requirement 16.3: Record platform type (iOS/Android)
    - Requirement 16.4: Update lastUsedAt on successful delivery
    - Requirement 16.5: Mark tokens inactive on permanent errors
    - Requirement 16.6: Remove inactive tokens after 90 days
    """
    
    @staticmethod
    def register_device_token(
        db: Session,
        user_id: UUID,
        fcm_token: str,
        platform: Platform
    ) -> DeviceToken:
        """
        Register or update a device token for a user
        
        Validates:
        - Requirement 16.1: Store token in device_tokens table
        - Requirement 16.2: Support multiple devices per user
        - Requirement 16.3: Record platform type
        
        Args:
            db: Database session
            user_id: User UUID
            fcm_token: Firebase Cloud Messaging token
            platform: Device platform (iOS/Android)
            
        Returns:
            DeviceToken: Created or updated device token record
        """
        # Check if token already exists
        existing_token = db.query(DeviceToken).filter(
            DeviceToken.fcmToken == fcm_token
        ).first()
        
        if existing_token:
            # Update existing token
            existing_token.userId = user_id
            existing_token.platform = platform
            existing_token.isActive = True
            existing_token.lastUsedAt = now_ist()
            db.commit()
            db.refresh(existing_token)
            logger.info(f"Updated device token for user {user_id}")
            return existing_token
        
        # Create new token
        device_token = DeviceToken(
            userId=user_id,
            fcmToken=fcm_token,
            platform=platform,
            isActive=True,
            createdAt=now_ist()
        )
        
        db.add(device_token)
        db.commit()
        db.refresh(device_token)
        logger.info(f"Registered new device token for user {user_id}")
        return device_token
    
    @staticmethod
    def get_active_tokens(db: Session, user_id: UUID) -> List[DeviceToken]:
        """
        Retrieve all active device tokens for a user
        
        Validates:
        - Requirement 16.2: Support multiple device tokens per user
        
        Args:
            db: Database session
            user_id: User UUID
            
        Returns:
            List[DeviceToken]: List of active device tokens
        """
        tokens = db.query(DeviceToken).filter(
            and_(
                DeviceToken.userId == user_id,
                DeviceToken.isActive == True
            )
        ).all()
        
        logger.debug(f"Found {len(tokens)} active tokens for user {user_id}")
        return tokens
    
    @staticmethod
    def mark_token_inactive(db: Session, fcm_token: str) -> bool:
        """
        Mark a device token as inactive
        
        Validates:
        - Requirement 16.5: Mark tokens inactive on permanent errors
        
        Args:
            db: Database session
            fcm_token: Firebase Cloud Messaging token
            
        Returns:
            bool: True if token was marked inactive, False if not found
        """
        token = db.query(DeviceToken).filter(
            DeviceToken.fcmToken == fcm_token
        ).first()
        
        if token:
            token.isActive = False
            db.commit()
            logger.info(f"Marked token as inactive: {fcm_token[:20]}...")
            return True
        
        logger.warning(f"Token not found for marking inactive: {fcm_token[:20]}...")
        return False
    
    @staticmethod
    def update_last_used(db: Session, fcm_token: str) -> bool:
        """
        Update the lastUsedAt timestamp for a device token
        
        Validates:
        - Requirement 16.4: Update lastUsedAt on successful delivery
        
        Args:
            db: Database session
            fcm_token: Firebase Cloud Messaging token
            
        Returns:
            bool: True if updated, False if not found
        """
        token = db.query(DeviceToken).filter(
            DeviceToken.fcmToken == fcm_token
        ).first()
        
        if token:
            token.lastUsedAt = now_ist()
            db.commit()
            logger.debug(f"Updated lastUsedAt for token: {fcm_token[:20]}...")
            return True
        
        return False
    
    @staticmethod
    def cleanup_old_tokens(db: Session) -> int:
        """
        Remove inactive tokens that haven't been used for 90 days
        
        Validates:
        - Requirement 16.6: Remove inactive tokens after 90 days
        
        Args:
            db: Database session
            
        Returns:
            int: Number of tokens removed
        """
        cutoff_date = now_ist() - timedelta(days=90)
        
        # Find inactive tokens older than 90 days
        old_tokens = db.query(DeviceToken).filter(
            and_(
                DeviceToken.isActive == False,
                DeviceToken.lastUsedAt < cutoff_date
            )
        ).all()
        
        count = len(old_tokens)
        
        for token in old_tokens:
            db.delete(token)
        
        db.commit()
        logger.info(f"Cleaned up {count} old inactive tokens")
        return count


# Service instance
device_token_service = DeviceTokenService()
