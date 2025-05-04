from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from ..database import get_db
from ..schemas.schemas import (
    CharacterCreate,
    CharacterUpdate,
    CharacterOutlineRequest,
)
from ..services.character_service import (
    create_character,
    update_character,
    get_characters,
    generate_character_outline,
)
from ..auth import require_write_permission

router = APIRouter(tags=["characters"])


@router.post("/characters")
def create_character_route(
    character: CharacterCreate, 
    db: Session = Depends(get_db),
    current_user: dict = Depends(require_write_permission)
):
    return create_character(db, character)


@router.put("/characters/{character_id}")
def update_character_route(
    character_id: int, 
    character_update: CharacterUpdate, 
    db: Session = Depends(get_db),
    current_user: dict = Depends(require_write_permission)
):
    character = update_character(db, character_id, character_update)
    if not character:
        raise HTTPException(status_code=404, detail="Character not found")
    return character


@router.get("/characters")
def get_characters_route(book_id: int = None, db: Session = Depends(get_db)):
    return get_characters(db, book_id)


@router.post("/characters/{character_id}/generate-outline")
async def generate_character_outline_route(
    character_id: int, 
    request: CharacterOutlineRequest, 
    db: Session = Depends(get_db),
    current_user: dict = Depends(require_write_permission)
):
    return await generate_character_outline(db, character_id, request)
