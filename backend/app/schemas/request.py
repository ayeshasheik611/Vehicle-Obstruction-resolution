"""
Request API schemas
"""
from pydantic import BaseModel, Field
from datetime import datetime
from uuid import UUID
from typing import List, Optional
from app.models.request import RequestStatus


class CreateRequestRequest(BaseModel):
    """Request schema for creating a call request"""
    targetVehicle: str = Field(..., min_length=1, max_length=20)
    message: Optional[str] = Field(None, max_length=500)


class CreateRequestResponse(BaseModel):
    """Response schema for request creation"""
    success: bool
    requestId: UUID
    status: RequestStatus
    expiresAt: datetime
    message: str
    
    class Config:
        from_attributes = True


class RespondRequestRequest(BaseModel):
    """Request schema for responding to a call request"""
    requestId: UUID
    response: str = Field(..., pattern="^(MESSAGE|ON_MY_WAY|CANNOT_MOVE)$")
    message: Optional[str] = Field(None, max_length=500)


class RespondRequestResponse(BaseModel):
    """Response schema for request response"""
    success: bool
    requestId: UUID
    status: RequestStatus
    message: str
    
    class Config:
        from_attributes = True


class RequestSummary(BaseModel):
    """Summary of a request for history"""
    id: UUID
    type: str  # "Sent" or "Received"
    vehicleNumber: str  # Masked
    status: RequestStatus
    createdAt: datetime
    expiresAt: datetime
    respondedAt: Optional[datetime]
    response: Optional[str] = None
    responseMessage: Optional[str] = None
    
    class Config:
        from_attributes = True


class RequestHistoryResponse(BaseModel):
    """Response schema for request history"""
    success: bool
    requests: List[RequestSummary]
    total: int
    hasMore: bool
