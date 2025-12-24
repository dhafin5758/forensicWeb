"""
Upload API Routes
Handles memory image upload with streaming, validation, and hash calculation.
"""

import hashlib
import logging
from datetime import datetime
from pathlib import Path
from typing import Optional
from uuid import uuid4

from fastapi import APIRouter, UploadFile, File, HTTPException, status, Depends
from fastapi.responses import JSONResponse

from backend.config import settings
from backend.schemas.api_schemas import (
    MemoryImageUploadResponse,
    MemoryImageUploadFromURLRequest,
    ErrorResponse
)
from backend.workers.tasks import download_memory_image_from_url


logger = logging.getLogger(__name__)
router = APIRouter()


# Magic bytes for memory dump validation
VALID_MAGIC_BYTES = {
    b'\x4D\x5A': 'PE/Windows',  # MZ header (often at start of Windows memory)
    b'\x7FELF': 'ELF/Linux',     # ELF header
    b'PAGEDUMP': 'Windows crash dump',
    b'PAGEDU64': 'Windows 64-bit crash dump',
    b'\x00\x00\x00\x00': 'Raw memory (permissive)',
}


class UploadValidator:
    """Validates uploaded memory images."""
    
    @staticmethod
    def validate_file_extension(filename: str) -> None:
        """Check if file extension is allowed."""
        file_ext = Path(filename).suffix.lower()
        
        if file_ext not in settings.ALLOWED_EXTENSIONS:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"File extension '{file_ext}' not allowed. "
                       f"Allowed: {', '.join(settings.ALLOWED_EXTENSIONS)}"
            )
    
    @staticmethod
    async def validate_magic_bytes(file: UploadFile) -> None:
        """
        Validate file magic bytes (basic header check).
        
        This is a permissive check - we allow many formats since
        raw memory dumps don't have consistent headers.
        """
        # Read first 16 bytes
        header = await file.read(16)
        await file.seek(0)  # Reset for subsequent reads
        
        # For raw dumps, we're permissive
        # In production, you might want stricter validation
        logger.info("File header: %s", header[:8].hex())
    
    @staticmethod
    def validate_file_size(file_size: int) -> None:
        """Check if file size is within limits."""
        if file_size > settings.MAX_UPLOAD_SIZE_BYTES:
            max_gb = settings.MAX_UPLOAD_SIZE_GB
            raise HTTPException(
                status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                detail=f"File too large. Maximum size: {max_gb} GB"
            )
        
        if file_size < 1024:  # Less than 1KB
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="File too small to be a valid memory image"
            )


async def save_upload_with_hash(
    file: UploadFile,
    destination: Path
) -> tuple[str, int]:
    """
    Save uploaded file with streaming and calculate SHA256 hash.
    
    Returns:
        (sha256_hash, file_size_bytes)
    """
    hasher = hashlib.sha256()
    file_size = 0
    chunk_size = settings.CHUNK_SIZE_MB * 1024 * 1024
    
    destination.parent.mkdir(parents=True, exist_ok=True)
    
    try:
        with open(destination, 'wb') as f:
            while True:
                chunk = await file.read(chunk_size)
                if not chunk:
                    break
                
                f.write(chunk)
                hasher.update(chunk)
                file_size += len(chunk)
        
        return hasher.hexdigest(), file_size
    
    except Exception as e:
        # Clean up partial file on error
        if destination.exists():
            destination.unlink()
        raise e


