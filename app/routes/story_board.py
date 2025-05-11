
from fastapi import APIRouter
import asyncio
from sqlalchemy.orm import Session

from ..database import get_db
from ..schemas.story_board_schemas import StoryBoardCreate, StoryBoardResponse
from ..services.story_generator_service import start_generation
from ..repository.story_board_repository import StoryBoardRepository

router = APIRouter(
    tags=["story_board"],
    responses={404: {"description": "Not found"}},
)


@router.post("/story-board", response_model=StoryBoardResponse)
def create_story_board(story_board: StoryBoardCreate):
    story_board_repo = StoryBoardRepository()
    story_board = story_board_repo.create(story_board.book_id, story_board.template_id, story_board.prompt, story_board.user_id)
    asyncio.run(start_generation(story_board.id))
    return story_board
