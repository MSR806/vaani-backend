from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from ..database import get_db
from ..schemas.storyboard import (
    BooleanResponse,
    StoryboardCreate,
    StoryboardGenerateChaptersSummaryRequest,
    StoryboardResponse,
)
from ..services.storyboard.storyboard_service import StoryboardService

router = APIRouter(
    tags=["storyboard"],
    responses={404: {"description": "Not found"}},
)


@router.post("/storyboard", response_model=StoryboardResponse)
async def create_storyboard(
    storyboard: StoryboardCreate,
    # current_user: dict = Depends(require_storyboard_write_permission)):
    db: Session = Depends(get_db),
):

    storyboard_service = StoryboardService(db, "test")
    storyboard = storyboard_service.create_storyboard(
        storyboard.book_id, storyboard.template_id, storyboard.prompt
    )
    return storyboard


@router.get("/storyboard/{storyboard_id}", response_model=StoryboardResponse)
def get_storyboard_by_id(storyboard_id: int, db: Session = Depends(get_db)):
    storyboard_service = StoryboardService(db, "test")
    storyboard = storyboard_service.get_storyboard_by_id(storyboard_id)
    return storyboard


@router.put("/storyboard/{storyboard_id}/continue", response_model=StoryboardResponse)
def continue_storyboard(storyboard_id: int, db: Session = Depends(get_db)):
    storyboard_service = StoryboardService(db, "test")
    storyboard = storyboard_service.continue_storyboard(storyboard_id)
    return storyboard


@router.post(
    "/storyboard/{storyboard_id}/generate-chapters-summary", response_model=BooleanResponse
)
async def generate_chapters_summary(
    storyboard_id: int,
    request: StoryboardGenerateChaptersSummaryRequest,
    db: Session = Depends(get_db),
):
    storyboard_service = StoryboardService(db, "test")
    chapters = await storyboard_service.generate_chapters_summary(
        storyboard_id, request.plot_beat_id
    )
    return BooleanResponse(success=True, message=f"Generated {len(chapters)} chapters")
