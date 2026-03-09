"""
Vehicle Obstruction Resolution System Backend API
Main application entry point
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from apscheduler.schedulers.background import BackgroundScheduler

from app.core.config import settings
from app.core.database import engine, Base
from app.api.v1 import api_router
from app.services.request_expiration_service import run_expiration_job


# Initialize scheduler
scheduler = BackgroundScheduler()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan events"""
    # Startup
    print("Starting Vehicle Obstruction Resolution API...")
    
    # Initialize Firebase
    try:
        from app.services.firebase_service import firebase_service
        firebase_service.initialize()
    except Exception as e:
        print(f"Warning: Firebase initialization failed: {e}")
    
    # Start the request expiration scheduler
    # Validates Requirement 12.1: Run scheduled job every 5 minutes
    try:
        scheduler.add_job(
            run_expiration_job,
            'interval',
            minutes=5,
            id='expire_requests',
            name='Expire pending requests',
            replace_existing=True
        )
        scheduler.start()
        print("Request expiration scheduler started (runs every 5 minutes)")
    except Exception as e:
        print(f"Warning: Scheduler initialization failed: {e}")
    
    yield
    
    # Shutdown
    print("Shutting down Vehicle Obstruction Resolution API...")
    
    # Shutdown scheduler
    try:
        scheduler.shutdown()
        print("Request expiration scheduler stopped")
    except Exception as e:
        print(f"Warning: Scheduler shutdown failed: {e}")


app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    description="Privacy-focused vehicle blocking resolution system",
    lifespan=lifespan,
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API router
app.include_router(api_router, prefix=settings.API_V1_PREFIX)


@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "message": "Vehicle Obstruction Resolution API",
        "version": settings.VERSION,
        "status": "running"
    }


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy"}
