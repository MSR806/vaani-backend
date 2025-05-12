from app.repository.plot_beat_repository import PlotBeatRepository

class PlotBeatService:
    def __init__(self):
        self.plot_beat_repo = PlotBeatRepository()
    
    def get_plot_beats_by_type_and_source_id(self, type: str, source_id: int):
        return self.plot_beat_repo.get_by_source_id_and_type(source_id, type)
        