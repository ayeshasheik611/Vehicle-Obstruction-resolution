"""
Report endpoints for abuse reporting

**Validates Requirements**: 14
"""
from fastapi import APIRouter, Depends, HTTPException, status
from uuid import UUID

from app.api.dependencies import get_current_user
from app.models.user import User
from app.models.report import ReportReason
from app.schemas.report import CreateReportRequest, CreateReportResponse
from app.services.report_service import report_service


router = APIRouter()


@router.post("/create", response_model=CreateReportResponse)
async def create_report(
    request: CreateReportRequest,
    current_user: User = Depends(get_current_user)
):
    """
    Create an abuse report
    
    **Validates Requirements**: 14.1, 14.2, 14.3, 14.4, 14.5, 14.6, 14.7, 14.8, 21.8
    """
    try:
        report = await report_service.create_report(
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
