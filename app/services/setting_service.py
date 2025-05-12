from sqlalchemy.orm import Session
from fastapi import HTTPException

from ..models.models import Setting


def get_setting_by_key(db: Session, key: str):
    """Get a setting by its key"""
    setting = db.query(Setting).filter(Setting.key == key).first()
    if not setting:
        raise HTTPException(status_code=404, detail=f"Setting with key '{key}' not found")
    return setting

def get_settings(db: Session, skip: int = 0, limit: int = 100):
    """Get all settings with pagination"""
    return db.query(Setting).offset(skip).limit(limit).all()