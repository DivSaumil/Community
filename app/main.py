from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.api.v1 import auth, users, finance, complaints, notices, visitors

# Initialize FastAPI App
app = FastAPI(
    title=settings.PROJECT_NAME,
    description="Backend API for Society / RWA Management Platform in India.",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

# Set CORS middleware
if settings.BACKEND_CORS_ORIGINS:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[str(origin) for origin in settings.BACKEND_CORS_ORIGINS],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )


# Root Healthcheck endpoint
@app.get("/", status_code=200)
async def root():
    """Service status and health check."""
    return {
        "status": "online",
        "service": settings.PROJECT_NAME,
        "environment": settings.ENVIRONMENT,
        "version": "1.0.0",
        "documentation": "/docs"
    }


# Include Routers
app.include_router(auth.router, prefix="/api/v1/auth", tags=["Authentication"])
app.include_router(users.router, prefix="/api/v1/users", tags=["Users & Flats"])
app.include_router(finance.router, prefix="/api/v1/finance", tags=["Financials"])
app.include_router(complaints.router, prefix="/api/v1/complaints", tags=["Helpdesk Tickets"])
app.include_router(notices.router, prefix="/api/v1/notices", tags=["Notice Board & Polls"])
app.include_router(visitors.router, prefix="/api/v1/visitors", tags=["Gate & Visitors"])
