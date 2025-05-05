#!/usr/bin/env python3
"""
Script to create default settings in the database.
Run this script to initialize or reset application settings.
"""

import sys
import os
import json
from pathlib import Path

# Add the parent directory to the path so we can import from the app
script_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(script_dir)
sys.path.insert(0, project_root)

from sqlalchemy.orm import Session
from app.database import SessionLocal, engine
from app.models.models import Base, Setting
from app.services.setting_service import create_setting
from app.schemas.schemas import SettingCreate

# Create tables if they don't exist
Base.metadata.create_all(bind=engine)

# Default settings with their descriptions
DEFAULT_SETTINGS = [
    {
        "key": "create_scenes_ai_model",
        "title": "Create Scenes AI Model",
        "section": "Scene",
        "value": "gpt-4o-mini",
        "description": "AI model to use for creating scenes",
        "type": "list",
        "options": json.dumps(["gpt-4o-mini", "grok-3-latest"])
    },
    {
        "key": "create_scenes_temperature",
        "title": "Create Scenes Temperature",
        "section": "Scene",
        "value": "0.7",
        "description": "Controls randomness of AI responses (0.0-1.0)",
        "type": "string",
        "options": None
    },
    {
        "key": "create_chapter_content_ai_model",
        "title": "Create Chapter Content AI Model",
        "section": "Chapter",
        "value": "gpt-4o-mini",
        "description": "AI model to use for creating chapter content",
        "type": "list",
        "options": json.dumps(["gpt-4o-mini", "grok-3-latest"])
    },
    {
        "key": "create_chapter_content_temperature",
        "title": "Create Chapter Content Temperature",
        "section": "Chapter",
        "value": "0.7",
        "description": "Controls randomness of AI responses (0.0-1.0)",
        "type": "string",
        "options": None
    },
    {
        "key": "chapter_select_and_replace_ai_model",
        "title": "Chapter Select and Replace AI Model",
        "section": "Chapter",
        "value": "gpt-4o-mini",
        "description": "AI model to use for chapter select and replace",
        "type": "list",
        "options": json.dumps(["gpt-4o-mini", "grok-3-latest"])
    },
    {
        "key": "chapter_select_and_replace_temperature",
        "title": "Chapter Select and Replace Temperature",
        "section": "Chapter",
        "value": "0.7",
        "description": "Controls randomness of AI responses (0.0-1.0)",
        "type": "string",
        "options": None
    }
]


def create_default_settings():
    """Create default settings in the database."""
    db = SessionLocal()
    try:
        # Check if settings already exist
        existing_settings = db.query(Setting).all()
        existing_keys = {setting.key for setting in existing_settings}
        
        # Create settings that don't exist
        created_count = 0
        for setting_data in DEFAULT_SETTINGS:
            if setting_data["key"] not in existing_keys:
                setting = SettingCreate(**setting_data)
                create_setting(db, setting)
                created_count += 1
                print(f"Created setting: {setting_data['key']}")
            else:
                print(f"Setting already exists: {setting_data['key']}")
        
        print(f"\nCreated {created_count} new settings")
    except Exception as e:
        print(f"Error creating settings: {e}")
    finally:
        db.close()


if __name__ == "__main__":
    create_default_settings()
