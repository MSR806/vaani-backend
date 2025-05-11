from app.models.models import StoryBoard
from .base_repository import BaseRepository
from app.models.models import StoryBoardStatus

class StoryBoardRepository(BaseRepository[StoryBoard]):
    def create(self, book_id: int, template_id: int, prompt: str, user_id: str) -> StoryBoard:
        story_board = StoryBoard(
            book_id=book_id,
            template_id=template_id,
            prompt=prompt,
            created_at=int(time.time()),
            updated_at=int(time.time()),
            created_by=user_id,
            updated_by=user_id,
            status=StoryBoardStatus.NOT_STARTED
        )
        self.db.add(story_board)
        self.db.commit()
        self.db.refresh(story_board)
        return story_board
    
    def update(self, story_board_id: int, **kwargs) -> StoryBoard:
        story_board = self.db.query(StoryBoard).filter(StoryBoard.id == story_board_id).first()
        if not story_board:
            raise HTTPException(status_code=404, detail="Story board not found")
        for key, value in kwargs.items():
            setattr(story_board, key, value)
        self.db.commit()
        self.db.refresh(story_board)
        return story_board
    
    def get_by_id(self, story_board_id: int) -> StoryBoard:
        story_board = self.db.query(StoryBoard).filter(StoryBoard.id == story_board_id).first()
        if not story_board:
            raise HTTPException(status_code=404, detail="Story board not found")
        return story_board
    
