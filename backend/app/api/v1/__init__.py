"""
API v1 router
"""
from fastapi import APIRouter
from app.api.v1.endpoints import auth, notification, request, vehicle, report, profile

api_router = APIRouter()

# Include authentication router
api_router.include_router(auth.router, prefix="/auth", tags=["authentication"])

# Include notification router
api_router.include_router(notification.router, prefix="/notification", tags=["notification"])

# Include request router
api_router.include_router(request.router, prefix="/request", tags=["request"])

# Include vehicle router
api_router.include_router(vehicle.router, prefix="/vehicle", tags=["vehicle"])

# Include report router
api_router.include_router(report.router, prefix="/report", tags=["report"])

# Include profile router
api_router.include_router(profile.router, prefix="/profile", tags=["profile"])
