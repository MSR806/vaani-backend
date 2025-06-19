from typing import Dict, Any
from app.repository.character_arcs_repository import CharacterArcsRepository
from sqlalchemy.orm import Session


class CharacterArcService:
    def __init__(self, db: Session):
        self.character_arcs_repo = CharacterArcsRepository(db)

    def get_character_arcs_by_type_and_source_id(self, type: str, source_id: int):
        return self.character_arcs_repo.get_by_type_and_source_id(type, source_id)

    def get_character_arc_by_id(self, character_arc_id: int):
        return self.character_arcs_repo.get_by_id(character_arc_id)

    def update_character_arc(self, character_arc_id: int, update_data: Dict[str, Any]):
        return self.character_arcs_repo.update(character_arc_id, update_data)

    def get_character_arcs_by_book_id(self, book_id: int):
        return self.character_arcs_repo.get_character_arcs_by_book_id(book_id)
