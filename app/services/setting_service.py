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

def get_setting_by_id(db: Session, setting_id: int):
    """Get a setting by its ID"""
    setting = db.query(Setting).filter(Setting.id == setting_id).first()
    if not setting:
        raise HTTPException(status_code=404, detail="Setting not found")
    return setting

def batch_update_settings(db: Session, settings_data: list):
    """Update multiple settings in a batch operation"""
    updated_settings = []
    
    # Start a transaction to ensure atomicity
    try:
        for setting_data in settings_data:
            # Each setting update needs an id to identify the setting
            if "id" not in setting_data:
                raise HTTPException(status_code=400, detail="Each setting must have an id")
            
            # Find the setting by id
            setting_id = setting_data["id"]
            db_setting = get_setting_by_id(db, setting_id)
            
            # Update the value
            if "value" in setting_data:
                db_setting.value = setting_data["value"]
            
            updated_settings.append(db_setting)
        
        db.commit()
        return updated_settings
    except Exception as e:
        db.rollback()
        raise e