from pydantic import BaseModel
from typing import List, Optional

class ChapterBase(BaseModel):
    title: str
    chapter_no: int
    content: str

class ChapterCreate(ChapterBase):
    book_id: int

class Chapter(ChapterBase):
    id: int
    book_id: int

    class Config:
        from_attributes = True

class BookBase(BaseModel):
    title: str
    author: str

class BookCreate(BookBase):
    pass

class Book(BookBase):
    id: int
    chapters: List[Chapter] = []

    class Config:
        from_attributes = True

class BookList(BaseModel):
    id: int
    title: str
    author: str

    class Config:
        from_attributes = True

class ChapterList(BaseModel):
    id: int
    title: str
    chapter_no: int

    class Config:
        from_attributes = True 