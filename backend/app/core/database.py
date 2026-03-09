"""
Database configuration and session management for MongoDB
"""
from motor.motor_asyncio import AsyncIOMotorClient
from beanie import init_beanie
from typing import Optional

from app.core.config import settings

# Global MongoDB client
mongodb_client: Optional[AsyncIOMotorClient] = None


async def connect_to_mongo():
    """Connect to MongoDB"""
    global mongodb_client
    mongodb_client = AsyncIOMotorClient(settings.DATABASE_URL)
    
    # Import all models for Beanie initialization
    from app.models.user import User
    from app.models.vehicle import Vehicle
    from app.models.request import Request
    from app.models.device_token import DeviceToken
    from app.models.report import Report
    from app.models.audit_log import AuditLog
    
    # Initialize Beanie with the database and models
    await init_beanie(
        database=mongodb_client[settings.DATABASE_NAME],
        document_models=[
            User,
            Vehicle,
            Request,
            DeviceToken,
            Report,
            AuditLog,
        ]
    )


async def close_mongo_connection():
    """Close MongoDB connection"""
    global mongodb_client
    if mongodb_client:
        mongodb_client.close()


def get_database():
    """Get MongoDB database instance"""
    if mongodb_client is None:
        raise Exception("Database not initialized. Call connect_to_mongo() first.")
    return mongodb_client[settings.DATABASE_NAME]
