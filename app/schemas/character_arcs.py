from pydantic import BaseModel
from typing import Optional


class CharacterArcBase(BaseModel):
    content: str
    type: str
    source_id: Optional[int] = None
    archetype: Optional[str] = None


class CharacterArcCreate(CharacterArcBase):
    pass


class CharacterArcUpdate(BaseModel):
    content: Optional[str] = None
    type: Optional[str] = None
    source_id: Optional[int] = None
    name: Optional[str] = None
    role: Optional[str] = None
    archetype: Optional[str] = None


class CharacterArcRead(BaseModel):
    id: int
    
    class Config:
        orm_mode = True
