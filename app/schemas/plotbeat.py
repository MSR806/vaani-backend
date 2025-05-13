from pydantic import BaseModel
from typing import Optional


class PlotBeatBase(BaseModel):
    content: str
    type: str
    source_id: Optional[int] = None
    plot_beat_number: Optional[int] = None


class PlotBeatCreate(PlotBeatBase):
    pass


class PlotBeatUpdate(BaseModel):
    content: Optional[str] = None
    type: Optional[str] = None
    source_id: Optional[int] = None


class PlotBeatRead(BaseModel):
    id: int
    
    class Config:
        orm_mode = True
