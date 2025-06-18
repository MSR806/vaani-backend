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
    blood_relations: Optional[str] = ""


class CharacterReference(BaseModel):
    index: int
    name: str


class CharacterArcNameGroup(BaseModel):
    indices: List[int]
    canonical_name: str


class CharacterArcNameGroups(BaseModel):
    groups: List[CharacterArcNameGroup]


# Content JSON Structure Schema
class CharacterArcContentJSON(BaseModel):
    chapter_range_content: List[CharacterArcContent]
    blood_relations: Optional[str] = ""
    gender_age: Optional[str] = ""
    description: Optional[str] = ""


class CharacterArc(BaseModel):
    name: str
    role: Optional[str] = ""
    archetype: Optional[str] = ""
    content_json: CharacterArcContentJSON
