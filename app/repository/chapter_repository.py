from .base_repository import BaseRepository
from sqlalchemy.orm import Session
from app.models.models import Chapter
from typing import List, Optional, Dict, Any
import time
import logging

logger = logging.getLogger(__name__)

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
        
    def batch_create(self, chapters_data: List[Dict[str, Any]], user_id: Optional[str] = None) -> List[Chapter]:
        try:
            if not chapters_data:
                logger.warning("No chapter data provided for batch creation")
                return []
                
            # Create all chapter objects but don't commit yet
            current_time = int(time.time())
            chapters = []
            
            for data in chapters_data:
                chapter = Chapter(
                    book_id=data.get("book_id"),
                    title=data.get("title"),
                    chapter_no=data.get("chapter_no"),
                    content=data.get("content", ""),
                    source_text=data.get("source_text"),
                    state=data.get("state", "DRAFT"),
                    created_at=current_time,
                    updated_at=current_time,
                    created_by=user_id,
                    updated_by=user_id
                )
                chapters.append(chapter)
            
            # Add all chapters in a single batch and commit once
            self.db.add_all(chapters)
            self.db.commit()
            
            # Refresh all objects to get their database-generated IDs
            for chapter in chapters:
                self.db.refresh(chapter)
                
            return chapters
            
        except Exception as e:
            self.db.rollback()
            logger.error(f"Error in batch chapter creation: {str(e)}")
            return []