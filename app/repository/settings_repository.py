from .base_repository import BaseRepository
from app.models.models import Setting
from app.database import get_db
from sqlalchemy.orm import Session

class SettingsRepository(BaseRepository[Setting]):
    def __init__(self, db: Session):
        super().__init__(db)

    def get_by_key(self, key: str) -> Setting:
        setting = self.db.query(Setting).filter(Setting.key == key).first()
        if not setting:
            raise ValueError(f"Setting with key {key} not found")
        return setting
settings_repo = SettingsRepository(get_db())
