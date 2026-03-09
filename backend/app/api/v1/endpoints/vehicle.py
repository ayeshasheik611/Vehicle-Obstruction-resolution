"""
Vehicle identification endpoints

Provides endpoints for identifying vehicles using ALPR or manual entry.

**Validates Requirements**: 4, 5, 6, 7, 21.3
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import Optional
from uuid import UUID

from app.core.database import get_db
from app.api.dependencies import get_current_user
from app.models.user import User
from app.schemas.vehicle import VehicleIdentifyRequest, VehicleIdentifyResponse
from app.services.alpr_service import alpr_service
from app.services.audit_service import audit_service
from app.models.audit_log import ActionType
from app.utils.vehicle_validation import validate_vehicle_format, normalize_vehicle_number, mask_vehicle_number


router = APIRouter()


@router.post("/identify", response_model=VehicleIdentifyResponse)
async def identify_vehicle(
    request: VehicleIdentifyRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Identify vehicle owner by license plate image or manual entry
    
    This endpoint:
    1. Accepts image (base64) or manual vehicle number (Requirement 5.1)
    2. Processes image with ALPR if provided (Requirement 5.2)
    3. Validates vehicle number format (Requirement 5.3)
    4. Queries database for vehicle owner (Requirement 6.1)
    5. Masks vehicle number for privacy (Requirement 7.1)
    6. Returns identification result (Requirement 6.2)
    7. Creates audit log entry (Requirement 21.3)
    
    **Validates Requirements**: 4, 5.1, 5.2, 5.3, 5.4, 6.1, 6.2, 6.3, 6.4, 6.5, 7.1, 7.2, 7.3, 7.4, 7.5, 21.3
    
    Args:
        request: VehicleIdentifyRequest with image or vehicleNumber
        db: Database session
        current_user: Authenticated user
        
    Returns:
        VehicleIdentifyResponse with identification result
        
    Raises:
        HTTPException: If validation fails or processing error occurs
    """
    vehicle_number = None
    confidence = None
    alpr_used = False
    
    # Process image with ALPR if provided (Requirement 5.2)
    if request.image:
        alpr_used = True
        alpr_result = alpr_service.extract_plate_number(request.image)
        
        if alpr_result["success"]:
            vehicle_number = alpr_result["vehicle_number"]
            confidence = alpr_result["confidence"]
        else:
            # ALPR failed, return response suggesting manual entry
            # Requirement 5.4: Handle ALPR failures gracefully
            return VehicleIdentifyResponse(
                success=False,
                message=alpr_result["message"] + " Please use manual entry instead.",
                vehicleNumber="",  # Empty string instead of None
                fullVehicleNumber="",
                found=False,
                canSendRequest=False,
                confidence=None
            )
    
    # Use manual entry if provided (Requirement 5.1)
    elif request.vehicleNumber:
        vehicle_number = normalize_vehicle_number(request.vehicleNumber)
        
        # Validate format (Requirement 5.3)
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
    
    # Query database for vehicle owner (Requirement 6.1)
    from app.models.user import User as UserModel
    
    owner = db.query(UserModel).filter(
        UserModel.vehicleNumber == vehicle_number,
        UserModel.isActive == True,
        UserModel.isBanned == False
    ).first()
    
    # Mask vehicle number for privacy (Requirement 7.1, 7.2, 7.3, 7.4, 7.5)
    masked_vehicle = mask_vehicle_number(vehicle_number)
    
    # Determine if vehicle was found and can receive requests
    found = owner is not None
    can_send_request = found and owner.id != current_user.id
    
    # Create audit log entry (Requirement 21.3)
    audit_service.log_action(
        db=db,
        user_id=current_user.id,
        action=ActionType.VEHICLE_IDENTIFIED,
        resource_type="Vehicle",
        resource_id=vehicle_number,
        metadata={
            "masked_vehicle": masked_vehicle,
            "found": found,
            "alpr_used": alpr_used,
            "confidence": confidence,
            "can_send_request": can_send_request
        }
    )
    
    # Return identification result (Requirement 6.2, 6.3, 6.4, 6.5)
    return VehicleIdentifyResponse(
        success=True,
        vehicleNumber=masked_vehicle,
        fullVehicleNumber=vehicle_number,
        found=found,
        canSendRequest=can_send_request,
        confidence=confidence,
        message="Vehicle identified successfully" if found else "Vehicle not registered in the system"
    )
