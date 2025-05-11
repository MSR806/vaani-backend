from pydantic import BaseModel
from typing import Optional, List, Dict
from enum import Enum


# Book schemas
class BookBase(BaseModel):
    title: str
    author: str | None = None
    author_id: str | None = None


class BookCreate(BaseModel):
    title: str


class BookUpdate(BaseModel):
    title: str


class BookResponse(BaseModel):
    id: int
    title: str
    author: str | None = None
    cover_url: str | None = None

    class Config:
        from_attributes = True


class Book(BookBase):
    id: int

    class Config:
        from_attributes = True


# Chapter schemas
class ChapterBase(BaseModel):
    title: str
    content: str
    source_text: str | None = None
    state: str | None = None


class ChapterCreate(ChapterBase):
    pass


class ChapterUpdate(BaseModel):
    content: str
    source_text: str | None = None
    state: str | None = None


class ChapterSourceTextUpdate(BaseModel):
    source_text: str | None = None


class ChapterResponse(BaseModel):
    id: int
    book_id: int
    title: str
    chapter_no: int
    content: str
    source_text: str | None = None
    state: str | None = None

    class Config:
        from_attributes = True


class ChapterStateUpdate(BaseModel):
    state: str | None = None


# Character schemas
class CharacterBase(BaseModel):
    name: str
    description: str


class CharacterCreate(CharacterBase):
    book_id: int


class CharacterUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None


class CharacterResponse(BaseModel):
    id: int
    name: str
    description: str
    book_id: int

    class Config:
        from_attributes = True


# Scene schemas
class SceneBase(BaseModel):
    scene_number: int
    title: str
    content: str


class SceneCreate(SceneBase):
    chapter_id: int


class SceneUpdate(BaseModel):
    scene_number: Optional[int] = None
    title: Optional[str] = None
    content: Optional[str] = None


class SceneResponse(BaseModel):
    id: int
    scene_number: int
    title: str
    chapter_id: int
    content: str

    class Config:
        from_attributes = True


# Scene reordering schema
class SceneReorderItem(BaseModel):
    id: int
    scene_number: int

class SceneReorderRequest(BaseModel):
    scenes: List[SceneReorderItem]


# Chat schemas
class ChatMessage(BaseModel):
    role: str
    content: str


class ChatRequest(BaseModel):
    messages: List[ChatMessage]
    system_prompt: Optional[str] = "You are a helpful AI assistant."
    character_name: Optional[str] = None
    chapter_id: Optional[int] = None


class ChatResponse(BaseModel):
    message: str


# Generation request schemas
class ChapterGenerateRequest(BaseModel):
    user_prompt: str


class SceneOutlineRequest(BaseModel):
    user_prompt: str


class CharacterOutlineRequest(BaseModel):
    user_prompt: str

# Outline schemas
class OutlineRequest(BaseModel):
    user_prompt: str


class OutlineSection(BaseModel):
    title: str
    content: str


class ChapterOutline(BaseModel):
    sections: List[OutlineSection]


class SceneOutlineResponse(BaseModel):
    scene_number: int
    title: str
    content: str


class ChapterOutlineResponse(BaseModel):
    scenes: List[SceneOutlineResponse]


# Character extraction schemas
class ExtractedCharacter(BaseModel):
    name: str
    description: str
    gender: str
    image_url: str


class ChapterCharactersResponse(BaseModel):
    characters: List[ExtractedCharacter]


class BookCoverResponse(BaseModel):
    book_id: int
    cover_url: str


# Completion schemas
class CompletionRequest(BaseModel):
    context: str
    user_prompt: str
    use_source_content: bool = False
    chapter_id: int | None = None
    book_id: int | None = None
    llm_model: str | None = None


class NextChapterRequest(BaseModel):
    user_prompt: str


# Setting schemas
class SettingBase(BaseModel):
    key: str
    title: str | None = None
    section: str | None = None
    value: str
    description: str | None = None
    type: str = "string"  # string or list
    options: str | None = None  # JSON string of options


class SettingCreate(SettingBase):
    pass


class SettingUpdate(BaseModel):
    id: int
    value: str


class SettingResponse(BaseModel):
    id: int
    key: str
    title: str | None = None
    section: str | None = None
    value: str
    description: str | None = None
    type: str
    options: str | None = None

    class Config:
        from_attributes = True


class SettingBatchUpdate(BaseModel):
    settings: List[SettingUpdate]


# Chapter bulk upload schema
class ChaptersBulkUploadRequest(BaseModel):
    book_id: int
    html_content: str


# Character Arc schemas
class CharacterArcBase(BaseModel):
    content: str
    type: str
    source_id: Optional[int] = None
    archetype: Optional[str] = None

class CharacterArcCreate(CharacterArcBase):
    pass

class CharacterArcRead(CharacterArcBase):
    id: int

    class Config:
        orm_mode = True


# PlotBeat schemas
class PlotBeatBase(BaseModel):
    content: str
    type: str
    source_id: Optional[int] = None
    plot_beat_number: Optional[int] = None

class PlotBeatCreate(PlotBeatBase):
    pass

class PlotBeatRead(PlotBeatBase):
    id: int
    class Config:
        orm_mode = True


# Template schemas
class TemplateStatusEnum(str, Enum):
    NOT_STARTED = "NOT_STARTED"
    IN_PROGRESS = "IN_PROGRESS"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"

class TemplateBase(BaseModel):
    name: str
    book_id: int
    summary_status: Optional[TemplateStatusEnum] = None
    character_arc_status: Optional[TemplateStatusEnum] = None
    plot_beats_status: Optional[TemplateStatusEnum] = None
    character_arc_template_status: Optional[TemplateStatusEnum] = None
    plot_beat_template_status: Optional[TemplateStatusEnum] = None

class TemplateCreate(TemplateBase):
    pass

class TemplateUpdate(BaseModel):
    name: str | None = None
    book_id: int | None = None
    summary_status: Optional[TemplateStatusEnum] = None
    character_arc_status: Optional[TemplateStatusEnum] = None
    plot_beats_status: Optional[TemplateStatusEnum] = None
    character_arc_template_status: Optional[TemplateStatusEnum] = None
    plot_beat_template_status: Optional[TemplateStatusEnum] = None

class TemplateRead(TemplateBase):
    id: int
    class Config:
        orm_mode = True
