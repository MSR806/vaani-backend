from .base_repository import BaseRepository
from app.models.models import CharacterArc
from typing import List, Optional

class CharacterArcsRepository(BaseRepository[CharacterArc]):
    def __init__(self, db: Optional[Session] = None):
        super().__init__(db)

    def create(self, content: str, type: str, source_id: int, name: str = None, role: str = None, archetype: str = None) -> CharacterArc:
        arc = CharacterArc(
            content=content,
            type=type,
            source_id=source_id,
            name=name,
            role=role,
            archetype=archetype
        )
        self.db.add(arc)
        self.db.commit()
        self.db.refresh(arc)
        return arc
        
    def batch_create(self, character_arcs: List[dict]) -> List[CharacterArc]:
        """
        Create multiple character arcs in a single transaction
        
        Args:
            character_arcs: List of dictionaries with the following keys:
                - content: str - The content of the character arc
                - type: str - The type of the character arc
                - source_id: int - The ID of the source (e.g., story_board.template_id)
                - name: str - The name of the character
                - role: str - The role of the character
                
        Returns:
            List of created CharacterArc objects
        """
        created_arcs = []
        
        for arc_data in character_arcs:
            arc = CharacterArc(
                content=arc_data['content'],
                type=arc_data['type'],
                source_id=arc_data['source_id'],
                name=arc_data['name'],
                role=arc_data.get('role')
            )
            self.db.add(arc)
            created_arcs.append(arc)
        
        self.db.commit()
        
        # Refresh all arcs to get their IDs
        for arc in created_arcs:
            self.db.refresh(arc)
            
        return created_arcs

    def get_by_type_and_source_id(self, type: str, source_id: int) -> List[CharacterArc]:
        return self.db.query(CharacterArc).filter(CharacterArc.type == type, CharacterArc.source_id == source_id).all()

    def get_by_name_type_and_source_id(self, name: str, type: str, source_id: int) -> Optional[CharacterArc]:
        return self.db.query(CharacterArc).filter(
            CharacterArc.name == name,
            CharacterArc.type == type,
            CharacterArc.source_id == source_id
        ).first()