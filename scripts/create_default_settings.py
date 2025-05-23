#!/usr/bin/env python3
"""
Initialize default settings in Supabase database.
This script creates the initial AI model settings needed by the application.
"""

import sys
import os
import time
import json

from app.utils.constants import SettingKeys

# Add the parent directory to sys.path to import app modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.database import SessionLocal
from app.models.models import Setting
from sqlalchemy.exc import IntegrityError

def create_default_settings():
    """Create default settings for the application."""
    db = SessionLocal()
    
    # Define default settings
    model_options = json.dumps(["gpt-4o-mini", "grok-3-latest", "gpt-4o", "o3"])
    settings = [
        # AI Model settings for chapter outline generation
        {
            "key": "create_scenes_ai_model",
            "title": "Scene Creation AI Model",
            "section": "Scene",
            "value": "gpt-4o-mini",
            "description": "AI model used for generating chapter outlines with scenes",
            "type": "list",
            "options": model_options
        },
        {
            "key": "create_scenes_temperature",
            "title": "Scene Creation Temperature",
            "section": "Scene",
            "value": "0.7",
            "description": "Temperature parameter for scene generation",
            "type": "string",
            "options": None
        },
        
        # AI Model settings for chapter content generation
        {
            "key": "create_chapter_content_ai_model",
            "title": "Chapter Content AI Model",
            "section": "Chapter",
            "value": "gpt-4o-mini",
            "description": "AI model used for generating chapter content",
            "type": "list",
            "options": model_options
        },
        {
            "key": "create_chapter_content_temperature",
            "title": "Chapter Content Temperature",
            "section": "Chapter",
            "value": "0.8",
            "description": "Temperature parameter for chapter content generation",
            "type": "string",
            "options": None
        },
        
        # AI Model settings for chapter editing
        {
            "key": "chapter_select_and_replace_ai_model",
            "title": "Chapter Edit AI Model",
            "section": "Chapter",
            "value": "gpt-4o-mini",
            "description": "AI model used for chapter editing",
            "type": "list",
            "options": model_options
        },
        {
            "key": "chapter_select_and_replace_temperature",
            "title": "Chapter Edit Temperature",
            "section": "Chapter",
            "value": "0.7",
            "description": "Temperature parameter for chapter editing",
            "type": "string",
            "options": None
        },
        {
            "key": SettingKeys.CHARACTER_ARC_GENERATION_MODEL.value,
            "title": "Character Arc Generation AI Model",
            "section": "Storyboard",
            "value": "gpt-4o",
            "description": "AI model used for generating character arcs",
            "type": "list",
            "options": model_options
        },
        {
            "key": SettingKeys.CHARACTER_ARC_GENERATION_TEMPERATURE.value,
            "title": "Character Arc Generation Temperature",
            "section": "Storyboard",
            "value": "0.7",
            "description": "Temperature parameter for character arc generation",
            "type": "string",
            "options": None
        },
        {
            "key": SettingKeys.PLOT_BEAT_GENERATION_MODEL.value,
            "title": "Plot Beat Generation AI Model",
            "section": "Storyboard",
            "value": "gpt-4o",
            "description": "AI model used for generating plot beats",
            "type": "list",
            "options": model_options
        },
        {
            "key": SettingKeys.PLOT_BEAT_GENERATION_TEMPERATURE.value,
            "title": "Plot Beat Generation Temperature",
            "section": "Storyboard",
            "value": "0.7",
            "description": "Temperature parameter for plot beat generation",
            "type": "string",
            "options": None
        },
        {
            "key": SettingKeys.PLOT_SUMMARY_GENERATION_MODEL.value,
            "title": "Plot Summary Generation AI Model",
            "section": "Storyboard",
            "value": "gpt-4o-mini",
            "description": "AI model used for generating plot summaries",
            "type": "list",
            "options": model_options
        },
        {
            "key": SettingKeys.PLOT_SUMMARY_GENERATION_TEMPERATURE.value,
            "title": "Plot Summary Generation Temperature",
            "section": "Storyboard",
            "value": "0.4",
            "description": "Temperature parameter for plot summary generation",
            "type": "string",
            "options": None
        },
        
        # Chapter summary generation settings
        {
            "key": SettingKeys.CHAPTER_SUMMARY_GENERATION_FROM_STORYBOARD_MODEL.value,
            "title": "Chapter Summary Generation from Storyboard AI Model",
            "section": "Storyboard",
            "value": "gpt-4o",
            "description": "AI model used for generating chapter summaries from storyboard",
            "type": "list",
            "options": model_options
        },
        {
            "key": SettingKeys.CHAPTER_SUMMARY_GENERATION_FROM_STORYBOARD_TEMPERATURE.value,
            "title": "Chapter Summary Generation from Storyboard Temperature",
            "section": "Storyboard",
            "value": "0.6",
            "description": "Temperature parameter for chapter summary generation from storyboard",
            "type": "string",
            "options": None
        },
        
        # Settings for extraction and abstraction/templating
        {
            "key": SettingKeys.EXTRACTING_CHARACTER_ARCS_MODEL.value,
            "title": "Character Arc Extraction AI Model",
            "section": "Templates",
            "value": "gpt-4o",
            "description": "AI model used for extracting character arcs from text",
            "type": "list",
            "options": model_options
        },
        {
            "key": SettingKeys.EXTRACTING_CHARACTER_ARCS_TEMPERATURE.value,
            "title": "Character Arc Extraction Temperature",
            "section": "Templates",
            "value": "0.3",
            "description": "Temperature parameter for character arc extraction",
            "type": "string",
            "options": None
        },
        {
            "key": SettingKeys.EXTRACTING_PLOT_BEATS_MODEL.value,
            "title": "Plot Beat Extraction AI Model",
            "section": "Templates",
            "value": "gpt-4o",
            "description": "AI model used for extracting plot beats from text",
            "type": "list",
            "options": model_options
        },
        {
            "key": SettingKeys.EXTRACTING_PLOT_BEATS_TEMPERATURE.value,
            "title": "Plot Beat Extraction Temperature",
            "section": "Templates",
            "value": "0.3",
            "description": "Temperature parameter for plot beat extraction",
            "type": "string",
            "options": None
        },
        {
            "key": SettingKeys.CHAPTER_SUMMARY_GENERATION_FOR_TEMPLATE_MODEL.value,
            "title": "Chapter Summary Generation for Template AI Model",
            "section": "Templates",
            "value": "gpt-4o-mini",
            "description": "AI model used for generating chapter summaries for templates",
            "type": "list",
            "options": model_options
        },
        {
            "key": SettingKeys.CHAPTER_SUMMARY_GENERATION_FOR_TEMPLATE_TEMPERATURE.value,
            "title": "Chapter Summary Generation for Template Temperature",
            "section": "Templates",
            "value": "0.3",
            "description": "Temperature parameter for chapter summary generation for templates",
            "type": "string",
            "options": None
        },
        {
            "key": SettingKeys.CHARACTER_ARC_TEMPLATE_MODEL.value,
            "title": "Character Arc Template AI Model",
            "section": "Templates",
            "value": "gpt-4o",
            "description": "AI model used for creating character arc templates",
            "type": "list",
            "options": model_options
        },
        {
            "key": SettingKeys.CHARACTER_ARC_TEMPLATE_TEMPERATURE.value,
            "title": "Character Arc Template Temperature",
            "section": "Templates",
            "value": "0.3",
            "description": "Temperature parameter for character arc template creation",
            "type": "string",
            "options": None
        },
        {
            "key": SettingKeys.PLOT_BEATS_TEMPLATE_MODEL.value,
            "title": "Plot Beat Template AI Model",
            "section": "Templates",
            "value": "gpt-4o",
            "description": "AI model used for creating plot beat templates",
            "type": "list",
            "options": model_options
        },
        {
            "key": SettingKeys.PLOT_BEATS_TEMPLATE_TEMPERATURE.value,
            "title": "Plot Beat Template Temperature",
            "section": "Templates",
            "value": "0.3",
            "description": "Temperature parameter for plot beat template creation",
            "type": "string",
            "options": None
        },
        # Character identification settings
        {
            "key": SettingKeys.CHARACTER_IDENTIFICATION_MODEL.value,
            "title": "Character Identification AI Model",
            "section": "Storyboard",
            "value": "o3",
            "description": "AI model used for identifying characters in plot beats",
            "type": "list",
            "options": model_options
        },
        {
            "key": SettingKeys.CHARACTER_IDENTIFICATION_TEMPERATURE.value,
            "title": "Character Identification Temperature",
            "section": "Storyboard",
            "value": "1",
            "description": "Temperature parameter for character identification in plot beats",
            "type": "string",
            "options": None
        }
    ]

    
    # Current timestamp
    current_time = int(time.time())
    
    # Insert settings
    created_count = 0
    for setting_data in settings:
        try:
            # Check if setting already exists
            existing = db.query(Setting).filter(Setting.key == setting_data["key"]).first()
            
            if not existing:
                # Create setting object with base data only
                setting = Setting(**setting_data)
                
                # Set audit fields separately after instantiation
                setting.created_at = current_time
                setting.updated_at = current_time
                setting.created_by = "system"
                setting.updated_by = "system"
                
                db.add(setting)
                db.commit()
                created_count += 1
                print(f"Created setting: {setting.key}")
            else:
                # Check if any fields other than 'value' have changed
                fields_to_check = ['title', 'section', 'description', 'type', 'options']
                changes_made = False
                
                for field in fields_to_check:
                    if field in setting_data and getattr(existing, field) != setting_data[field]:
                        setattr(existing, field, setting_data[field])
                        changes_made = True
                
                if changes_made:
                    # Update metadata but preserve the existing value
                    existing.updated_at = current_time
                    existing.updated_by = "system"
                    db.commit()
                    print(f"Updated metadata for setting: {setting_data['key']}")
                else:
                    print(f"Setting already exists (no changes needed): {setting_data['key']}")
        
        except IntegrityError as e:
            db.rollback()
            print(f"Error creating setting: {setting_data['key']} - {e}")
        except Exception as e:
            db.rollback()
            print(f"Unexpected error: {e}")
    
    print(f"Created {created_count} settings")
    db.close()

if __name__ == "__main__":
    create_default_settings()
