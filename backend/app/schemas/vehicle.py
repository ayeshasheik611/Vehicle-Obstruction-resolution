"""
Vehicle schemas for request/response validation
"""
from pydantic import BaseModel, Field
from typing import Optional


class VehicleIdentifyRequest(BaseModel):
    """Request schema for vehicle identification"""
    image: Optional[str] = Field(None, description="Base64 encoded image data")
    vehicleNumber: Optional[str] = Field(None, description="Manual vehicle number entry")
    
    class Config:
        json_schema_extra = {
            "example": {
                "image": "base64_encoded_image_string",
                "vehicleNumber": "MH12AB1234"
            }
        }


class VehicleIdentifyResponse(BaseModel):
    """Response schema for vehicle identification"""
    success: bool = Field(..., description="Whether identification was successful")
    vehicleNumber: str = Field(..., description="Masked vehicle number for display")
    fullVehicleNumber: str = Field(..., description="Full vehicle number for creating requests")
    found: bool = Field(..., description="Whether vehicle is registered")
    canSendRequest: bool = Field(..., description="Whether user can send request to this vehicle")
    confidence: Optional[float] = Field(None, description="ALPR confidence score (0-1)")
    message: str = Field(..., description="Result message")
    
    class Config:
        json_schema_extra = {
            "example": {
                "success": True,
                "vehicleNumber": "MH****1234",
                "fullVehicleNumber": "MH12AB1234",
                "found": True,
                "canSendRequest": True,
                "confidence": 0.95,
                "message": "Vehicle identified successfully"
            }
        }
