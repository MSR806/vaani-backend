from sqlalchemy.orm import Session
from fastapi import HTTPException

from ..models.models import Setting


def get_setting_by_key(db: Session, key: str):
    """Get a setting by its key"""
    setting = db.query(Setting).filter(Setting.key == key).first()
    if not setting:
        raise HTTPException(status_code=404, detail=f"Setting with key '{key}' not found")
    return setting