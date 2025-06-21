from typing import List

from fastapi import Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.metrics.router import MetricsRouter
from app.schemas.schemas import SettingBatchUpdate, SettingResponse
from app.services.setting_service import batch_update_settings, get_settings

router = MetricsRouter(tags=["settings"])


@router.get("/settings", response_model=List[SettingResponse])
def read_settings(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    settings = get_settings(db, skip=skip, limit=limit)
    return settings


@router.put("/settings/batch", response_model=List[SettingResponse])
def update_settings_batch(settings_batch: SettingBatchUpdate, db: Session = Depends(get_db)):
    # Convert the Pydantic models to dictionaries for the service function
    settings_data = [setting.dict(exclude_unset=True) for setting in settings_batch.settings]
    return batch_update_settings(db, settings_data)
