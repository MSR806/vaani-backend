"""
Test tasks for background job system.

Simple tasks for testing the background job functionality.
"""

import logging
import time
from datetime import datetime
from typing import Dict, Any
from app.repository.base_repository import BaseRepository
from app.repository.template_repository import TemplateRepository
from app.services.background_jobs import enqueue_job
from app.services.template_generator.template_manager import TemplateManager
from database import get_db

# Configure logging
logger = logging.getLogger(__name__)

async def create_template_task(book_id: int, template_id: int):
    db = next(get_db())
    manager = TemplateManager(book_id, db)
    await manager.run(template_id)

def add_template_creation_task_to_bg_jobs(book_id: int, template_id: int):
    enqueue_job(create_template_task, book_id=book_id, template_id=template_id)