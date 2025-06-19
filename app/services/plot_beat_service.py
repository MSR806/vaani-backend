from typing import Any, Dict

from requests import Session

from app.repository.plot_beat_repository import PlotBeatRepository


class PlotBeatService:
    def __init__(self, db: Session):
        self.plot_beat_repo = PlotBeatRepository(db)

    def get_plot_beats_by_type_and_source_id(self, type: str, source_id: int):
        return self.plot_beat_repo.get_by_source_id_and_type(source_id, type)

    def get_plot_beat_by_id(self, plot_beat_id: int):
        return self.plot_beat_repo.get_by_id(plot_beat_id)

    def update_plot_beat(self, plot_beat_id: int, update_data: Dict[str, Any]):
        return self.plot_beat_repo.update(plot_beat_id, update_data)
