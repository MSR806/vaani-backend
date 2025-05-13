from fastapi import APIRouter, HTTPException, Path

from ..services.character_arc_service import CharacterArcService
from ..utils.exceptions import CharacterArcNotFoundException
from ..schemas.character_arcs import CharacterArcUpdate

router = APIRouter()

@router.get("/character-arcs")
def get_character_arcs_by_type_and_source_id(
    type: str,
    source_id: int,
):
    service = CharacterArcService()
    return service.get_character_arcs_by_type_and_source_id(type, source_id)

@router.put("/character-arcs/{character_arc_id}")
def update_character_arc(
    update_data: CharacterArcUpdate,
    character_arc_id: int = Path(..., gt=0)
):
    service = CharacterArcService()
    try:
        # Convert Pydantic model to dict, excluding None values
        update_dict = {k: v for k, v in update_data.dict().items() if v is not None}
        
        # Don't proceed if there's nothing to update
        if not update_dict:
            raise HTTPException(status_code=400, detail="No valid fields to update provided")
            
        return service.update_character_arc(character_arc_id, update_dict)
    except CharacterArcNotFoundException as e:
        raise HTTPException(status_code=404, detail=str(e))