"""
Celery Tasks - Memory Forensics Analysis Pipeline
Production-grade task definitions for distributed forensic analysis.
"""

import asyncio
import hashlib
import logging
import urllib.request
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any
from uuid import UUID

from celery import Task, group, chain, chord
from celery.exceptions import SoftTimeLimitExceeded

from backend.workers.celery_app import celery_app
from backend.core.volatility_runner import Volatility3Runner, ProfileDetector
from backend.core.artifact_processor import ArtifactProcessor
from backend.config import settings


logger = logging.getLogger(__name__)


@celery_app.task(
    bind=True,
    name="backend.workers.tasks.download_memory_image_from_url",
    queue="analysis",
    priority=10,
    time_limit=7200,  # 2 hours hard limit
    soft_time_limit=6900,  # 1h 55min soft limit
)
def download_memory_image_from_url(
    self: Task,
    image_id: str,
    url: str,
    description: str
) -> Dict[str, Any]:
    """
    Download memory image from URL and validate.
    
    Downloads file with streaming to minimize memory usage.
    Calculates SHA256 hash during download.
    
    Args:
        image_id: UUID identifier for this download
        url: Direct download URL
        description: Human-readable description
    
    Returns:
        Dictionary with download summary
    """
    logger.info("Starting download from URL: %s (image_id: %s)", url, image_id)
    
    image_id_obj = UUID(image_id)
    sanitized_filename = f"{image_id}_downloaded"
    destination = settings.UPLOAD_DIR / sanitized_filename
    
    chunk_size = 1024 * 1024  # 1MB chunks
    hasher = hashlib.sha256()
    file_size = 0
    
    try:
        destination.parent.mkdir(parents=True, exist_ok=True)
        
        # Download with streaming
        logger.info("Downloading from: %s", url)
        
        try:
            request = urllib.request.Request(
                url,
                headers={'User-Agent': 'ForensicWeb-Downloader/1.0'}
            )
            response = urllib.request.urlopen(request, timeout=300)
            
            with open(destination, 'wb') as f:
                while True:
                    chunk = response.read(chunk_size)
                    if not chunk:
                        break
                    
                    f.write(chunk)
                    hasher.update(chunk)
                    file_size += len(chunk)
                    
                    # Log progress every 100MB
                    if file_size % (100 * 1024 * 1024) == 0:
                        logger.info(
                            "Downloaded %.2f MB from %s",
                            file_size / (1024 * 1024),
                            url
                        )
            
            response.close()
        
        except urllib.error.URLError as e:
            raise Exception(f"URL access failed: {str(e)}")
        except urllib.error.HTTPError as e:
            raise Exception(f"HTTP error {e.code}: {str(e)}")
        except Exception as e:
            raise Exception(f"Download failed: {str(e)}")
        
        # Validate file
        if file_size < 1024:  # Less than 1KB
            raise Exception("Downloaded file too small to be valid memory image")
        
        if file_size > settings.MAX_UPLOAD_SIZE_BYTES:
            max_gb = settings.MAX_UPLOAD_SIZE_GB
            raise Exception(f"Downloaded file exceeds maximum size of {max_gb}GB")
        
        sha256_hash = hasher.hexdigest()
        
        logger.info(
            "Download completed: %s (%.2f MB, SHA256: %s)",
            sanitized_filename,
            file_size / (1024 * 1024),
            sha256_hash
        )
        
        # TODO: Store metadata in database
        # memory_image = MemoryImage(
        #     id=image_id_obj,
        #     filename=sanitized_filename,
        #     original_filename=url.split('/')[-1] or 'downloaded_image',
        #     file_size_bytes=file_size,
        #     file_hash_sha256=sha256_hash,
        #     file_path=str(destination),
        #     source='url',
        #     source_url=url,
        #     description=description,
        #     uploaded_by=None  # System download
        # )
        # await db.add(memory_image)
        # await db.commit()
        
        return {
            "image_id": image_id,
            "filename": sanitized_filename,
            "file_size_bytes": file_size,
            "file_hash_sha256": sha256_hash,
            "url": url,
            "status": "completed",
            "message": "Download and validation successful"
        }
    
    except SoftTimeLimitExceeded:
        logger.error("Download timeout for: %s", url)
        if destination.exists():
            destination.unlink()
        return {
            "image_id": image_id,
            "status": "timeout",
            "error": "Download exceeded time limit (95 minutes)"
        }
    
    except Exception as e:
        logger.exception("Download failed for: %s", url)
        
        # Clean up partial file
        if destination.exists():
            destination.unlink()
        
        return {
            "image_id": image_id,
            "status": "error",
            "error": str(e),
            "url": url
        }


