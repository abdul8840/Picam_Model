"""
PICAM Main Application Entry Point
Physics-based Intelligent Capacity and Money System
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import logging

from app.config import get_settings
from app.database import DatabaseManager
from app.api.routes import metrics, insights, roi, data
# Add to imports
from app.api.routes import admin

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application lifespan manager.
    Handles startup and shutdown events.
    """
    # Startup
    logger.info("Starting PICAM System...")
    settings = get_settings()
    
    # Connect to database
    await DatabaseManager.connect()
    logger.info(f"Connected to MongoDB: {settings.mongodb_database}")
    
    yield
    
    # Shutdown
    logger.info("Shutting down PICAM System...")
    await DatabaseManager.disconnect()
    logger.info("Cleanup complete")


# Create FastAPI application
settings = get_settings()

app = FastAPI(
    title="PICAM - Physics-based Intelligent Capacity and Money",
    description="""
    ## Hotel Operational Loss Detection System
    
    PICAM converts real hotel operational data into provable financial loss 
    using physics laws (Little's Law, Queueing Theory).
    
    ### Key Principles:
    - **Deterministic**: All calculations are reproducible
    - **Physics-Based**: Uses proven mathematical laws, not predictions
    - **Conservative**: Always calculates minimum provable loss
    - **Privacy-First**: No personal data stored, video processed in-memory only
    - **Auditable**: Complete traceability for every calculation
    
    ### Core Calculations:
    - **Little's Law**: L = λW (customers = arrival_rate × wait_time)
    - **Queueing Theory**: Wait times, utilization, capacity limits
    - **Entropy**: Operational variability as cost multiplier
    """,
    version=settings.app_version,
    lifespan=lifespan,
    docs_url="/api/docs",
    redoc_url="/api/redoc",
    openapi_url="/api/openapi.json"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Health check endpoint
@app.get("/health", tags=["System"])
async def health_check():
    """
    System health check endpoint.
    """
    db_health = await DatabaseManager.health_check()
    
    return {
        "status": "healthy" if db_health["connected"] else "degraded",
        "version": settings.app_version,
        "system": "PICAM",
        "database": db_health,
        "physics_engine": "operational",
        "privacy_mode": "enabled"
    }


@app.get("/", tags=["System"])
async def root():
    """
    Root endpoint with system information.
    """
    return {
        "system": "PICAM",
        "name": "Physics-based Intelligent Capacity and Money",
        "version": settings.app_version,
        "description": "Hotel operational loss detection using physics laws",
        "documentation": "/api/docs",
        "principles": [
            "Deterministic calculations",
            "Physics-based (Little's Law, Queueing Theory)",
            "Conservative lower-bound loss estimation",
            "Privacy-first (no personal data stored)",
            "Fully auditable"
        ]
    }


# Include API routers
app.include_router(
    data.router,
    prefix=f"{settings.api_prefix}/data",
    tags=["Data Ingestion"]
)

app.include_router(
    metrics.router,
    prefix=f"{settings.api_prefix}/metrics",
    tags=["Metrics & Calculations"]
)

app.include_router(
    insights.router,
    prefix=f"{settings.api_prefix}/insights",
    tags=["Daily Insights"]
)

app.include_router(
    roi.router,
    prefix=f"{settings.api_prefix}/roi",
    tags=["ROI Tracking"]
)

# Add to router includes (after ROI router)
app.include_router(
    admin.router,
    prefix=f"{settings.api_prefix}/admin",
    tags=["Administration"]
)


# Error handlers
@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    """
    Global exception handler for unhandled errors.
    """
    logger.error(f"Unhandled exception: {exc}", exc_info=True)
    return {
        "error": "Internal server error",
        "detail": str(exc) if settings.debug else "An error occurred",
        "traceable": True
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.debug
    )