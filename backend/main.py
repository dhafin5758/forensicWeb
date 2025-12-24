"""
FastAPI Application - Main Entry Point
Production-grade REST API for the forensics platform.
"""

import time
from contextlib import asynccontextmanager
from datetime import datetime

from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.responses import JSONResponse

from backend.config import settings
from backend.api.routes import upload, jobs, results, artifacts, auth, health


# Application startup/shutdown lifecycle
@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application lifespan handler.
    Initialize resources on startup, cleanup on shutdown.
    """
    # Startup
    settings.ensure_directories()
    
    # TODO: Initialize database connection pool
    # TODO: Initialize Redis connection
    # TODO: Verify external tools (volatility, binwalk, exiftool)
    
    yield
    
    # Shutdown
    # TODO: Close database connections
    # TODO: Close Redis connections
    pass


# Create FastAPI application
app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="Enterprise memory forensics automation platform",
    docs_url="/docs" if settings.DEBUG else None,
    redoc_url="/redoc" if settings.DEBUG else None,
    lifespan=lifespan
)


# ============================================================================
# Middleware Configuration
# ============================================================================

# CORS - Allow frontend access
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# GZip compression for responses
app.add_middleware(GZipMiddleware, minimum_size=1000)


# Request timing middleware
@app.middleware("http")
async def add_process_time_header(request: Request, call_next):
    """Add request processing time to response headers."""
    start_time = time.time()
    response = await call_next(request)
    process_time = time.time() - start_time
    response.headers["X-Process-Time"] = str(process_time)
    return response


# Exception handlers
@app.exception_handler(ValueError)
async def value_error_handler(request: Request, exc: ValueError):
    """Handle validation errors."""
    return JSONResponse(
        status_code=status.HTTP_400_BAD_REQUEST,
        content={
            "error": "Validation Error",
            "detail": str(exc),
            "timestamp": datetime.utcnow().isoformat()
        }
    )


@app.exception_handler(FileNotFoundError)
async def file_not_found_handler(request: Request, exc: FileNotFoundError):
    """Handle file not found errors."""
    return JSONResponse(
        status_code=status.HTTP_404_NOT_FOUND,
        content={
            "error": "Resource Not Found",
            "detail": str(exc),
            "timestamp": datetime.utcnow().isoformat()
        }
    )


# ============================================================================
# Route Registration
# ============================================================================

# API v1 routes
app.include_router(
    auth.router,
    prefix=f"{settings.API_V1_PREFIX}/auth",
    tags=["Authentication"]
)

app.include_router(
    upload.router,
    prefix=f"{settings.API_V1_PREFIX}/upload",
    tags=["Upload"]
)

app.include_router(
    jobs.router,
    prefix=f"{settings.API_V1_PREFIX}/jobs",
    tags=["Jobs"]
)

app.include_router(
    results.router,
    prefix=f"{settings.API_V1_PREFIX}/results",
    tags=["Results"]
)

app.include_router(
    artifacts.router,
    prefix=f"{settings.API_V1_PREFIX}/artifacts",
    tags=["Artifacts"]
)

app.include_router(
    health.router,
    prefix=f"{settings.API_V1_PREFIX}/health",
    tags=["Health"]
)


# Root endpoint
@app.get("/")
async def root():
    """API root endpoint."""
    return {
        "name": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "status": "operational",
        "docs": "/docs" if settings.DEBUG else "disabled",
        "api_version": "v1"
    }


if __name__ == "__main__":
    import uvicorn
    
    uvicorn.run(
        "main:app",
        host=settings.API_HOST,
        port=settings.API_PORT,
        workers=settings.API_WORKERS,
        log_level=settings.LOG_LEVEL.lower(),
        reload=settings.DEBUG
    )
