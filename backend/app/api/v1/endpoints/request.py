"""
Request endpoints for call request management
Validates: Requirements 8.1-8.13, 11.1-11.10, 13.1-13.7, 21.4-21.5
"""
from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.orm import Session
from datetime import datetime, timedelta
from uuid import UUID
from typing import Optional

from app.core.database import get_db
from app.core.config import settings
from app.api.dependencies import get_current_user
from app.models.user import User
from app.models.request import Request as RequestModel, RequestStatus, ResponseType
from app.models.audit_log import ActionType
from app.schemas.request import (
    CreateRequestRequest,
    CreateRequestResponse,
    RespondRequestRequest,
    RespondRequestResponse,
    RequestHistoryResponse,
    RequestSummary
)
from app.services.rate_limit_service import get_rate_limit_service
from app.services.notification_service import notification_service
from app.services.audit_service import audit_service
from app.services.report_service import report_service
from app.utils.vehicle_validation import mask_vehicle_number
from app.utils.datetime import now_ist


router = APIRouter()


@router.post("/create", response_model=CreateRequestResponse, status_code=status.HTTP_201_CREATED)
async def create_request(
    request: Request,
    request_data: CreateRequestRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Create a new call request
    
    Validates Requirements: 8.1-8.13, 21.4
    """
    # Check rate limit
    rate_limit_service = get_rate_limit_service()
    rate_status = rate_limit_service.check_rate_limit(current_user.id)
    
    if not rate_status.allowed:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail={
                "message": "Rate limit exceeded",
                "remaining": rate_status.remaining_requests,
                "reset_time": rate_status.reset_time.isoformat()
            }
        )
    
    # Find target vehicle owner
    target_user = db.query(User).filter(User.vehicleNumber == request_data.targetVehicle).first()
    
    if not target_user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Vehicle not registered in system"
        )
    
    # Check if requester is not the owner
    if current_user.id == target_user.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot send request to your own vehicle"
        )
    
    # Check if target user is banned
    if target_user.isBanned:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Unable to send request to this user"
        )
    
    # Create request record
    current_time = now_ist()
    expiry_time = current_time + timedelta(minutes=settings.REQUEST_EXPIRY_MINUTES)
    
    new_request = RequestModel(
        requesterId=current_user.id,
        targetUserId=target_user.id,
        targetVehicle=request_data.targetVehicle,
        status=RequestStatus.PENDING,
        expiresAt=expiry_time
    )
    
    db.add(new_request)
    db.commit()
    db.refresh(new_request)
    
    # Increment user's request count
    current_user.requestCount += 1
    db.commit()
    
    # Send push notification
    notification_result = notification_service.send_call_request_notification(
        db=db,
        target_user_id=target_user.id,
        request_id=new_request.id,
        vehicle_number=request_data.targetVehicle,
        requester_id=current_user.id
    )
    
    # Increment rate limit counter
    rate_limit_service.increment_request_count(current_user.id)
    
    # Check for abuse patterns and apply restrictions if detected
    # Validates Requirements: 15.1, 15.2, 15.3, 15.4, 15.5, 15.6, 15.7
    report_service.check_and_apply_abuse_detection(db, current_user.id)
    
    # Create audit log
    audit_service.log_action(
        db=db,
        user_id=current_user.id,
        action=ActionType.REQUEST_CREATE,
        resource_type="Request",
        resource_id=new_request.id,
        metadata={
            "targetVehicle": request_data.targetVehicle,
            "targetUserId": str(target_user.id),
            "notificationSent": notification_result.success
        }
    )
    
    return CreateRequestResponse(
        success=True,
        requestId=new_request.id,
        status=new_request.status,
        expiresAt=new_request.expiresAt,
        message="Request sent successfully"
    )


@router.post("/respond", response_model=RespondRequestResponse, status_code=status.HTTP_200_OK)
async def respond_to_request(
    request: Request,
    response_data: RespondRequestRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Respond to a call request
    
    Validates Requirements: 11.1-11.10, 21.5
    """
    # Find request
    req = db.query(RequestModel).filter(RequestModel.id == response_data.requestId).first()
    
    if not req:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Request not found"
        )
    
    # Verify responding user is target user
    if req.targetUserId != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You are not authorized to respond to this request"
        )
    
    # Check request status
    if req.status != RequestStatus.PENDING:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Request is already {req.status.value}"
        )
    
    # Check if expired
    if now_ist() > req.expiresAt:
        req.status = RequestStatus.EXPIRED
        db.commit()
        raise HTTPException(
            status_code=status.HTTP_410_GONE,
            detail="Request has expired"
        )
    
    # Update request
    req.status = RequestStatus.RESPONDED
    req.respondedAt = now_ist()
    req.response = ResponseType[response_data.response]
    req.responseMessage = response_data.message
    
    db.commit()
    db.refresh(req)
    
    # Send notification to requester
    notification_service.send_response_notification(
        db=db,
        requester_id=req.requesterId,
        request_id=req.id,
        response_type=response_data.response,
        vehicle_number=req.targetVehicle
    )
    
    # Create audit log
    audit_service.log_action(
        db=db,
        user_id=current_user.id,
        action=ActionType.REQUEST_RESPOND,
        resource_type="Request",
        resource_id=req.id,
        metadata={
            "response": response_data.response,
            "requesterId": str(req.requesterId)
        }
    )
    
    return RespondRequestResponse(
        success=True,
        requestId=req.id,
        status=req.status,
        message="Response recorded successfully"
    )


@router.get("/history", response_model=RequestHistoryResponse, status_code=status.HTTP_200_OK)
async def get_request_history(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    status: Optional[str] = None,
    limit: int = 20,
    offset: int = 0
):
    """
    Get request history for current user
    
    Validates Requirements: 13.1-13.7
    """
    print(f"Request history called with status: {status}")
    
    # Build query
    query = db.query(RequestModel).filter(
        (RequestModel.requesterId == current_user.id) | 
        (RequestModel.targetUserId == current_user.id)
    )
    
    # Apply status filter
    if status:
        try:
            status_enum = RequestStatus[status.upper()]
            query = query.filter(RequestModel.status == status_enum)
            print(f"Filtering by status: {status_enum}")
        except KeyError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid status: {status}"
            )
    
    # Get total count
    total = query.count()
    
    # Apply pagination and ordering
    requests = query.order_by(RequestModel.createdAt.desc()).offset(offset).limit(limit).all()
    
    # Build response
    summaries = []
    for req in requests:
        req_type = "Sent" if req.requesterId == current_user.id else "Received"
        masked_vehicle = mask_vehicle_number(req.targetVehicle)
        
        print(f"Request {req.id}: status={req.status}, type={req_type}")
        
        summaries.append(RequestSummary(
            id=req.id,
            type=req_type,
            vehicleNumber=masked_vehicle,
            status=req.status,
            createdAt=req.createdAt,
            expiresAt=req.expiresAt,
            respondedAt=req.respondedAt,
            response=req.response.value if req.response else None,
            responseMessage=req.responseMessage
        ))
    
    return RequestHistoryResponse(
        success=True,
        requests=summaries,
        total=total,
        hasMore=(offset + limit) < total
    )
