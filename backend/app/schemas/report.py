"""
Report schemas for request/response validation
"""
from pydantic import BaseModel, Field
from typing import Optional


class CreateReportRequest(BaseModel):
    """Request schema for creating a report"""
    targetUserId: str = Field(..., description="ID of user being reported")
    reason: str = Field(..., description="Reason for report (SPAM, HARASSMENT, FALSE_REQUEST, ABUSE, OTHER)")
    description: Optional[str] = Field(None, max_length=500, description="Optional description")
    
    class Config:
        json_schema_extra = {
            "example": {
                "targetUserId": "123e4567-e89b-12d3-a456-426614174000",
                "reason": "SPAM",
                "description": "User is sending too many requests"
            }
        }


class CreateReportResponse(BaseModel):
    """Response schema for report creation"""
    success: bool = Field(..., description="Whether report was created successfully")
    reportId: str = Field(..., description="ID of created report")
    message: str = Field(..., description="Success message")
    
    class Config:
        json_schema_extra = {
            "example": {
                "success": True,
                "reportId": "123e4567-e89b-12d3-a456-426614174000",
                "message": "Report submitted successfully. We will review it shortly."
            }
        }
