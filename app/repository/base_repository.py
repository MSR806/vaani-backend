from sqlalchemy.orm import Session
from typing import Generic, TypeVar

T = TypeVar("T")


class BaseRepository(Generic[T]):
    def __init__(self, db: Session):
        self.db = db
