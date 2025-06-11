from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any


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


# Models for Character Arc Extraction and Consolidation
class CharacterArcContent(BaseModel):
    chapter_range: List[int]
    content: str
    blood_relations: str


class CharacterReference(BaseModel):
    index: int
    name: str


class CharacterArcNameGroup(BaseModel):
    indices: List[int]
    canonical_name: str


class CharacterArcNameGroups(BaseModel):
    groups: List[CharacterArcNameGroup]


class CharacterArc(BaseModel):
    name: str
    role: Optional[str] = ""
    content_json: List[CharacterArcContent]  # JSON string containing list of CharacterArcContent
