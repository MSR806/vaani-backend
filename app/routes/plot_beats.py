from fastapi import APIRouter, Depends, HTTPException, Path
from requests import Session

from database import get_db

from ..services.plot_beat_service import PlotBeatService
from ..utils.exceptions import PlotBeatNotFoundException
from ..schemas.plotbeat import PlotBeatUpdate

router = APIRouter()


@router.get("/plot-beats")
def get_plot_beats_by_type_and_source_id(type: str, source_id: int, db: Session = Depends(get_db)):
    service = PlotBeatService(db)
    return service.get_plot_beats_by_type_and_source_id(type, source_id)


@router.put("/plot-beats/{plot_beat_id}")
def update_plot_beat(
    update_data: PlotBeatUpdate, plot_beat_id: int = Path(..., gt=0), db: Session = Depends(get_db)
):

    service = PlotBeatService(db)
    try:
        # Convert Pydantic model to dict, excluding None values
        update_dict = {k: v for k, v in update_data.dict().items() if v is not None}

        # Don't proceed if there's nothing to update
        if not update_dict:
            raise HTTPException(status_code=400, detail="No valid fields to update provided")

        return service.update_plot_beat(plot_beat_id, update_dict)
    except PlotBeatNotFoundException as e:
        raise HTTPException(status_code=404, detail=str(e))
