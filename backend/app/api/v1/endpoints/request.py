"""
Request endpoints for call request management
Validates: Requirements 8.1-8.13, 11.1-11.10, 13.1-13.7, 21.4-21.5
"""
from fastapi import APIRouter, Depends, HTTPException, status, Request
from datetime import datetime, timedelta
from uuid import UUID
from typing import Optional
from beanie.operators import Or

from app.core.config import settings
from app.api.dependencies import get_current_user
from app.models.user import User
from app.models.request import Request as RequestModel, RequestStatus, ResponseType
from app.models.audit_log import ActionType, AuditLog
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
from app.services.report_service import report_service
from app.utils.vehicle_validation import mask_vehicle_number
from app.utils.datetime import now_ist


router = APIRouter()


@router.post("/create", response_model=CreateRequestResponse, status_code=status.HTTP_201_CREATED)
async def create_request(
    request: Request,
    request_data: CreateRequestRequest,
    current_user: User = Depends(get_current_user),
):
    """Create a new call request - Validates Requirements: 8.1-8.13, 21.4"""
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
    
    target_user = await User.find_one(User.vehicleNumber == request_data.targetVehicle)
    
    if not target_user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Vehicle not registered in system"
        )
    
    if current_user.id == target_user.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot send request to your own vehicle"
        )
    
    if target_user.isBanned:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Unable to send request to this user"
        )
    
    current_time = now_ist()
    expiry_time = current_time + timedelta(minutes=settings.REQUEST_EXPIRY_MINUTES)
    
    new_request = RequestModel(
        requesterId=current_user.id,
        targetUserId=target_user.id,
        targetVehicle=request_data.targetVehicle,
        status=RequestStatus.PENDING,
        createdAt=current_time,
        expiresAt=expiry_time
    )
    
    await new_request.insert()
    
    current_user.requestCount += 1
    await current_user.save()
    
    notification_result = await notification_service.send_call_request_notification(
        target_user_id=target_user.id,
        request_id=new_request.id,
        vehicle_number=request_data.targetVehicle,
        requester_id=current_user.id
    )
    
    rate_limit_service.increment_request_count(current_user.id)
    
    await report_service.check_and_apply_abuse_detection(current_user.id)
    
    audit_log = AuditLog(
        userId=current_user.id,
        action=ActionType.REQUEST_CREATE,
        resourceType="Request",
        resourceId=str(new_request.id),
        metadata={
            "targetVehicle": request_data.targetVehicle,
            "targetUserId": str(target_user.id),
            "notificationSent": notification_result.success
        }
    )
    await audit_log.insert()
    
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
):
    """Respond to a call request - Validates Requirements: 11.1-11.10, 21.5"""
    req = await RequestModel.find_one(RequestModel.id == response_data.requestId)
    
    if not req:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Request not found"
        )
    
    if req.targetUserId != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You are not authorized to respond to this request"
        )
    
    if req.status != RequestStatus.PENDING:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Request is already {req.status.value}"
        )
    
    if now_ist() > req.expiresAt:
        req.status = RequestStatus.EXPIRED
        await req.save()
        raise HTTPException(
            status_code=status.HTTP_410_GONE,
            detail="Request has expired"
        )
    
    req.status = RequestStatus.RESPONDED
    req.respondedAt = now_ist()
    req.response = ResponseType[response_data.response]
    req.responseMessage = response_data.message
    
    await req.save()
    
    await notification_service.send_response_notification(
        requester_id=req.requesterId,
        request_id=req.id,
        response_type=response_data.response,
        vehicle_number=req.targetVehicle
    )
    
    audit_log = AuditLog(
        userId=current_user.id,
        action=ActionType.REQUEST_RESPOND,
        resourceType="Request",
        resourceId=str(req.id),
        metadata={
            "response": response_data.response,
            "requesterId": str(req.requesterId)
        }
    )
    await audit_log.insert()
    
    return RespondRequestResponse(
        success=True,
        requestId=req.id,
        status=req.status,
        message="Response recorded successfully"
    )


@router.get("/history", response_model=RequestHistoryResponse, status_code=status.HTTP_200_OK)
async def get_request_history(
    current_user: User = Depends(get_current_user),
    status: Optional[str] = None,
    limit: int = 20,
    offset: int = 0
):
    """Get request history for current user - Validates Requirements: 13.1-13.7"""
    print(f"Request history called with status: {status}")
    
    query_filter = Or(
        RequestModel.requesterId == current_user.id,
        RequestModel.targetUserId == current_user.id
    )
    
    if status:
        try:
            from beanie.operators import And
            status_enum = RequestStatus[status.upper()]
            query_filter = And(query_filter, RequestModel.status == status_enum)
            print(f"Filtering by status: {status_enum}")
        except KeyError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid status: {status}"
            )
    
    total = await RequestModel.find(query_filter).count()
    requests = await RequestModel.find(query_filter).sort(-RequestModel.createdAt).skip(offset).limit(limit).to_list()
    
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
