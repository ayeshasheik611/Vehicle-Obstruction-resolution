"""
Vehicle model
Validates: Requirements 22.4, 22.5
"""
from sqlalchemy import Column, String, Boolean, DateTime, ForeignKey, Index
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from datetime import datetime
import uuid

from app.core.database import Base


class Vehicle(Base):
    """
    Vehicle model representing registered vehicles
    
    Validates:
    - Requirement 22.4: Every vehicle has a valid user ID referencing an existing user
    - Requirement 22.5: Vehicle numbers are unique across all vehicles
    """
    __tablename__ = "vehicles"
    
    # Primary key
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    
    # Foreign key to user
    userId = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    
    # Vehicle identification
    vehicleNumber = Column(String(20), unique=True, nullable=False, index=True)
    
    # Status
    isActive = Column(Boolean, default=True, nullable=False)
    
    # Timestamps
    registeredAt = Column(DateTime, default=datetime.utcnow, nullable=False)
    lastIdentifiedAt = Column(DateTime, nullable=True)
    
    # Relationships
    owner = relationship("User", back_populates="vehicles")
    
    def __repr__(self):
        return f"<Vehicle(id={self.id}, vehicleNumber={self.vehicleNumber}, userId={self.userId})>"
