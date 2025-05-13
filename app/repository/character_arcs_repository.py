from sqlalchemy.orm import Session
from typing import List, Optional, Dict, Any

from .base_repository import BaseRepository
from app.models.models import CharacterArc, Storyboard
from app.utils.exceptions import CharacterArcNotFoundException

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
                - source_id: int - The ID of the source (e.g., storyboard.template_id)
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
    
    def get_by_id(self, character_arc_id: int) -> CharacterArc:
        arc = self.db.query(CharacterArc).filter(CharacterArc.id == character_arc_id).first()
            
        if not arc:
            raise CharacterArcNotFoundException(f"Character arc with ID {character_arc_id} not found")
            
        return arc
    
    def update(self, character_arc_id: int, update_data: Dict[str, Any]) -> CharacterArc:
        arc = self.get_by_id(character_arc_id)
        for key, value in update_data.items():
            if hasattr(arc, key):
                setattr(arc, key, value)
        
        self.db.commit()
        self.db.refresh(arc)
        
        return arc
    
    def get_character_arcs_by_book_id(self, book_id: int) -> List[CharacterArc]:
        character_arcs = self.db.query(CharacterArc).join(
            Storyboard,
            CharacterArc.source_id == Storyboard.id
        ).filter(
            Storyboard.book_id == book_id,
            CharacterArc.type == "STORYBOARD"
        ).all()
        
        return character_arcs