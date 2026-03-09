"""
Device Token Management Service
Validates: Requirements 16.1, 16.2, 16.3, 16.4, 16.5, 16.6
"""
from datetime import datetime, timedelta
from typing import List, Optional
from uuid import UUID
from loguru import logger
from beanie.operators import And, LT

from app.models.device_token import DeviceToken, Platform
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
    async def register_device_token(
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
        """
        try:
            # Try to find existing token
            existing_token = await DeviceToken.find_one(DeviceToken.fcmToken == fcm_token)
            
            if existing_token:
                existing_token.userId = user_id
                existing_token.platform = platform
                existing_token.isActive = True
                existing_token.lastUsedAt = now_ist()
                await existing_token.save()
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
            
            await device_token.insert()
            logger.info(f"Registered new device token for user {user_id}")
            return device_token
            
        except Exception as e:
            # Handle duplicate key error - token was inserted by another request
            if "duplicate key error" in str(e) or "E11000" in str(e):
                logger.info(f"Token already exists, fetching and updating for user {user_id}")
                existing_token = await DeviceToken.find_one(DeviceToken.fcmToken == fcm_token)
                if existing_token:
                    existing_token.userId = user_id
                    existing_token.platform = platform
                    existing_token.isActive = True
                    existing_token.lastUsedAt = now_ist()
                    await existing_token.save()
                    return existing_token
            # Re-raise if it's a different error
            raise
    
    @staticmethod
    async def get_active_tokens(user_id: UUID) -> List[DeviceToken]:
        """
        Retrieve all active device tokens for a user
        
        Validates:
        - Requirement 16.2: Support multiple device tokens per user
        """
        tokens = await DeviceToken.find(
            And(
                DeviceToken.userId == user_id,
                DeviceToken.isActive == True
            )
        ).to_list()
        
        logger.debug(f"Found {len(tokens)} active tokens for user {user_id}")
        return tokens
    
    @staticmethod
    async def mark_token_inactive(fcm_token: str) -> bool:
        """
        Mark a device token as inactive
        
        Validates:
        - Requirement 16.5: Mark tokens inactive on permanent errors
        """
        token = await DeviceToken.find_one(DeviceToken.fcmToken == fcm_token)
        
        if token:
            token.isActive = False
            await token.save()
            logger.info(f"Marked token as inactive: {fcm_token[:20]}...")
            return True
        
        logger.warning(f"Token not found for marking inactive: {fcm_token[:20]}...")
        return False
    
    @staticmethod
    async def update_last_used(fcm_token: str) -> bool:
        """
        Update the lastUsedAt timestamp for a device token
        
        Validates:
        - Requirement 16.4: Update lastUsedAt on successful delivery
        """
        token = await DeviceToken.find_one(DeviceToken.fcmToken == fcm_token)
        
        if token:
            token.lastUsedAt = now_ist()
            await token.save()
            logger.debug(f"Updated lastUsedAt for token: {fcm_token[:20]}...")
            return True
        
        return False
    
    @staticmethod
    async def cleanup_old_tokens() -> int:
        """
        Remove inactive tokens that haven't been used for 90 days
        
        Validates:
        - Requirement 16.6: Remove inactive tokens after 90 days
        """
        cutoff_date = now_ist() - timedelta(days=90)
        
        old_tokens = await DeviceToken.find(
            And(
                DeviceToken.isActive == False,
                LT(DeviceToken.lastUsedAt, cutoff_date)
            )
        ).to_list()
        
        count = len(old_tokens)
        
        for token in old_tokens:
            await token.delete()
        
        logger.info(f"Cleaned up {count} old inactive tokens")
        return count


# Service instance
device_token_service = DeviceTokenService()
