"""
Test tasks for background job system.

Simple tasks for testing the background job functionality.
"""

import logging
import time
from datetime import datetime
from typing import Dict, Any
from app.services.background_jobs import enqueue_job

# Configure logging
logger = logging.getLogger(__name__)

def simple_test_task(name: str, sleep_time: int = 5) -> Dict[str, Any]:
    """
    A simple test task that simulates work by sleeping
    
    Args:
        name: A name for this task run
        sleep_time: How long to sleep in seconds
        
    Returns:
        A dictionary with the results
    """
    start_time = datetime.now()
    logger.info(f"Starting test task '{name}' at {start_time}")
    
    # Simulate work
    for i in range(sleep_time):
        logger.info(f"Working on '{name}': step {i+1}/{sleep_time}")
        time.sleep(1)
    
    end_time = datetime.now()
    duration = (end_time - start_time).total_seconds()
    
    logger.info(f"Completed test task '{name}' in {duration:.2f} seconds")
    
    return {
        "task_name": name,
        "status": "completed",
        "start_time": start_time.isoformat(),
        "end_time": end_time.isoformat(),
        "duration_seconds": duration,
        "sleep_time": sleep_time
    }

def add_task_to_bg_jobs():
    enqueue_job(simple_test_task, "test_task", sleep_time=5)