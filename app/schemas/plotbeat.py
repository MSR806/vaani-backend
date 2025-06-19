from typing import List, Optional

from pydantic import BaseModel


class PlotBeatBase(BaseModel):
    content: str
    type: str
    source_id: Optional[int] = None
    plot_beat_number: Optional[int] = None
    character_ids: Optional[List[int]] = []


class PlotBeatCreate(PlotBeatBase):
    pass


class PlotBeatUpdate(BaseModel):
    content: Optional[str] = None
    type: Optional[str] = None
    source_id: Optional[int] = None
    character_ids: Optional[List[int]] = None


class PlotBeatRead(PlotBeatBase):
    id: int

    class Config:
        from_attributes = True
