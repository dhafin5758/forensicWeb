"""
Celery Application Configuration
Distributed task queue for long-running forensic analysis jobs.
"""

from celery import Celery
from kombu import Queue, Exchange

from backend.config import settings


# Create Celery app
celery_app = Celery(
    "forensics_worker",
    broker=settings.CELERY_BROKER_URL,
    backend=settings.CELERY_RESULT_BACKEND,
)


# Celery configuration
celery_app.conf.update(
    # Task routing
    task_routes={
        "backend.workers.tasks.analyze_memory_image": {"queue": "analysis"},
        "backend.workers.tasks.run_volatility_plugin": {"queue": "plugins"},
        "backend.workers.tasks.process_artifact": {"queue": "postprocess"},
    },
    
    # Task serialization
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    
    # Task execution
    task_time_limit=settings.CELERY_TASK_TIMEOUT,
    task_soft_time_limit=settings.CELERY_TASK_TIMEOUT - 300,  # 5 min before hard limit
    task_acks_late=True,  # Acknowledge after completion
    task_reject_on_worker_lost=True,
    
    # Result backend
    result_expires=86400,  # 24 hours
    result_extended=True,
    
    # Worker configuration
    worker_prefetch_multiplier=1,  # Fetch one task at a time (memory-intensive tasks)
    worker_max_tasks_per_child=10,  # Restart worker after N tasks (memory cleanup)
    worker_send_task_events=True,
    
    # Monitoring
    task_send_sent_event=True,
    task_track_started=True,
    
    # Timezone
    timezone="UTC",
    enable_utc=True,
)


# Define task queues with priorities
celery_app.conf.task_queues = (
    Queue("analysis", Exchange("analysis"), routing_key="analysis", priority=10),
    Queue("plugins", Exchange("plugins"), routing_key="plugins", priority=5),
    Queue("postprocess", Exchange("postprocess"), routing_key="postprocess", priority=3),
)


# Auto-discover tasks from workers module
celery_app.autodiscover_tasks(["backend.workers"])


# Task base class for custom behavior
class ForensicsTask(celery_app.Task):
    """
    Custom base task class with forensics-specific features.
    """
    
    def on_failure(self, exc, task_id, args, kwargs, einfo):
        """
        Handle task failure.
        
        - Log error details
        - Update job status in database
        - Send notification (if configured)
        """
        # TODO: Update job status to FAILED
        # TODO: Store error message and traceback
        # TODO: Send admin notification for critical failures
        pass
    
    def on_success(self, retval, task_id, args, kwargs):
        """
        Handle task success.
        
        - Update job status
        - Trigger dependent tasks
        """
        # TODO: Update job status to COMPLETED
        pass
    
    def on_retry(self, exc, task_id, args, kwargs, einfo):
        """
        Handle task retry.
        
        - Log retry attempt
        - Update job status
        """
        # TODO: Log retry information
        pass


# Set default task base class
celery_app.Task = ForensicsTask