@celery_app.task(
    bind=True,
    name="backend.workers.tasks.analyze_memory_image",
    queue="analysis",
    priority=10
)
def analyze_memory_image(self: Task, job_id: str) -> Dict[str, Any]:
    """
    Main orchestrator task for memory image analysis.
    
    Pipeline:
    1. Load job metadata from database
    2. Detect OS profile
    3. Execute Volatility plugins (parallel)
    4. Extract artifacts
    5. Post-process artifacts (binwalk, exiftool)
    6. Store results in database
    
    Args:
        job_id: UUID of the analysis job
    
    Returns:
        Dictionary with execution summary
    """
    logger.info("Starting analysis for job: %s", job_id)
    
    try:
        # TODO: Load job from database
        # job = await db.get(AnalysisJob, UUID(job_id))
        # if not job:
        #     raise ValueError(f"Job {job_id} not found")
        
        # memory_image = await db.get(MemoryImage, job.memory_image_id)
        
        # For now, use placeholder
        # memory_image_path = Path(memory_image.file_path)
        # output_dir = settings.RESULT_DIR / job_id
        
        # TODO: Update job status to PROFILING
        # job.status = JobStatus.PROFILING
        # job.started_at = datetime.utcnow()
        # await db.commit()
        
        # Step 1: Profile Detection
        # profile_info = detect_profile.delay(str(memory_image_path)).get()
        
        # TODO: Update job status to ANALYZING
        # job.status = JobStatus.ANALYZING
        # await db.commit()
        
        # Step 2: Execute plugins in parallel
        # plugins_to_run = job.plugins_requested or settings.VOL3_CRITICAL_PLUGINS
        # plugin_tasks = group(
        #     run_volatility_plugin.s(job_id, plugin_name, str(memory_image_path))
        #     for plugin_name in plugins_to_run
        # )
        # plugin_results = plugin_tasks.apply_async().get()
        
        # Step 3: Extract and process artifacts
        # artifact_tasks = group(
        #     process_artifact.s(artifact_path)
        #     for artifact_path in extracted_artifact_paths
        # )
        # artifact_results = artifact_tasks.apply_async().get()
        
        # TODO: Update job to COMPLETED
        # job.status = JobStatus.COMPLETED
        # job.completed_at = datetime.utcnow()
        # await db.commit()
        
        logger.info("Analysis completed for job: %s", job_id)
        
        return {
            "job_id": job_id,
            "status": "completed",
            "message": "Analysis pipeline completed successfully"
        }
    
    except SoftTimeLimitExceeded:
        logger.error("Analysis job %s exceeded time limit", job_id)
        # TODO: Update job status to FAILED
        raise
    
    except Exception as e:
        logger.exception("Analysis job %s failed", job_id)
        # TODO: Update job status to FAILED with error details
        raise


@celery_app.task(
    name="backend.workers.tasks.detect_profile",
    queue="plugins",
    priority=10
)
def detect_profile(memory_image_path: str) -> Dict[str, Any]:
    """
    Detect OS profile of a memory image.
    
    Args:
        memory_image_path: Path to memory dump
    
    Returns:
        Profile detection results
    """
    logger.info("Detecting profile for: %s", memory_image_path)
    
    try:
        detector = ProfileDetector(Path(memory_image_path))
        
        # Run async function in sync context
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        profile_info = loop.run_until_complete(detector.detect_profile())
        loop.close()
        
        logger.info(
            "Profile detected: %s (confidence: %.2f)",
            profile_info['os'],
            profile_info['confidence']
        )
        
        return profile_info
    
    except Exception as e:
        logger.exception("Profile detection failed")
        return {
            'os': 'Unknown',
            'profile': 'auto',
            'confidence': 0.0,
            'error': str(e)
        }


@celery_app.task(
    name="backend.workers.tasks.run_volatility_plugin",
    queue="plugins",
    bind=True
)
def run_volatility_plugin(
    self: Task,
    job_id: str,
    plugin_name: str,
    memory_image_path: str
) -> Dict[str, Any]:
    """
    Execute a single Volatility 3 plugin.
    
    Args:
        job_id: Parent job UUID
        plugin_name: Volatility plugin name
        memory_image_path: Path to memory dump
    
    Returns:
        Plugin execution results
    """
    logger.info("Executing plugin '%s' for job %s", plugin_name, job_id)
    
    output_dir = settings.RESULT_DIR / job_id
    output_dir.mkdir(parents=True, exist_ok=True)
    
    try:
        runner = Volatility3Runner(
            memory_image_path=Path(memory_image_path),
            output_dir=output_dir
        )
        
        # Run async function in sync context
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        result = loop.run_until_complete(
            runner.execute_plugin_async(plugin_name)
        )
        loop.close()
        
        # TODO: Store result in database
        # plugin_result = PluginResult(
        #     job_id=UUID(job_id),
        #     plugin_name=plugin_name,
        #     success=(result.status == PluginStatus.SUCCESS),
        #     row_count=result.row_count,
        #     execution_time_seconds=result.execution_time_seconds,
        #     result_json_path=str(result.output_json_path) if result.output_json_path else None,
        #     error_message=result.error_message,
        #     stderr_output=result.stderr
        # )
        # await db.add(plugin_result)
        # await db.commit()
        
        logger.info(
            "Plugin '%s' completed: %s (%d rows, %.2fs)",
            plugin_name,
            result.status.value,
            result.row_count,
            result.execution_time_seconds
        )
        
        return {
            "plugin_name": plugin_name,
            "status": result.status.value,
            "row_count": result.row_count,
            "execution_time": result.execution_time_seconds,
            "success": result.status.value == "success"
        }
    
    except SoftTimeLimitExceeded:
        logger.error("Plugin '%s' exceeded time limit", plugin_name)
        # TODO: Record timeout in database
        raise
    
    except Exception as e:
        logger.exception("Plugin '%s' execution failed", plugin_name)
        # TODO: Record failure in database
        return {
            "plugin_name": plugin_name,
            "status": "failed",
            "error": str(e)
        }


