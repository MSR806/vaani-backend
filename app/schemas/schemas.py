from pydantic import BaseModel
from typing import Optional, List, Dict


# Book schemas
class BookBase(BaseModel):
    title: str
    author: str


class BookCreate(BookBase):
    pass


class BookUpdate(BaseModel):
    title: str


class Book(BookBase):
    id: int

    class Config:
        from_attributes = True


# Chapter schemas
class ChapterBase(BaseModel):
    title: str
    content: str
    source_text: str | None = None


class ChapterCreate(ChapterBase):
    pass


class ChapterUpdate(BaseModel):
    content: str
    source_text: str | None = None


class ChapterSourceTextUpdate(BaseModel):
    source_text: str | None = None


class ChapterResponse(BaseModel):
    id: int
    book_id: int
    title: str
    chapter_no: int
    content: str
    source_text: str | None = None

    class Config:
        from_attributes = True


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
class CharacterInScene(BaseModel):
    name: str
    description: str


class SceneBase(BaseModel):
    scene_number: int
    title: str
    content: str
    characters: List[CharacterInScene]


class SceneCreate(SceneBase):
    chapter_id: int


class SceneUpdate(BaseModel):
    scene_number: Optional[int] = None
    title: Optional[str] = None
    content: Optional[str] = None
    characters: Optional[List[CharacterInScene]] = None


class SceneResponse(BaseModel):
    id: int
    scene_number: int
    title: str
    chapter_id: int
    content: str
    characters: List[CharacterResponse]

    class Config:
        from_attributes = True


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


class SceneCompletionRequest(BaseModel):
    outline: str


class SceneCompletionResponse(BaseModel):
    content: str


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
    characters: List[CharacterInScene]
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


class NextChapterRequest(BaseModel):
    user_prompt: str
