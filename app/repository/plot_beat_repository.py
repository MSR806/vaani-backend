from .base_repository import BaseRepository
from sqlalchemy.orm import Session
from app.models.models import PlotBeat
from typing import List, Optional

class PlotBeatRepository(BaseRepository[PlotBeat]):
    def __init__(self, db: Optional[Session] = None):
        super().__init__(db)

    def create(self, content: str, type: str, source_id: int) -> PlotBeat:
        plot_beat = PlotBeat(
            content=content,
            type=type,
            source_id=source_id,
        )
        self.db.add(plot_beat)
        self.db.commit()
        self.db.refresh(plot_beat)
        return plot_beat

    def get_by_source_id_and_type(self, source_id: int, type: str) -> List[PlotBeat]:
        return self.db.query(PlotBeat).filter(PlotBeat.source_id == source_id, PlotBeat.type == type).all() 
    
    def get_by_id(self, id: int) -> PlotBeat:
        return self.db.query(PlotBeat).filter(PlotBeat.id == id).first()
