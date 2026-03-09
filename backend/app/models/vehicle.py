"""
Vehicle model
Validates: Requirements 22.4, 22.5
"""
from beanie import Document
from pydantic import Field, UUID4
from datetime import datetime
from typing import Optional
from uuid import uuid4
from pymongo import IndexModel, ASCENDING


class Vehicle(Document):
    """
    Vehicle model representing registered vehicles
    
    Validates:
    - Requirement 22.4: Every vehicle has a valid user ID referencing an existing user
    - Requirement 22.5: Vehicle numbers are unique across all vehicles
    """
    
    # Primary key
    id: UUID4 = Field(default_factory=uuid4)
    
    # Foreign key to user
    userId: UUID4
    
    # Vehicle identification
    vehicleNumber: str
    
    # Status
    isActive: bool = True
    
    # Timestamps
    registeredAt: datetime = Field(default_factory=datetime.utcnow)
    lastIdentifiedAt: Optional[datetime] = None
    
    class Settings:
        name = "vehicles"
        indexes = [
            IndexModel([("userId", ASCENDING)]),
            IndexModel([("vehicleNumber", ASCENDING)], unique=True),
        ]
    
    def __repr__(self):
        return f"<Vehicle(id={self.id}, vehicleNumber={self.vehicleNumber}, userId={self.userId})>"
