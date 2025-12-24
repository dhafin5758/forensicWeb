"""
Configuration management for the forensics platform.
Supports environment-based configuration with secure defaults.
"""

import os
from pathlib import Path
from typing import Optional
from pydantic_settings import BaseSettings
from pydantic import Field, validator


class Settings(BaseSettings):
    """Application configuration with validation."""
    
    # Application
    APP_NAME: str = "Volatility3 Forensics Platform"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = Field(default=False, env="DEBUG")
    ENVIRONMENT: str = Field(default="production", env="ENVIRONMENT")
    
    # API
    API_V1_PREFIX: str = "/api/v1"
    API_HOST: str = Field(default="0.0.0.0", env="API_HOST")
    API_PORT: int = Field(default=8000, env="API_PORT")
    API_WORKERS: int = Field(default=4, env="API_WORKERS")
    
    # Security
    SECRET_KEY: str = Field(..., env="SECRET_KEY")
    JWT_ALGORITHM: str = "HS256"
    JWT_EXPIRATION_HOURS: int = 24
    ALLOWED_ORIGINS: list[str] = Field(
        default=["http://localhost:3000"],
        env="ALLOWED_ORIGINS"
    )
    
    # Upload Constraints
    MAX_UPLOAD_SIZE_GB: int = Field(default=10, env="MAX_UPLOAD_SIZE_GB")
    MAX_UPLOAD_SIZE_BYTES: int = 0  # Calculated in validator
    ALLOWED_EXTENSIONS: set[str] = {
        ".raw", ".mem", ".dmp", ".vmem", ".bin", ".dd", ".lime", ".elf"
    }
    CHUNK_SIZE_MB: int = 10  # Streaming upload chunk size
    
    # Storage Paths
    BASE_DIR: Path = Path(__file__).resolve().parent.parent
    STORAGE_ROOT: Path = Field(default=Path("/var/forensics"), env="STORAGE_ROOT")
    UPLOAD_DIR: Path = Field(default=None)
    ARTIFACT_DIR: Path = Field(default=None)
    RESULT_DIR: Path = Field(default=None)
    LOG_DIR: Path = Field(default=None)
    
    # Database
    DATABASE_URL: str = Field(
        default="postgresql+asyncpg://forensics:forensics@localhost/forensics_db",
        env="DATABASE_URL"
    )
    DB_POOL_SIZE: int = 10
    DB_MAX_OVERFLOW: int = 20
    
    # Redis
    REDIS_URL: str = Field(
        default="redis://localhost:6379/0",
        env="REDIS_URL"
    )
    REDIS_CACHE_TTL: int = 3600  # 1 hour
    
    # Celery
    CELERY_BROKER_URL: str = Field(
        default="redis://localhost:6379/1",
        env="CELERY_BROKER_URL"
    )
    CELERY_RESULT_BACKEND: str = Field(
        default="redis://localhost:6379/2",
        env="CELERY_RESULT_BACKEND"
    )
    CELERY_TASK_TIMEOUT: int = 14400  # 4 hours
    CELERY_WORKER_CONCURRENCY: int = Field(default=2, env="CELERY_WORKER_CONCURRENCY")
    
    # Volatility 3
    VOL3_PATH: str = Field(default="/usr/local/bin/vol", env="VOL3_PATH")
    VOL3_PLUGINS: list[str] = [
        "pslist",
        "pstree",
        "netscan",
        "cmdline",
        "malfind",
        "filescan",
        "dumpfiles",
        "handles",
        "vadinfo",
        "dlllist",
        "modscan",
    ]
    VOL3_CRITICAL_PLUGINS: list[str] = [
        "pslist",
        "pstree",
        "netscan",
        "cmdline",
        "malfind",
    ]
    VOL3_TIMEOUT_SECONDS: int = 3600  # Per plugin timeout
    
    # Post-Processing Tools
    BINWALK_PATH: str = Field(default="/usr/bin/binwalk", env="BINWALK_PATH")
    EXIFTOOL_PATH: str = Field(default="/usr/bin/exiftool", env="EXIFTOOL_PATH")
    BINWALK_ENABLED: bool = True
    EXIFTOOL_ENABLED: bool = True
    
    # Process Isolation
    USE_DOCKER_ISOLATION: bool = Field(default=True, env="USE_DOCKER_ISOLATION")
    DOCKER_WORKER_IMAGE: str = "forensics-worker:latest"
    WORKER_MEMORY_LIMIT: str = "4g"
    WORKER_CPU_LIMIT: str = "2.0"
    
    # Rate Limiting
    RATE_LIMIT_UPLOADS_PER_HOUR: int = 10
    RATE_LIMIT_API_PER_MINUTE: int = 60
    
    # Logging
    LOG_LEVEL: str = Field(default="INFO", env="LOG_LEVEL")
    LOG_FORMAT: str = "json"  # json or text
    LOG_RETENTION_DAYS: int = 30
    
    @validator("MAX_UPLOAD_SIZE_BYTES", always=True)
    def calculate_max_upload_bytes(cls, v, values):
        """Calculate bytes from GB."""
        return values.get("MAX_UPLOAD_SIZE_GB", 10) * 1024 * 1024 * 1024
    
    @validator("UPLOAD_DIR", "ARTIFACT_DIR", "RESULT_DIR", "LOG_DIR", always=True)
    def set_storage_paths(cls, v, values, field):
        """Set storage subdirectories."""
        storage_root = values.get("STORAGE_ROOT", Path("/var/forensics"))
        mapping = {
            "UPLOAD_DIR": "uploads",
            "ARTIFACT_DIR": "artifacts",
            "RESULT_DIR": "results",
            "LOG_DIR": "logs",
        }
        return storage_root / mapping[field.name]
    
    def ensure_directories(self) -> None:
        """Create required directories if they don't exist."""
        for path in [
            self.UPLOAD_DIR,
            self.ARTIFACT_DIR,
            self.RESULT_DIR,
            self.LOG_DIR,
        ]:
            path.mkdir(parents=True, exist_ok=True)
            # Set restrictive permissions for security
            os.chmod(path, 0o750)
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = True


# Global settings instance
settings = Settings()
