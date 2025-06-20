import logging
import os
from typing import Any, Callable, Dict, Optional

from redis import Redis
from rq import Queue

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


def enqueue_job(
    func: Callable,
    *args: Any,
    priority: str = "default",
    job_timeout: int = 3600,
    result_ttl: int = 86400,
    **kwargs: Any,
):
    logger.info(f"Enqueueing job: {func.__name__} with priority {priority}")

    if priority == "high":
        return high_queue.enqueue(
            func, *args, job_timeout=job_timeout, result_ttl=result_ttl, **kwargs
        )
    elif priority == "low":
        return low_queue.enqueue(
            func, *args, job_timeout=job_timeout, result_ttl=result_ttl, **kwargs
        )
    else:
        return default_queue.enqueue(
            func, *args, job_timeout=job_timeout, result_ttl=result_ttl, **kwargs
        )


def get_job(job_id: str):
    from rq.job import Job

    try:
        return Job.fetch(job_id, connection=redis_conn)
    except Exception as e:
        logger.error(f"Error fetching job {job_id}: {str(e)}")
        return None


def get_job_status(job_id: str) -> Optional[Dict[str, Any]]:
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
    job = get_job(job_id)
    if not job:
        return False

    if job.get_status() == "queued":
        job.cancel()
        return True

    return False


def get_queue_length(queue_name: str = "default") -> int:
    if queue_name == "high":
        return len(high_queue)
    elif queue_name == "low":
        return len(low_queue)
    else:
        return len(default_queue)
