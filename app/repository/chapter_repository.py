from .base_repository import BaseRepository
from sqlalchemy.orm import Session
from app.models.models import Chapter
from typing import List, Optional
import time

class ChapterRepository(BaseRepository[Chapter]):
    
    def get_by_id(self, chapter_id: int) -> Optional[Chapter]:
        return self.db.query(Chapter).filter(Chapter.id == chapter_id).first()

    def get_all(self) -> List[Chapter]:
        return self.db.query(Chapter).all()

    def get_by_book_id(self, book_id: int) -> List[Chapter]:
        return self.db.query(Chapter).filter(Chapter.book_id == book_id).all()

    def create(self, book_id: int, title: str, chapter_no: int, content: str, source_text: str = None, state: str = None, user_id: str = None) -> Chapter:
        current_time = int(time.time())
        chapter = Chapter(
            book_id=book_id,
            title=title,
            chapter_no=chapter_no,
            content=content,
            source_text=source_text,
            state=state,
            created_at=current_time,
            updated_at=current_time,
            created_by=user_id,
            updated_by=user_id
        )
        self.db.add(chapter)
        self.db.commit()
        self.db.refresh(chapter)
        return chapter

    def update(self, chapter: Chapter) -> Chapter:
        merged_chapter = self.db.merge(chapter)
        self.db.commit()
        self.db.refresh(merged_chapter)
        return merged_chapter

    def delete(self, chapter_id: int) -> bool:
        chapter = self.get_by_id(chapter_id)
        if not chapter:
            return False
        self.db.delete(chapter)
        self.db.commit()
        return True 