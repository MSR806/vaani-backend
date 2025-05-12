from fastapi import APIRouter, Depends
from typing import List
from sqlalchemy.orm import Session

from ..database import get_db
from ..schemas.schemas import SettingResponse
from ..services.setting_service import (
    get_settings,
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
