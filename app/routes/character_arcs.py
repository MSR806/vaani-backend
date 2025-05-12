from fastapi import APIRouter
from ..services.character_arc_service import CharacterArcService

router = APIRouter()

@router.get("/character-arcs")
def get_character_arcs_by_type_and_source_id(
    type: str,
    source_id: int,
):
    service = CharacterArcService()
    return service.get_character_arcs_by_type_and_source_id(type, source_id)