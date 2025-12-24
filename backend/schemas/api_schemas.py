"""
Pydantic schemas for API request/response validation.
Defines the contract between frontend and backend.
"""

from datetime import datetime
from typing import Any, Dict, List, Optional
from uuid import UUID

from pydantic import BaseModel, Field, validator


# ============================================================================
# Authentication Schemas
# ============================================================================

class UserLogin(BaseModel):
    """User login request."""
    username: str = Field(..., min_length=3, max_length=64)
    password: str = Field(..., min_length=8)


class UserCreate(BaseModel):
    """User registration request."""
    username: str = Field(..., min_length=3, max_length=64)
    email: str = Field(..., regex=r'^[\w\.-]+@[\w\.-]+\.\w+$')
    password: str = Field(..., min_length=8)


class UserResponse(BaseModel):
    """User information response."""
    id: UUID
    username: str
    email: str
    is_active: bool
    is_admin: bool
    created_at: datetime
    
    class Config:
        from_attributes = True


class Token(BaseModel):
    """JWT token response."""
    access_token: str
    token_type: str = "bearer"
    expires_at: datetime


# ============================================================================
# Memory Image Schemas
# ============================================================================

class MemoryImageUploadFromURLRequest(BaseModel):
    """Request to download memory image from URL."""
    url: str = Field(..., description="Direct download URL for memory image")
    description: Optional[str] = Field(None, max_length=256, description="Optional description")
    
    @validator('url')
    def validate_url(cls, v):
        """Validate URL format."""
        if not v.startswith(('http://', 'https://')):
            raise ValueError('URL must start with http:// or https://')
        if len(v) > 2048:
            raise ValueError('URL too long')
        return v


class MemoryImageUploadResponse(BaseModel):
    """Response after successful upload."""
    image_id: UUID
    filename: str
    file_size_bytes: int
    file_hash_sha256: str
    uploaded_at: datetime
    message: str = "Upload successful"


class MemoryImageInfo(BaseModel):
    """Memory image metadata."""
    id: UUID
    filename: str
    original_filename: str
    file_size_bytes: int
    file_hash_sha256: str
    uploaded_at: datetime
    detected_os: Optional[str]
    detected_profile: Optional[str]
    detection_confidence: Optional[float]
    
    class Config:
        from_attributes = True


# ============================================================================
# Analysis Job Schemas
# ============================================================================

class JobCreate(BaseModel):
    """Request to create a new analysis job."""
    memory_image_id: UUID
    plugins: Optional[List[str]] = None  # If None, run all critical plugins
    priority: int = Field(default=5, ge=1, le=10)


class JobStatus(BaseModel):
    """Job status information."""
    id: UUID
    status: str
    memory_image_id: UUID
    created_at: datetime
    started_at: Optional[datetime]
    completed_at: Optional[datetime]
    total_plugins: int
    completed_plugins: int
    failed_plugins: int
    artifacts_extracted: int
    error_message: Optional[str]
    
    class Config:
        from_attributes = True


class JobListResponse(BaseModel):
    """List of jobs with pagination."""
    jobs: List[JobStatus]
    total: int
    page: int
    page_size: int


# ============================================================================
# Plugin Result Schemas
# ============================================================================

class PluginResultSummary(BaseModel):
    """Summary of a plugin execution."""
    id: UUID
    plugin_name: str
    success: bool
    row_count: int
    execution_time_seconds: Optional[float]
    error_message: Optional[str]
    started_at: datetime
    completed_at: Optional[datetime]
    
    class Config:
        from_attributes = True


class PluginResultDetail(BaseModel):
    """Detailed plugin result with data."""
    id: UUID
    plugin_name: str
    success: bool
    row_count: int
    execution_time_seconds: Optional[float]
    result_data: Optional[List[Dict[str, Any]]]  # Parsed JSON data
    error_message: Optional[str]
    
    class Config:
        from_attributes = True


class JobResultsResponse(BaseModel):
    """Complete results for a job."""
    job_id: UUID
    status: str
    plugins: List[PluginResultSummary]
    artifacts_count: int


# ============================================================================
# Artifact Schemas
# ============================================================================

class ArtifactInfo(BaseModel):
    """Extracted artifact metadata."""
    id: UUID
    artifact_type: str
    source_plugin: str
    filename: str
    file_size_bytes: int
    file_hash_sha256: str
    process_pid: Optional[int]
    process_name: Optional[str]
    memory_offset: Optional[int]
    binwalk_analyzed: bool
    exiftool_analyzed: bool
    extracted_at: datetime
    
    class Config:
        from_attributes = True


class ArtifactDetail(BaseModel):
    """Detailed artifact information with post-processing results."""
    id: UUID
    artifact_type: str
    source_plugin: str
    filename: str
    file_size_bytes: int
    file_hash_sha256: str
    process_pid: Optional[int]
    process_name: Optional[str]
    binwalk_results: Optional[Dict[str, Any]]
    exiftool_metadata: Optional[Dict[str, Any]]
    extracted_at: datetime
    download_url: str
    
    class Config:
        from_attributes = True


class ArtifactListResponse(BaseModel):
    """List of artifacts for a job."""
    job_id: UUID
    artifacts: List[ArtifactInfo]
    total: int


# ============================================================================
# Dashboard Schemas
# ============================================================================

class DashboardStats(BaseModel):
    """Dashboard statistics."""
    total_jobs: int
    running_jobs: int
    completed_jobs: int
    failed_jobs: int
    total_images_uploaded: int
    total_artifacts_extracted: int
    storage_used_gb: float
    recent_jobs: List[JobStatus]


# ============================================================================
# Error Response Schemas
# ============================================================================

class ErrorResponse(BaseModel):
    """Standard error response."""
    error: str
    detail: Optional[str] = None
    error_code: Optional[str] = None
    timestamp: datetime = Field(default_factory=datetime.utcnow)


# ============================================================================
# Health Check Schema
# ============================================================================

class HealthCheckResponse(BaseModel):
    """System health status."""
    status: str  # "healthy" | "degraded" | "unhealthy"
    version: str
    timestamp: datetime
    services: Dict[str, str]  # service_name -> status
    uptime_seconds: float
