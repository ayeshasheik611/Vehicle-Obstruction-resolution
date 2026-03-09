"""
Report endpoints for abuse reporting

**Validates Requirements**: 14
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from uuid import UUID

from app.core.database import get_db
from app.api.dependencies import get_current_user
from app.models.user import User
from app.models.report import ReportReason
from app.schemas.report import CreateReportRequest, CreateReportResponse
from app.services.report_service import report_service


router = APIRouter()


@router.post("/create", response_model=CreateReportResponse)
async def create_report(
    request: CreateReportRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Create an abuse report
    
    This endpoint:
    1. Validates target user is different from reporter (Requirement 14.2)
    2. Validates reason is valid enum value (Requirement 14.3)
    3. Checks daily report limit (5 reports/day) (Requirement 14.4)
    4. Creates report record (Requirement 14.5)
    5. Checks if target has 3+ reports (Requirement 14.6)
    6. Flags account for review if threshold reached (Requirement 14.7)
    7. Returns report ID and success message (Requirement 14.8)
    
    **Validates Requirements**: 14.1, 14.2, 14.3, 14.4, 14.5, 14.6, 14.7, 14.8, 21.8
    
    Args:
        request: CreateReportRequest with target user and reason
        db: Database session
        current_user: Authenticated user
        
    Returns:
        CreateReportResponse with report ID and success message
        
    Raises:
        HTTPException: If validation fails or rate limit exceeded
    """
    try:
        # Create report using service
        report = report_service.create_report(
            db=db,
            reporter_id=current_user.id,
            target_user_id=UUID(request.targetUserId),
            reason=ReportReason(request.reason),
            description=request.description
        )
        
        return CreateReportResponse(
            success=True,
            reportId=str(report.id),
            message="Report submitted successfully. We will review it shortly."
        )
        
    except ValueError as e:
        # Handle validation errors and rate limits
        error_message = str(e)
        
        if "Daily report limit" in error_message:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail=error_message
            )
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=error_message
            )
    
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create report: {str(e)}"
        )
