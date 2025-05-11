from .base_repository import BaseRepository
from app.models.models import Setting
from app.database import get_db


class SettingsRepository(BaseRepository[Setting]):
    def get_by_key(self, key: str) -> Setting:
        setting = self.db.query(Setting).filter(Setting.key == key).first()
        if not setting:
            raise ValueError(f"Setting with key {key} not found")
        return setting

settings_repo = SettingsRepository(get_db())