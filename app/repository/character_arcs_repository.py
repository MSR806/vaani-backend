from .base_repository import BaseRepository
from sqlalchemy.orm import Session
from app.models.models import CharacterArc
from typing import List, Optional

class CharacterArcsRepository(BaseRepository[CharacterArc]):
    def create(self, content: str, type: str, source_id: int, name: str = None, role: str = None) -> CharacterArc:
        arc = CharacterArc(
            content=content,
            type=type,
            source_id=source_id,
            name=name,
            role=role
        )
        self.db.add(arc)
        self.db.commit()
        self.db.refresh(arc)
        return arc

    def get_by_source_id(self, source_id: int) -> List[CharacterArc]:
        return self.db.query(CharacterArc).filter(CharacterArc.source_id == source_id).all()

    def get_by_type_and_source_id(self, arc_type: str, source_id: int) -> List[CharacterArc]:
        return self.db.query(CharacterArc).filter(CharacterArc.type == arc_type, CharacterArc.source_id == source_id).all() 