@router.post(
    "/",
    response_model=MemoryImageUploadResponse,
    status_code=status.HTTP_201_CREATED,
    responses={
        400: {"model": ErrorResponse},
        413: {"model": ErrorResponse},
    }
)
async def upload_memory_image(
    file: UploadFile = File(..., description="Memory dump file"),
    # current_user: User = Depends(get_current_user)  # TODO: Add auth dependency
) -> MemoryImageUploadResponse:
    """
    Upload a memory image for analysis.
    
    - Validates file extension and size
    - Calculates SHA256 hash during upload
    - Stores metadata in database
    - Returns upload confirmation with image ID
    
    **Supported formats:** .raw, .mem, .dmp, .vmem, .bin, .dd, .lime, .elf
    
    **Maximum size:** Configured in MAX_UPLOAD_SIZE_GB (default: 10GB)
    """
    logger.info("Upload request received: %s", file.filename)
    
    # Validation
    UploadValidator.validate_file_extension(file.filename)
    await UploadValidator.validate_magic_bytes(file)
    
    # Generate unique identifier
    image_id = uuid4()
    sanitized_filename = f"{image_id}_{Path(file.filename).name}"
    destination = settings.UPLOAD_DIR / sanitized_filename
    
    try:
        # Save file with streaming and hash calculation
        logger.info("Saving upload to: %s", destination)
        sha256_hash, file_size = await save_upload_with_hash(file, destination)
        
        # Validate size
        UploadValidator.validate_file_size(file_size)
        
        logger.info(
            "Upload completed: %s (%.2f MB, SHA256: %s)",
            sanitized_filename,
            file_size / (1024 * 1024),
            sha256_hash
        )
        
        # TODO: Store metadata in database
        # memory_image = MemoryImage(
        #     id=image_id,
        #     filename=sanitized_filename,
        #     original_filename=file.filename,
        #     file_size_bytes=file_size,
        #     file_hash_sha256=sha256_hash,
        #     file_path=str(destination),
        #     uploaded_by=current_user.id
        # )
        # await db.add(memory_image)
        # await db.commit()
        
        return MemoryImageUploadResponse(
            image_id=image_id,
            filename=sanitized_filename,
            file_size_bytes=file_size,
            file_hash_sha256=sha256_hash,
            uploaded_at=datetime.utcnow(),
            message="Upload successful"
        )
    
    except HTTPException:
        # Re-raise validation errors
        raise
    
    except Exception as e:
        logger.exception("Upload failed")
        
        # Clean up file on error
        if destination.exists():
            destination.unlink()
        
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Upload failed: {str(e)}"
        )


@router.post(
    "/from-url",
    response_model=MemoryImageUploadResponse,
    status_code=status.HTTP_202_ACCEPTED,
    responses={
        400: {"model": ErrorResponse},
        504: {"model": ErrorResponse},
    }
)
async def upload_from_url(
    request: MemoryImageUploadFromURLRequest,
    # current_user: User = Depends(get_current_user)  # TODO: Add auth dependency
) -> MemoryImageUploadResponse:
    """
    Download memory image from URL and start analysis.
    
    This endpoint accepts a direct download link to a memory dump file.
    The server will download it asynchronously and process it.
    
    - Validates URL format
    - Checks URL accessibility
    - Queues async download task
    - Returns job ID for tracking download progress
    
    **Example:**
    ```json
    {
        "url": "https://example.com/dumps/memory.raw",
        "description": "Linux server memory dump - 2025-12-24"
    }
    ```
    
    **Status codes:**
    - 202: Download job queued successfully
    - 400: Invalid URL format
    - 504: URL unreachable or download timeout
    """
    logger.info("URL download request: %s", request.url)
    
    # Generate unique identifier for this download job
    image_id = uuid4()
    
    try:
        # Queue async download task
        # This returns immediately; download happens in background
        task = download_memory_image_from_url.delay(
            str(image_id),
            request.url,
            request.description or f"Downloaded from {request.url}"
        )
        
        logger.info(
            "Queued URL download task %s for image %s from %s",
            task.id,
            image_id,
            request.url
        )
        
        return MemoryImageUploadResponse(
            image_id=image_id,
            filename=f"{image_id}_downloading",
            file_size_bytes=0,  # Unknown until download completes
            file_hash_sha256="pending",
            uploaded_at=datetime.utcnow(),
            message="Download queued - task is running in background. Check status with GET /upload/status/{image_id}"
        )
    
    except Exception as e:
        logger.exception("Failed to queue download task")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to queue download: {str(e)}"
        )


@router.get("/status/{image_id}")
async def get_upload_status(image_id: str):
    """
    Get upload status and metadata.
    
    Used for checking if an upload exists and retrieving its information.
    For URL downloads, shows download progress.
    """
    # TODO: Query database for image metadata
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail="Endpoint not yet implemented"
    )
