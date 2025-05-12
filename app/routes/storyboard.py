
from fastapi import APIRouter
from ..schemas.storyboard import StoryboardCreate, StoryboardResponse
from ..services.storyboard.storyboard_service import StoryboardService

router = APIRouter(
    tags=["storyboard"],
    responses={404: {"description": "Not found"}},
)


@router.post("/storyboard", response_model=StoryboardResponse)
async def create_storyboard(
    storyboard: StoryboardCreate,
    # current_user: dict = Depends(require_storyboard_write_permission)):
):

    storyboard_service = StoryboardService()
    storyboard = storyboard_service.create_storyboard(storyboard.book_id, storyboard.template_id, storyboard.prompt, "test")
    return storyboard

@router.get("/storyboard/{storyboard_id}", response_model=StoryboardResponse)
def get_storyboard_by_id(storyboard_id: int):
    storyboard_service = StoryboardService()
    storyboard = storyboard_service.get_storyboard_by_id(storyboard_id)
    return storyboard

@router.put("/storyboard/{storyboard_id}/continue", response_model=StoryboardResponse)
def continue_storyboard(storyboard_id: int):
    storyboard_service = StoryboardService()
    storyboard = storyboard_service.continue_storyboard(storyboard_id)
    return storyboard