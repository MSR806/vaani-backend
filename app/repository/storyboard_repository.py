import time
from app.utils.exceptions import StoryboardNotFoundException

from app.models.models import Storyboard
from .base_repository import BaseRepository
from app.models.models import StoryboardStatus

class StoryboardRepository(BaseRepository[Storyboard]):
    def create(self, book_id: int, template_id: int, prompt: str, user_id: str) -> Storyboard:
        storyboard = Storyboard(
            book_id=book_id,
            template_id=template_id,
            prompt=prompt,
            created_at=int(time.time()),
            updated_at=int(time.time()),
            created_by=user_id,
            updated_by=user_id,
            status=StoryboardStatus.NOT_STARTED
        )
        self.db.add(storyboard)
        self.db.commit()
        self.db.refresh(storyboard)
        return storyboard
    
    def update(self, storyboard_id: int, **kwargs) -> Storyboard:
        storyboard = self.db.query(Storyboard).filter(Storyboard.id == storyboard_id).first()
        if not storyboard:
            raise StoryboardNotFoundException(storyboard_id)
        for key, value in kwargs.items():
            setattr(storyboard, key, value)
        self.db.commit()
        self.db.refresh(storyboard)
        return storyboard
    
    def get_by_id(self, storyboard_id: int) -> Storyboard:
        storyboard = self.db.query(Storyboard).filter(Storyboard.id == storyboard_id).first()
        if not storyboard:
            raise StoryboardNotFoundException(storyboard_id)
        return storyboard
    
    def get_by_book_id(self, book_id: int) -> Storyboard:
        storyboard = self.db.query(Storyboard).filter(Storyboard.book_id == book_id).first()
        if not storyboard:
            raise StoryboardNotFoundException(book_id)
        return storyboard
    
