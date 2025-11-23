"""
Background job processing for async tasks
Uses Celery for distributed task processing with Redis/RabbitMQ
"""
import asyncio
import logging
from typing import Dict, Any, Optional, Callable
from datetime import datetime
from enum import Enum

logger = logging.getLogger(__name__)

# Try to import Celery
try:
    from celery import Celery
    from celery.result import AsyncResult
    CELERY_AVAILABLE = True
except ImportError:
    CELERY_AVAILABLE = False
    logger.warning("Celery not available. Background jobs will run in-process.")

from config import get_settings

settings = get_settings()


class JobStatus(Enum):
    """Job status enumeration"""
    PENDING = "pending"
    STARTED = "started"
    SUCCESS = "success"
    FAILURE = "failure"
    RETRY = "retry"
    REVOKED = "revoked"


class InProcessJobQueue:
    """Simple in-process job queue (fallback when Celery is not available)"""
    
    def __init__(self):
        self.jobs: Dict[str, Dict[str, Any]] = {}
        self._running = False
        self._task: Optional[asyncio.Task] = None
    
    async def start(self):
        """Start the job processor"""
        if self._running:
            return
        
        self._running = True
        self._task = asyncio.create_task(self._process_jobs())
        logger.info("In-process job queue started")
    
    async def stop(self):
        """Stop the job processor"""
        self._running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        logger.info("In-process job queue stopped")
    
    async def _process_jobs(self):
        """Process jobs in the queue"""
        while self._running:
            try:
                # Process pending jobs
                pending_jobs = [
                    (job_id, job) for job_id, job in self.jobs.items()
                    if job.get("status") == JobStatus.PENDING.value
                ]
                
                for job_id, job in pending_jobs:
                    try:
                        self.jobs[job_id]["status"] = JobStatus.STARTED.value
                        self.jobs[job_id]["started_at"] = datetime.utcnow().isoformat()
                        
                        # Execute job
                        if asyncio.iscoroutinefunction(job["func"]):
                            result = await job["func"](*job.get("args", []), **job.get("kwargs", {}))
                        else:
                            result = job["func"](*job.get("args", []), **job.get("kwargs", {}))
                        
                        self.jobs[job_id]["status"] = JobStatus.SUCCESS.value
                        self.jobs[job_id]["result"] = result
                        self.jobs[job_id]["completed_at"] = datetime.utcnow().isoformat()
                        
                    except Exception as e:
                        self.jobs[job_id]["status"] = JobStatus.FAILURE.value
                        self.jobs[job_id]["error"] = str(e)
                        self.jobs[job_id]["completed_at"] = datetime.utcnow().isoformat()
                        logger.error(f"Job {job_id} failed: {str(e)}")
                
                await asyncio.sleep(1)  # Check every second
            
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in job processor: {str(e)}")
                await asyncio.sleep(5)
    
    def enqueue(self, func: Callable, *args, job_id: Optional[str] = None, **kwargs) -> str:
        """Enqueue a job"""
        import uuid
        job_id = job_id or str(uuid.uuid4())
        
        self.jobs[job_id] = {
            "func": func,
            "args": args,
            "kwargs": kwargs,
            "status": JobStatus.PENDING.value,
            "created_at": datetime.utcnow().isoformat(),
        }
        
        logger.info(f"Job {job_id} enqueued")
        return job_id
    
    def get_status(self, job_id: str) -> Optional[Dict[str, Any]]:
        """Get job status"""
        return self.jobs.get(job_id)
    
    def get_result(self, job_id: str) -> Optional[Any]:
        """Get job result"""
        job = self.jobs.get(job_id)
        if job and job.get("status") == JobStatus.SUCCESS.value:
            return job.get("result")
        return None


# Initialize Celery app if available
celery_app: Optional[Celery] = None
in_process_queue: Optional[InProcessJobQueue] = None


