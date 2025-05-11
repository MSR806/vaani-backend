from .base_repository import BaseRepository
from sqlalchemy.orm import Session
from app.models.models import PlotBeat
from typing import List

class PlotBeatRepository(BaseRepository[PlotBeat]):
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

    def get_by_source_id(self, source_id: int, type: str) -> List[PlotBeat]:
        return self.db.query(PlotBeat).filter(PlotBeat.source_id == source_id, PlotBeat.type == type).all() 