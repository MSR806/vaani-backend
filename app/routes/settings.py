from fastapi import APIRouter, Depends
from typing import List
from sqlalchemy.orm import Session

from ..database import get_db
from ..schemas.schemas import SettingResponse, SettingBatchUpdate
from ..services.setting_service import (
    get_settings,
    batch_update_settings,
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


@router.put("/settings/batch", response_model=List[SettingResponse])
def update_settings_batch(settings_batch: SettingBatchUpdate, db: Session = Depends(get_db)):
    """Update multiple settings in a single request

    Each setting in the list must have at least a key and value.
    Other fields (title, section, description, type, options) are optional.
    """
    # Convert the Pydantic models to dictionaries for the service function
    settings_data = [setting.dict(exclude_unset=True) for setting in settings_batch.settings]
    return batch_update_settings(db, settings_data)