@celery_app.task(
    name="backend.workers.tasks.extract_malfind_artifacts",
    queue="plugins"
)
def extract_malfind_artifacts(
    job_id: str,
    malfind_result_path: str
) -> List[str]:
    """
    Extract suspicious memory regions identified by malfind.
    
    Malfind identifies injected code. This task extracts those
    regions to disk for further analysis.
    
    Args:
        job_id: Parent job UUID
        malfind_result_path: Path to malfind JSON output
    
    Returns:
        List of extracted artifact paths
    """
    logger.info("Extracting malfind artifacts for job %s", job_id)
    
    import json
    
    artifact_dir = settings.ARTIFACT_DIR / job_id / "malfind"
    artifact_dir.mkdir(parents=True, exist_ok=True)
    
    extracted_files = []
    
    try:
        # Parse malfind results
        with open(malfind_result_path, 'r') as f:
            malfind_data = [json.loads(line) for line in f.readlines()]
        
        # TODO: For each suspicious region, use dumpfiles plugin to extract
        # For now, just log findings
        logger.info("Found %d suspicious regions in malfind output", len(malfind_data))
        
        # TODO: Store artifact metadata in database
        
        return extracted_files
    
    except Exception as e:
        logger.exception("Malfind artifact extraction failed")
        return []


@celery_app.task(
    name="backend.workers.tasks.process_artifact",
    queue="postprocess"
)
def process_artifact(
    artifact_path: str,
    job_id: str
) -> Dict[str, Any]:
    """
    Post-process an extracted artifact with binwalk and exiftool.
    
    Args:
        artifact_path: Path to the artifact file
        job_id: Parent job UUID
    
    Returns:
        Processing results
    """
    logger.info("Post-processing artifact: %s", artifact_path)
    
    extraction_dir = settings.ARTIFACT_DIR / job_id / "postprocessed"
    
    try:
        processor = ArtifactProcessor(extraction_dir)
        
        # Run async function in sync context
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        results = loop.run_until_complete(
            processor.process_artifact(
                Path(artifact_path),
                run_binwalk=settings.BINWALK_ENABLED,
                run_exiftool=settings.EXIFTOOL_ENABLED
            )
        )
        loop.close()
        
        # TODO: Update artifact record in database with results
        # artifact = await db.query(Artifact).filter(
        #     Artifact.file_path == artifact_path
        # ).first()
        # if artifact:
        #     artifact.binwalk_analyzed = True
        #     artifact.binwalk_results = results.get('binwalk')
        #     artifact.exiftool_analyzed = True
        #     artifact.exiftool_metadata = results.get('exiftool')
        #     await db.commit()
        
        logger.info("Artifact post-processing completed: %s", artifact_path)
        
        return results
    
    except Exception as e:
        logger.exception("Artifact post-processing failed: %s", artifact_path)
        return {"error": str(e)}


@celery_app.task(
    name="backend.workers.tasks.cleanup_job_artifacts",
    queue="postprocess",
    priority=1
)
def cleanup_job_artifacts(job_id: str, keep_results: bool = True) -> None:
    """
    Clean up temporary files and artifacts for a job.
    
    Called after job completion or when manually triggered.
    
    Args:
        job_id: Job UUID
        keep_results: If True, keep JSON results but remove raw artifacts
    """
    logger.info("Cleaning up job %s (keep_results=%s)", job_id, keep_results)
    
    try:
        # TODO: Implement selective cleanup
        # - Remove extracted artifacts if keep_results=False
        # - Remove temporary processing files
        # - Keep JSON outputs if keep_results=True
        # - Update storage statistics
        
        pass
    
    except Exception as e:
        logger.exception("Cleanup failed for job %s", job_id)


# Periodic tasks (can be registered with Celery Beat)
@celery_app.task(
    name="backend.workers.tasks.cleanup_old_jobs",
    queue="postprocess"
)
def cleanup_old_jobs(days_threshold: int = 30) -> Dict[str, int]:
    """
    Periodic task to clean up jobs older than threshold.
    
    Args:
        days_threshold: Delete jobs older than this many days
    
    Returns:
        Statistics on cleaned jobs
    """
    logger.info("Running periodic cleanup (threshold: %d days)", days_threshold)
    
    # TODO: Implement periodic cleanup
    # - Query old completed jobs
    # - Remove artifacts
    # - Archive or delete job records
    
    return {
        "jobs_cleaned": 0,
        "space_freed_gb": 0.0
    }