def init_celery(broker_url: str = None, result_backend: str = None) -> bool:
    """
    Initialize Celery for background job processing
    
    Args:
        broker_url: Redis/RabbitMQ broker URL
        result_backend: Result backend URL
    
    Returns:
        True if Celery was initialized, False otherwise
    """
    global celery_app
    
    if not CELERY_AVAILABLE:
        logger.warning("Celery not available. Using in-process job queue.")
        return False
    
    try:
        broker_url = broker_url or getattr(settings, 'CELERY_BROKER_URL', 'redis://localhost:6379/0')
        result_backend = result_backend or getattr(settings, 'CELERY_RESULT_BACKEND', 'redis://localhost:6379/0')
        
        celery_app = Celery(
            'accessibility_analyzer',
            broker=broker_url,
            backend=result_backend
        )
        
        # Celery configuration
        celery_app.conf.update(
            task_serializer='json',
            accept_content=['json'],
            result_serializer='json',
            timezone='UTC',
            enable_utc=True,
            task_track_started=True,
            task_time_limit=30 * 60,  # 30 minutes
            task_soft_time_limit=25 * 60,  # 25 minutes
            worker_prefetch_multiplier=1,
            worker_max_tasks_per_child=1000,
        )
        
        logger.info("Celery initialized successfully")
        return True
    
    except Exception as e:
        logger.error(f"Failed to initialize Celery: {str(e)}")
        return False


def get_job_queue():
    """Get the appropriate job queue (Celery or in-process)"""
    global in_process_queue
    
    if celery_app:
        return celery_app
    
    if in_process_queue is None:
        in_process_queue = InProcessJobQueue()
        # Start it in the background
        asyncio.create_task(in_process_queue.start())
    
    return in_process_queue


# Task decorators
def task(name: str = None, **kwargs):
    """
    Decorator to create a background task
    
    Usage:
        @task(name='analyze_accessibility')
        def analyze_file(file_path: str):
            # Do work
            return result
    """
    if celery_app:
        return celery_app.task(name=name, **kwargs)
    else:
        # For in-process queue, just return the function as-is
        def decorator(func):
            return func
        return decorator


async def enqueue_job(func: Callable, *args, job_id: Optional[str] = None, **kwargs) -> str:
    """
    Enqueue a job for background processing
    
    Args:
        func: Function to execute
        *args: Positional arguments
        job_id: Optional job ID
        **kwargs: Keyword arguments
    
    Returns:
        Job ID
    """
    queue = get_job_queue()
    
    if celery_app:
        # Use Celery
        celery_task = task()(func)
        result = celery_task.delay(*args, **kwargs)
        return result.id
    else:
        # Use in-process queue
        return in_process_queue.enqueue(func, *args, job_id=job_id, **kwargs)


async def get_job_status(job_id: str) -> Optional[Dict[str, Any]]:
    """
    Get status of a background job
    
    Args:
        job_id: Job ID
    
    Returns:
        Job status dictionary or None if not found
    """
    queue = get_job_queue()
    
    if celery_app:
        result = AsyncResult(job_id, app=celery_app)
        return {
            "id": job_id,
            "status": result.status.lower(),
            "result": result.result if result.ready() and result.successful() else None,
            "error": str(result.result) if result.ready() and result.failed() else None,
        }
    else:
        return in_process_queue.get_status(job_id)


async def get_job_result(job_id: str) -> Optional[Any]:
    """
    Get result of a completed job
    
    Args:
        job_id: Job ID
    
    Returns:
        Job result or None if not ready
    """
    queue = get_job_queue()
    
    if celery_app:
        result = AsyncResult(job_id, app=celery_app)
        if result.ready() and result.successful():
            return result.result
        return None
    else:
        return in_process_queue.get_result(job_id)


# Example background tasks
@task(name='analyze_accessibility_async')
def analyze_accessibility_async(session_id: str, file_path: str, model: str):
    """Example: Analyze accessibility in background"""
    # This would call the actual analysis logic
    # For now, it's a placeholder
    logger.info(f"Background analysis started for session {session_id}")
    return {"status": "completed", "session_id": session_id}

