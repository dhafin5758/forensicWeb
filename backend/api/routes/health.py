"""
Health Check API Routes
System health monitoring and diagnostics.
"""

import logging
import os
import time
from datetime import datetime
from pathlib import Path

from fastapi import APIRouter, status
from fastapi.responses import JSONResponse

from backend.config import settings
from backend.schemas.api_schemas import HealthCheckResponse


logger = logging.getLogger(__name__)
router = APIRouter()

# Track application start time
_start_time = time.time()


@router.get(
    "/",
    response_model=HealthCheckResponse,
    status_code=status.HTTP_200_OK
)
async def health_check() -> HealthCheckResponse:
    """
    System health check endpoint.
    
    Returns:
    - Overall system status
    - Individual service statuses
    - Uptime
    - Version information
    
    Status values:
    - **healthy**: All systems operational
    - **degraded**: Some non-critical services down
    - **unhealthy**: Critical services unavailable
    
    Use this for:
    - Load balancer health checks
    - Monitoring/alerting
    - Deployment validation
    """
    services = {}
    overall_status = "healthy"
    
    # Check filesystem access
    try:
        settings.UPLOAD_DIR.exists()
        services["filesystem"] = "healthy"
    except Exception as e:
        logger.error("Filesystem check failed: %s", e)
        services["filesystem"] = "unhealthy"
        overall_status = "degraded"
    
    # Check Volatility 3
    try:
        vol_path = Path(settings.VOL3_PATH)
        if vol_path.exists():
            services["volatility3"] = "healthy"
        else:
            services["volatility3"] = "unavailable"
            overall_status = "degraded"
    except Exception as e:
        logger.error("Volatility check failed: %s", e)
        services["volatility3"] = "unhealthy"
        overall_status = "degraded"
    
    # Check binwalk
    try:
        binwalk_path = Path(settings.BINWALK_PATH)
        if binwalk_path.exists():
            services["binwalk"] = "healthy"
        else:
            services["binwalk"] = "unavailable"
    except Exception:
        services["binwalk"] = "unhealthy"
    
    # Check exiftool
    try:
        exiftool_path = Path(settings.EXIFTOOL_PATH)
        if exiftool_path.exists():
            services["exiftool"] = "healthy"
        else:
            services["exiftool"] = "unavailable"
    except Exception:
        services["exiftool"] = "unhealthy"
    
    # TODO: Check database connection
    # try:
    #     await db.execute(text("SELECT 1"))
    #     services["database"] = "healthy"
    # except Exception as e:
    #     logger.error("Database check failed: %s", e)
    #     services["database"] = "unhealthy"
    #     overall_status = "unhealthy"
    
    services["database"] = "not_configured"
    
    # TODO: Check Redis connection
    # try:
    #     await redis.ping()
    #     services["redis"] = "healthy"
    # except Exception as e:
    #     logger.error("Redis check failed: %s", e)
    #     services["redis"] = "unhealthy"
    #     overall_status = "degraded"
    
    services["redis"] = "not_configured"
    
    # TODO: Check Celery workers
    # try:
    #     inspect = celery_app.control.inspect()
    #     active_workers = inspect.active()
    #     if active_workers:
    #         services["celery_workers"] = "healthy"
    #     else:
    #         services["celery_workers"] = "no_workers"
    #         overall_status = "degraded"
    # except Exception as e:
    #     logger.error("Celery check failed: %s", e)
    #     services["celery_workers"] = "unhealthy"
    #     overall_status = "degraded"
    
    services["celery_workers"] = "not_configured"
    
    uptime = time.time() - _start_time
    
    return HealthCheckResponse(
        status=overall_status,
        version=settings.APP_VERSION,
        timestamp=datetime.utcnow(),
        services=services,
        uptime_seconds=uptime
    )


@router.get(
    "/storage",
    description="Storage usage statistics"
)
async def storage_stats():
    """
    Get storage usage statistics.
    
    Returns:
    - Total disk usage by category
    - Number of files
    - Available space
    """
    stats = {
        "upload_dir": {},
        "artifact_dir": {},
        "result_dir": {},
        "total_used_gb": 0.0,
    }
    
    try:
        # Calculate directory sizes
        for dir_name, dir_path in [
            ("upload_dir", settings.UPLOAD_DIR),
            ("artifact_dir", settings.ARTIFACT_DIR),
            ("result_dir", settings.RESULT_DIR),
        ]:
            if dir_path.exists():
                total_size = sum(
                    f.stat().st_size for f in dir_path.rglob('*') if f.is_file()
                )
                file_count = sum(1 for f in dir_path.rglob('*') if f.is_file())
                
                stats[dir_name] = {
                    "size_bytes": total_size,
                    "size_gb": round(total_size / (1024**3), 2),
                    "file_count": file_count
                }
                stats["total_used_gb"] += stats[dir_name]["size_gb"]
            else:
                stats[dir_name] = {"error": "Directory not found"}
        
        # Get available disk space
        statvfs = os.statvfs(settings.STORAGE_ROOT)
        available_bytes = statvfs.f_bavail * statvfs.f_frsize
        stats["available_gb"] = round(available_bytes / (1024**3), 2)
        
        return stats
    
    except Exception as e:
        logger.exception("Storage stats failed")
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"error": str(e)}
        )


@router.get(
    "/ready",
    description="Readiness probe for Kubernetes"
)
async def readiness_probe():
    """
    Kubernetes readiness probe.
    
    Returns 200 OK when the application is ready to accept traffic.
    Checks critical dependencies only.
    """
    # Check database connection
    # TODO: Implement database check
    
    return {"ready": True}


@router.get(
    "/live",
    description="Liveness probe for Kubernetes"
)
async def liveness_probe():
    """
    Kubernetes liveness probe.
    
    Returns 200 OK when the application is running.
    Simple check to verify the process is alive.
    """
    return {"alive": True}
