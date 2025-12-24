"""
Database models for the forensics platform.
Uses SQLAlchemy 2.0 async API with PostgreSQL.
"""

from datetime import datetime
from enum import Enum as PyEnum
from typing import Optional
from uuid import uuid4

from sqlalchemy import (
    String, Integer, Float, Boolean, Text, JSON, DateTime, Enum,
    ForeignKey, Index
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID


class Base(DeclarativeBase):
    """Base class for all models."""
    pass


class JobStatus(str, PyEnum):
    """Job execution states."""
    PENDING = "pending"
    VALIDATING = "validating"
    PROFILING = "profiling"
    ANALYZING = "analyzing"
    EXTRACTING = "extracting"
    POST_PROCESSING = "post_processing"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class ArtifactType(str, PyEnum):
    """Types of extracted artifacts."""
    PROCESS_DUMP = "process_dump"
    MALFIND_REGION = "malfind_region"
    EXTRACTED_FILE = "extracted_file"
    NETWORK_PCAP = "network_pcap"
    REGISTRY_HIVE = "registry_hive"
    OTHER = "other"


class User(Base):
    """User accounts for authentication."""
    __tablename__ = "users"
    
    id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid4
    )
    username: Mapped[str] = mapped_column(String(64), unique=True, nullable=False, index=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    is_admin: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    last_login: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    
    # Relationships
    jobs: Mapped[list["AnalysisJob"]] = relationship(
        "AnalysisJob",
        back_populates="user",
        cascade="all, delete-orphan"
    )


class MemoryImage(Base):
    """Uploaded memory images metadata."""
    __tablename__ = "memory_images"
    
    id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid4
    )
    filename: Mapped[str] = mapped_column(String(255), nullable=False)
    original_filename: Mapped[str] = mapped_column(String(255), nullable=False)
    file_size_bytes: Mapped[int] = mapped_column(Integer, nullable=False)
    file_hash_sha256: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    file_path: Mapped[str] = mapped_column(Text, nullable=False)
    
    # Metadata
    uploaded_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    uploaded_by: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id"),
        nullable=False
    )
    
    # Detection results
    detected_os: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    detected_profile: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    detection_confidence: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    
    # Relationships
    jobs: Mapped[list["AnalysisJob"]] = relationship(
        "AnalysisJob",
        back_populates="memory_image",
        cascade="all, delete-orphan"
    )
    
    __table_args__ = (
        Index("idx_memory_image_hash", "file_hash_sha256"),
        Index("idx_memory_image_uploaded", "uploaded_at"),
    )


class AnalysisJob(Base):
    """Analysis job tracking."""
    __tablename__ = "analysis_jobs"
    
    id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid4
    )
    
    # Job metadata
    status: Mapped[JobStatus] = mapped_column(
        Enum(JobStatus),
        default=JobStatus.PENDING,
        nullable=False,
        index=True
    )
    priority: Mapped[int] = mapped_column(Integer, default=5)  # 1-10, higher = more urgent
    
    # References
    memory_image_id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("memory_images.id"),
        nullable=False
    )
    user_id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id"),
        nullable=False
    )
    
    # Timing
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    started_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    
    # Execution details
    celery_task_id: Mapped[Optional[str]] = mapped_column(String(128), nullable=True, index=True)
    worker_node: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    error_traceback: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    
    # Configuration
    plugins_requested: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    plugins_completed: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    
    # Statistics
    total_plugins: Mapped[int] = mapped_column(Integer, default=0)
    completed_plugins: Mapped[int] = mapped_column(Integer, default=0)
    failed_plugins: Mapped[int] = mapped_column(Integer, default=0)
    artifacts_extracted: Mapped[int] = mapped_column(Integer, default=0)
    
    # Relationships
    user: Mapped["User"] = relationship("User", back_populates="jobs")
    memory_image: Mapped["MemoryImage"] = relationship("MemoryImage", back_populates="jobs")
    plugin_results: Mapped[list["PluginResult"]] = relationship(
        "PluginResult",
        back_populates="job",
        cascade="all, delete-orphan"
    )
    artifacts: Mapped[list["Artifact"]] = relationship(
        "Artifact",
        back_populates="job",
        cascade="all, delete-orphan"
    )
    
    __table_args__ = (
        Index("idx_job_status", "status"),
        Index("idx_job_created", "created_at"),
        Index("idx_job_user", "user_id"),
    )


class PluginResult(Base):
    """Individual Volatility plugin execution results."""
    __tablename__ = "plugin_results"
    
    id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid4
    )
    
    # References
    job_id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("analysis_jobs.id"),
        nullable=False
    )
    
    # Plugin information
    plugin_name: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    plugin_version: Mapped[Optional[str]] = mapped_column(String(32), nullable=True)
    
    # Execution
    started_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    execution_time_seconds: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    
    # Results
    success: Mapped[bool] = mapped_column(Boolean, default=False)
    row_count: Mapped[int] = mapped_column(Integer, default=0)
    result_json_path: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    result_data: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)  # Small results only
    
    # Errors
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    stderr_output: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    
    # Relationships
    job: Mapped["AnalysisJob"] = relationship("AnalysisJob", back_populates="plugin_results")
    
    __table_args__ = (
        Index("idx_plugin_result_job", "job_id"),
        Index("idx_plugin_result_name", "plugin_name"),
    )


class Artifact(Base):
    """Extracted forensic artifacts."""
    __tablename__ = "artifacts"
    
    id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid4
    )
    
    # References
    job_id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("analysis_jobs.id"),
        nullable=False
    )
    
    # Artifact metadata
    artifact_type: Mapped[ArtifactType] = mapped_column(
        Enum(ArtifactType),
        nullable=False,
        index=True
    )
    source_plugin: Mapped[str] = mapped_column(String(64), nullable=False)
    filename: Mapped[str] = mapped_column(String(255), nullable=False)
    file_path: Mapped[str] = mapped_column(Text, nullable=False)
    file_size_bytes: Mapped[int] = mapped_column(Integer, nullable=False)
    file_hash_sha256: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    
    # Context
    process_pid: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    process_name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    memory_offset: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    
    # Post-processing results
    binwalk_analyzed: Mapped[bool] = mapped_column(Boolean, default=False)
    binwalk_results: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    exiftool_analyzed: Mapped[bool] = mapped_column(Boolean, default=False)
    exiftool_metadata: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    
    # Timing
    extracted_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    
    # Relationships
    job: Mapped["AnalysisJob"] = relationship("AnalysisJob", back_populates="artifacts")
    
    __table_args__ = (
        Index("idx_artifact_job", "job_id"),
        Index("idx_artifact_type", "artifact_type"),
        Index("idx_artifact_hash", "file_hash_sha256"),
    )
