import time
from typing import List, Optional

from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.models.enums import PromptSource
from app.models.models import Prompt
from app.repository.prompt_repository import PromptRepository
from app.schemas.prompts import PromptCreate, PromptUpdate


def create_prompt(db: Session, prompt_data: PromptCreate, user_id: str) -> Prompt:
    current_time = int(time.time())

    prompt = Prompt(
        title=prompt_data.title,
        content=prompt_data.content,
        source=prompt_data.source,
        created_at=current_time,
        updated_at=current_time,
        created_by=user_id,
        updated_by=user_id,
    )

    repository = PromptRepository(db)
    return repository.create(prompt)


def get_prompt(db: Session, prompt_id: int) -> Prompt:
    repository = PromptRepository(db)
    prompt = repository.get_by_id(prompt_id)

    if prompt is None:
        raise HTTPException(status_code=404, detail="Prompt not found")

    return prompt


def get_all_prompts(db: Session, source: Optional[PromptSource] = None) -> List[Prompt]:
    repository = PromptRepository(db)
    return repository.get_all(source=source)


def update_prompt(db: Session, prompt_id: int, prompt_data: PromptUpdate, user_id: str) -> Prompt:
    repository = PromptRepository(db)
    prompt = repository.get_by_id(prompt_id)

    if prompt is None:
        raise HTTPException(status_code=404, detail="Prompt not found")

    update_data = prompt_data.model_dump(exclude_unset=True)
    if not update_data:
        raise HTTPException(status_code=400, detail="No fields to update")

    if "title" in update_data:
        prompt.title = update_data["title"]
    if "content" in update_data:
        prompt.content = update_data["content"]
    if "source" in update_data:
        prompt.source = update_data["source"]

    prompt.updated_at = int(time.time())
    prompt.updated_by = user_id

    return repository.update(prompt)


def delete_prompt(db: Session, prompt_id: int) -> None:
    repository = PromptRepository(db)
    prompt = repository.get_by_id(prompt_id)

    if prompt is None:
        raise HTTPException(status_code=404, detail="Prompt not found")

    repository.delete(prompt)
