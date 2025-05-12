from app.repository.character_arcs_repository import CharacterArcsRepository

class CharacterArcService:
    def __init__(self):
        self.character_arcs_repo = CharacterArcsRepository()
    
    def get_character_arcs_by_type_and_source_id(self, type: str, source_id: int):
        return self.character_arcs_repo.get_by_type_and_source_id(type, source_id)
    
    def get_character_arc_by_id(self, character_arc_id: int):
        return self.character_arcs_repo.get_by_id(character_arc_id)