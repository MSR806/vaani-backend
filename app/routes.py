from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from .database import get_db
from .models.models import Book, Chapter, Character, Scene
from .schemas.schemas import (
    BookCreate, BookUpdate, ChapterCreate, ChapterUpdate,
    CharacterCreate, CharacterUpdate, SceneCreate, SceneUpdate,
    ChatRequest, ChatResponse, ChapterResponse, CharacterResponse,
    SceneResponse, ChapterOutlineResponse, SceneOutlineResponse,
    ChapterGenerateRequest, SceneCompletionRequest, SceneCompletionResponse,
    ChapterCharactersResponse, CompletionRequest, NextChapterRequest,
    OutlineRequest, SceneOutlineRequest
)
from .services.book_service import (
    create_book, get_book, get_books, update_book,
    generate_next_chapter, generate_chapter_outline, generate_chapter_content,
    get_book_chapters
)
from .services.chapter_service import (
    create_chapter, update_chapter, get_chapter
)
from .services.character_service import (
    create_character, update_character, get_characters,
    extract_chapter_characters
)
from .services.scene_service import (
    create_scene, update_scene, get_scenes,
    generate_scene_outline, generate_scene_content
)
from .services.chat_service import (
    chat_with_ai, stream_chat, chat_as_character, stream_chat_as_character
)

router = APIRouter()

@router.get("/books/test")
def test_db(db: Session = Depends(get_db)):
    book = Book(title="Test Book", author="Test Author")
    db.add(book)
    db.commit()
    
    chapter = Chapter(
        book_id=book.id,
        title="Chapter 1",
        chapter_no=1,
        content="This is test content"
    )
    db.add(chapter)
    db.commit()
    
    return {"message": "Database test successful", "book_id": book.id}

@router.get("/books")
def get_books_route(db: Session = Depends(get_db)):
    return get_books(db)

@router.get("/books/{book_id}")
def get_book_route(book_id: int, db: Session = Depends(get_db)):
    book = get_book(db, book_id)
    if not book:
        raise HTTPException(status_code=404, detail="Book not found")
    return book

@router.post("/books")
def create_book_route(book: BookCreate, db: Session = Depends(get_db)):
    return create_book(db, book)

@router.put("/books/{book_id}")
def update_book_route(book_id: int, book_update: BookUpdate, db: Session = Depends(get_db)):
    book = update_book(db, book_id, book_update)
    if not book:
        raise HTTPException(status_code=404, detail="Book not found")
    return book

@router.post("/books/{book_id}/chapters")
def create_chapter_route(book_id: int, chapter: ChapterCreate, db: Session = Depends(get_db)):
    chapter = create_chapter(db, book_id, chapter)
    if not chapter:
        raise HTTPException(status_code=404, detail="Book not found")
    return chapter

@router.get("/books/{book_id}/chapters")
def get_book_chapters_route(book_id: int, db: Session = Depends(get_db)):
    # First check if the book exists
    book = get_book(db, book_id)
    if not book:
        raise HTTPException(status_code=404, detail="Book not found")
    
    # Then get the chapters
    chapters = get_book_chapters(db, book_id)
    return chapters

@router.get("/books/{book_id}/chapters/{chapter_id}")
def get_chapter_route(book_id: int, chapter_id: int, db: Session = Depends(get_db)):
    chapter = get_chapter(db, book_id, chapter_id)
    if not chapter:
        raise HTTPException(status_code=404, detail="Chapter not found")
    return chapter

@router.put("/books/{book_id}/chapters/{chapter_id}")
def update_chapter_route(book_id: int, chapter_id: int, chapter_update: ChapterUpdate, db: Session = Depends(get_db)):
    chapter = update_chapter(db, book_id, chapter_id, chapter_update)
    if not chapter:
        raise HTTPException(status_code=404, detail="Chapter not found")
    return chapter

@router.post("/books/{book_id}/chapters/next")
async def generate_next_chapter_route(book_id: int, request: ChapterGenerateRequest, db: Session = Depends(get_db)):
    return await generate_next_chapter(db, book_id, request)

@router.post("/books/{book_id}/chapters/outline")
async def generate_chapter_outline_route(book_id: int, request: ChapterGenerateRequest, db: Session = Depends(get_db)):
    return await generate_chapter_outline(db, book_id, request)

@router.post("/books/{book_id}/chapters/{chapter_id}/generate")
async def generate_chapter_content_route(book_id: int, chapter_id: int, request: ChapterGenerateRequest, db: Session = Depends(get_db)):
    return await generate_chapter_content(db, book_id, chapter_id, request)

@router.post("/characters")
def create_character_route(character: CharacterCreate, db: Session = Depends(get_db)):
    return create_character(db, character)

@router.put("/characters/{character_id}")
def update_character_route(character_id: int, character_update: CharacterUpdate, db: Session = Depends(get_db)):
    character = update_character(db, character_id, character_update)
    if not character:
        raise HTTPException(status_code=404, detail="Character not found")
    return character

@router.get("/characters")
def get_characters_route(book_id: int = None, db: Session = Depends(get_db)):
    return get_characters(db, book_id)

@router.post("/scenes")
def create_scene_route(scene: SceneCreate, db: Session = Depends(get_db)):
    return create_scene(db, scene)

@router.put("/scenes/{scene_id}")
def update_scene_route(scene_id: int, scene_update: SceneUpdate, db: Session = Depends(get_db)):
    scene = update_scene(db, scene_id, scene_update)
    if not scene:
        raise HTTPException(status_code=404, detail="Scene not found")
    return scene

@router.get("/scenes")
def get_scenes_route(chapter_id: int = None, db: Session = Depends(get_db)):
    return get_scenes(db, chapter_id)

@router.post("/scenes/{scene_id}/outline-generation")
async def generate_scene_outline_route(scene_id: int, request: SceneOutlineRequest, db: Session = Depends(get_db)):
    return await generate_scene_outline(db, scene_id, request)

@router.post("/scenes/{scene_id}/completion")
async def generate_scene_content_route(scene_id: int, request: SceneCompletionRequest, db: Session = Depends(get_db)):
    return await generate_scene_content(db, scene_id, request)

@router.get("/chapters/{chapter_id}/characters")
async def extract_chapter_characters_route(chapter_id: int, db: Session = Depends(get_db)):
    return await extract_chapter_characters(db, chapter_id)

@router.post("/chat")
async def chat_with_ai_route(request: ChatRequest):
    return await chat_with_ai(request)

@router.post("/chat/stream")
async def stream_chat_route(request: ChatRequest):
    return await stream_chat(request)

@router.post("/chat/character")
async def chat_as_character_route(request: ChatRequest, db: Session = Depends(get_db)):
    return await chat_as_character(request, db)

@router.post("/chat/character/stream")
async def stream_chat_as_character_route(request: ChatRequest, db: Session = Depends(get_db)):
    return await stream_chat_as_character(request, db) 