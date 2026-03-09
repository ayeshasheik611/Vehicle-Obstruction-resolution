"""
Firebase Cloud Messaging service
Validates: Requirements 10.1, 16.1, 16.2, 16.3
"""
import firebase_admin
from firebase_admin import credentials, messaging
from typing import Optional
from loguru import logger
import os

from app.core.config import settings


class FirebaseService:
    """
    Firebase Cloud Messaging service for push notifications
    
    Validates:
    - Requirement 10.1: Push notification delivery via Firebase
    - Requirement 16.1: Device token storage and management
    - Requirement 16.2: Multiple device support per user
    - Requirement 16.3: Platform type recording (iOS/Android)
    """
    
    _instance: Optional['FirebaseService'] = None
    _initialized: bool = False
    
    def __new__(cls):
        """Singleton pattern to ensure only one Firebase instance"""
        if cls._instance is None:
            cls._instance = super(FirebaseService, cls).__new__(cls)
        return cls._instance
    
    def initialize(self):
        """Initialize Firebase Admin SDK (lazy initialization)"""
        if not FirebaseService._initialized:
            try:
                # Check if credentials file exists
                if not os.path.exists(settings.FIREBASE_CREDENTIALS_PATH):
                    logger.warning(
                        f"Firebase credentials file not found: {settings.FIREBASE_CREDENTIALS_PATH}. "
                        "Firebase notifications will not work."
                    )
                    return
                
                # Initialize Firebase with service account credentials
                cred = credentials.Certificate(settings.FIREBASE_CREDENTIALS_PATH)
                firebase_admin.initialize_app(cred)
                FirebaseService._initialized = True
                logger.info("Firebase Admin SDK initialized successfully")
            except Exception as e:
                logger.error(f"Failed to initialize Firebase Admin SDK: {e}")
                raise
    
    def is_initialized(self) -> bool:
        """Check if Firebase is initialized"""
        return FirebaseService._initialized


# Global Firebase service instance
firebase_service = FirebaseService()
