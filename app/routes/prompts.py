from typing import List, Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.auth import require_write_permission
from app.database import get_db
from app.models.enums import PromptSource
from app.schemas.prompts import PromptCreate, PromptResponse, PromptUpdate
from app.services.prompt_service import create_prompt, get_all_prompts, get_prompt, update_prompt

router = APIRouter(tags=["prompts"])


@router.post("/prompts", response_model=PromptResponse)
def create_prompt_route(
    prompt: PromptCreate,
    db: Session = Depends(get_db),
    current_user: dict = Depends(require_write_permission),
):
    return create_prompt(db, prompt, current_user["user_id"])


@router.get("/prompts", response_model=List[PromptResponse])
def get_all_prompts_route(
    db: Session = Depends(get_db),
    source: Optional[PromptSource] = Query(
        None, description="Filter prompts by source (CHAPTER or SCENE)"
    ),
):
    return get_all_prompts(db, source=source)


@router.get("/prompts/{prompt_id}", response_model=PromptResponse)
def get_prompt_route(
    prompt_id: int,
    db: Session = Depends(get_db),
):
    return get_prompt(db, prompt_id)


@router.put("/prompts/{prompt_id}", response_model=PromptResponse)
def update_prompt_route(
    prompt_id: int,
    prompt_update: PromptUpdate,
    db: Session = Depends(get_db),
    current_user: dict = Depends(require_write_permission),
):
    return update_prompt(db, prompt_id, prompt_update, current_user["user_id"])
