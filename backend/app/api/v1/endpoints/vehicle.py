"""
Vehicle identification endpoints

Provides endpoints for identifying vehicles using ALPR or manual entry.

**Validates Requirements**: 4, 5, 6, 7, 21.3
"""
from fastapi import APIRouter, Depends, HTTPException, status

from app.api.dependencies import get_current_user
from app.models.user import User
from app.models.audit_log import ActionType, AuditLog
from app.schemas.vehicle import VehicleIdentifyRequest, VehicleIdentifyResponse
from app.services.alpr_service import alpr_service
from app.utils.vehicle_validation import validate_vehicle_format, normalize_vehicle_number, mask_vehicle_number


router = APIRouter()


@router.post("/identify", response_model=VehicleIdentifyResponse)
async def identify_vehicle(
    request: VehicleIdentifyRequest,
    current_user: User = Depends(get_current_user)
):
    """
    Identify vehicle owner by license plate image or manual entry
    
    **Validates Requirements**: 4, 5.1, 5.2, 5.3, 5.4, 6.1, 6.2, 6.3, 6.4, 6.5, 7.1, 7.2, 7.3, 7.4, 7.5, 21.3
    """
    vehicle_number = None
    confidence = None
    alpr_used = False
    
    if request.image:
        alpr_used = True
        alpr_result = alpr_service.extract_plate_number(request.image)
        
        if alpr_result["success"]:
            vehicle_number = alpr_result["vehicle_number"]
            confidence = alpr_result["confidence"]
        else:
            return VehicleIdentifyResponse(
                success=False,
                message=alpr_result["message"] + " Please use manual entry instead.",
                vehicleNumber="",
                fullVehicleNumber="",
                found=False,
                canSendRequest=False,
                confidence=None
            )
    
    elif request.vehicleNumber:
        vehicle_number = normalize_vehicle_number(request.vehicleNumber)
        
        if not validate_vehicle_format(vehicle_number):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid vehicle number format. Please check and try again."
            )
    
    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Either image or vehicleNumber must be provided"
        )
    
    owner = await User.find_one(
        User.vehicleNumber == vehicle_number,
        User.isActive == True,
        User.isBanned == False
    )
    
    masked_vehicle = mask_vehicle_number(vehicle_number)
    
    found = owner is not None
    can_send_request = found and owner.id != current_user.id
    
    audit_log = AuditLog(
        userId=current_user.id,
        action=ActionType.VEHICLE_IDENTIFIED,
        resourceType="Vehicle",
        resourceId=vehicle_number,
        metadata={
            "masked_vehicle": masked_vehicle,
            "found": found,
            "alpr_used": alpr_used,
            "confidence": confidence,
            "can_send_request": can_send_request
        }
    )
    await audit_log.insert()
    
    return VehicleIdentifyResponse(
        success=True,
        vehicleNumber=masked_vehicle,
        fullVehicleNumber=vehicle_number,
        found=found,
        canSendRequest=can_send_request,
        confidence=confidence,
        message="Vehicle identified successfully" if found else "Vehicle not registered in the system"
    )
