from fastapi import APIRouter
from ..services.plot_beat_service import PlotBeatService

router = APIRouter()

@router.get("/plot-beats")
def get_plot_beats_by_type_and_source_id(
    type: str,
    source_id: int
):
    service = PlotBeatService()
    return service.get_plot_beats_by_type_and_source_id(type, source_id)
    