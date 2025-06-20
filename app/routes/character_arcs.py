from fastapi import APIRouter, Depends, HTTPException, Path
from sqlalchemy.orm import Session

from app.database import get_db
from app.schemas.character_arcs import CharacterArcUpdate
from app.services.character_arc_service import CharacterArcService
from app.utils.exceptions import CharacterArcNotFoundException

router = APIRouter()


@router.get("/character-arcs")
def get_character_arcs_by_type_and_source_id(
    type: str, source_id: int, db: Session = Depends(get_db)
):
    service = CharacterArcService(db)
    return service.get_character_arcs_by_type_and_source_id(type, source_id)


@router.put("/character-arcs/{character_arc_id}")
def update_character_arc(
    update_data: CharacterArcUpdate,
    character_arc_id: int = Path(..., gt=0),
    db: Session = Depends(get_db),
):
    service = CharacterArcService(db)
    try:
        # Convert Pydantic model to dict, excluding None values
        update_dict = {k: v for k, v in update_data.dict().items() if v is not None}

        # Don't proceed if there's nothing to update
        if not update_dict:
            raise HTTPException(status_code=400, detail="No valid fields to update provided")

        return service.update_character_arc(character_arc_id, update_dict)
    except CharacterArcNotFoundException as e:
        raise HTTPException(status_code=404, detail=str(e))
