from fastapi import APIRouter, Depends, status
from typing import List, Dict
from sqlalchemy.orm import Session

from ..database import get_db
from ..schemas.schemas import SettingCreate, SettingResponse, SettingBatchUpdate
from ..services.setting_service import (
    create_setting, 
    get_settings, 
    delete_setting,
    batch_update_settings
)

router = APIRouter(
    tags=["settings"],
    responses={404: {"description": "Not found"}},
)


@router.get("/settings", response_model=List[SettingResponse])
def read_settings(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    """Get all settings with pagination"""
    settings = get_settings(db, skip=skip, limit=limit)
    return settings


@router.post("/settings", response_model=SettingResponse, status_code=status.HTTP_201_CREATED)
def create_new_setting(setting: SettingCreate, db: Session = Depends(get_db)):
    """Create a new setting"""
    return create_setting(db, setting)


@router.put("/settings/batch", response_model=List[SettingResponse])
def update_settings_batch(settings_batch: SettingBatchUpdate, db: Session = Depends(get_db)):
    """Update multiple settings in a single request
    
    Each setting in the list must have at least a key and value.
    Other fields (title, section, description, type, options) are optional.
    """
    # Convert the Pydantic models to dictionaries for the service function
    settings_data = [setting.dict(exclude_unset=True) for setting in settings_batch.settings]
    return batch_update_settings(db, settings_data)


@router.delete("/settings/{setting_id}", response_model=SettingResponse)
def delete_existing_setting(setting_id: int, db: Session = Depends(get_db)):
    """Delete a setting by ID"""
    return delete_setting(db, setting_id)
