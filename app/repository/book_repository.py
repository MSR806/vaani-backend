import time
from typing import List, Optional

from app.models.models import Book

from .base_repository import BaseRepository


class BookRepository(BaseRepository[Book]):

    def get_by_id(self, book_id: int) -> Optional[Book]:
        return self.db.query(Book).filter(Book.id == book_id).first()

    def get_all(self) -> List[Book]:
        return self.db.query(Book).all()

    def create(
        self, title: str, author: str, author_id: str, cover_url: str = None, user_id: str = None
    ) -> Book:
        current_time = int(time.time())
        book = Book(
            title=title,
            author=author,
            author_id=author_id,
            cover_url=cover_url,
            created_at=current_time,
            updated_at=current_time,
            created_by=user_id,
            updated_by=user_id,
        )
        self.db.add(book)
        self.db.commit()
        self.db.refresh(book)
        return book

    def update(self, book_id: int, **kwargs) -> Optional[Book]:
        book = self.get_by_id(book_id)
        if not book:
            return None
        for key, value in kwargs.items():
            if hasattr(book, key):
                setattr(book, key, value)
        book.updated_at = int(time.time())
        self.db.commit()
        self.db.refresh(book)
        return book

    def delete(self, book_id: int) -> bool:
        book = self.get_by_id(book_id)
        if not book:
            return False
        self.db.delete(book)
        self.db.commit()
        return True
