"""
Vehicle model
Validates: Requirements 22.4, 22.5
"""
from beanie import Document, Indexed, Link
from pydantic import Field
from datetime import datetime
from typing import Optional
from uuid import UUID, uuid4


class Vehicle(Document):
    """
    Vehicle model representing registered vehicles
    
    Validates:
    - Requirement 22.4: Every vehicle has a valid user ID referencing an existing user
    - Requirement 22.5: Vehicle numbers are unique across all vehicles
    """
    
    # Primary key
    id: UUID = Field(default_factory=uuid4)
    
    # Foreign key to user
    userId: Indexed(UUID)
    
    # Vehicle identification
    vehicleNumber: Indexed(str, unique=True)
    
    # Status
    isActive: bool = True
    
    # Timestamps
    registeredAt: datetime = Field(default_factory=datetime.utcnow)
    lastIdentifiedAt: Optional[datetime] = None
    
    class Settings:
        name = "vehicles"
        indexes = [
            "id",
            "userId",
            "vehicleNumber",
        ]
    
    def __repr__(self):
        return f"<Vehicle(id={self.id}, vehicleNumber={self.vehicleNumber}, userId={self.userId})>"
