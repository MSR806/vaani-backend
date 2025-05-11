"""
Background Job Service

This module provides functions to enqueue and manage background jobs using Redis Queue (RQ).
Services can directly use these functions to create background jobs without going through APIs.
"""

import logging
import os
from rq import Queue
from redis import Redis
from typing import Any, Dict, Optional, List, Callable

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Get Redis URL from environment variable or use default
redis_url = os.getenv("REDIS_URL", "redis://redis:6379/0")

# Connect to Redis
redis_conn = Redis.from_url(redis_url)

# Create queues with different priorities
high_queue = Queue("high", connection=redis_conn)
default_queue = Queue("default", connection=redis_conn)
low_queue = Queue("low", connection=redis_conn)

def enqueue_job(func: Callable, *args: Any, priority: str = "default", 
                job_timeout: int = 3600, result_ttl: int = 86400, **kwargs: Any):
    """
    Enqueue a background job with specified priority
    
    Args:
        func: The function to run in the background
        *args: Arguments to pass to the function
        priority: Priority level ("high", "default", or "low")
        job_timeout: Maximum runtime allowed for the job in seconds
        result_ttl: How long to keep the job result in Redis (seconds)
        **kwargs: Keyword arguments to pass to the function
    
    Returns:
        The job object
    """
    logger.info(f"Enqueueing job: {func.__name__} with priority {priority}")
    
    if priority == "high":
        return high_queue.enqueue(func, *args, job_timeout=job_timeout, 
                                result_ttl=result_ttl, **kwargs)
    elif priority == "low":
        return low_queue.enqueue(func, *args, job_timeout=job_timeout, 
                               result_ttl=result_ttl, **kwargs)
    else:
        return default_queue.enqueue(func, *args, job_timeout=job_timeout, 
                                  result_ttl=result_ttl, **kwargs)

def get_job(job_id: str):
    """
    Get a job by its ID
    
    Args:
        job_id: The job ID
        
    Returns:
        The job object or None if not found
    """
    from rq.job import Job
    try:
        return Job.fetch(job_id, connection=redis_conn)
    except Exception as e:
        logger.error(f"Error fetching job {job_id}: {str(e)}")
        return None

def get_job_status(job_id: str) -> Optional[Dict[str, Any]]:
    """
    Get the status of a job
    
    Args:
        job_id: ID of the job
        
    Returns:
        Job status information dictionary or None if job not found
    """
    job = get_job(job_id)
    if not job:
        return None
        
    result = {
        "job_id": job_id,
        "status": job.get_status(),
        "queue": job.origin,
        "created_at": job.created_at.isoformat() if job.created_at else None,
        "ended_at": job.ended_at.isoformat() if job.ended_at else None,
    }
    
    if job.get_status() == "finished" and job.result:
        result["result"] = job.result
    elif job.get_status() == "failed" and job.exc_info:
        result["error"] = job.exc_info
        
    return result

def cancel_job(job_id: str) -> bool:
    """
    Cancel a job by its ID if it hasn't started yet
    
    Args:
        job_id: The job ID
        
    Returns:
        True if job was cancelled, False otherwise
    """
    job = get_job(job_id)
    if not job:
        return False
    
    if job.get_status() == "queued":
        job.cancel()
        return True
    
    return False

def get_queue_length(queue_name: str = "default") -> int:
    """
    Get the number of jobs in a queue
    
    Args:
        queue_name: Name of the queue ("high", "default", "low")
        
    Returns:
        Number of jobs in the queue
    """
    if queue_name == "high":
        return len(high_queue)
    elif queue_name == "low":
        return len(low_queue)
    else:
        return len(default_queue)
