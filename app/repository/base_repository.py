from sqlalchemy.orm import Session
from typing import Generic, TypeVar, Optional

T = TypeVar('T')

class BaseRepository(Generic[T]):
    _global_db: Optional[Session] = None

    @classmethod
    def set_session(cls, db: Session):
        cls._global_db = db

    def __init__(self, db: Optional[Session] = None):
        if db is not None:
            self.db = db
        elif self._global_db is not None:
            self.db = self._global_db
        else:
            raise ValueError("No database session provided to repository and no global session set.")
