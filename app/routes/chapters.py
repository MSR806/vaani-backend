from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from ..database import get_db
from ..schemas.schemas import (
    ChapterCreate,
    ChapterUpdate,
    ChapterResponse,
    ChapterGenerateRequest,
    ChapterSourceTextUpdate,
    ChapterStateUpdate,
)
from ..services.chapter_service import (
    create_chapter,
    update_chapter,
    get_chapter,
    generate_chapter_outline,
    stream_chapter_content,
    patch_chapter_source_text,
    delete_chapter,
    patch_chapter_state,
)
from ..services.book_service import (
    get_book,
    get_book_chapters,
)
from ..services.character_service import extract_chapter_characters
from ..auth import require_write_permission

router = APIRouter(tags=["chapters"])


@router.post("/books/{book_id}/chapters")
def create_chapter_route(
    book_id: int, 
    chapter: ChapterCreate, 
    db: Session = Depends(get_db),
    current_user: dict = Depends(require_write_permission)
):
    chapter = create_chapter(db, book_id, chapter, current_user["user_id"])
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
def update_chapter_route(
    book_id: int,
    chapter_id: int,
    chapter_update: ChapterUpdate,
    db: Session = Depends(get_db),
    current_user: dict = Depends(require_write_permission)
):
    chapter = update_chapter(db, book_id, chapter_id, chapter_update, current_user["user_id"])
    if not chapter:
        raise HTTPException(status_code=404, detail="Chapter not found")
    return chapter


@router.delete("/books/{book_id}/chapters/{chapter_id}")
def delete_chapter_route(book_id: int, chapter_id: int, db: Session = Depends(get_db)):
    success = delete_chapter(db, book_id, chapter_id)
    if not success:
        raise HTTPException(status_code=404, detail="Chapter not found")
    return {"detail": "Chapter deleted successfully"}


@router.post("/books/{book_id}/chapters/{chapter_id}/generate-scenes")
async def generate_chapter_outline_route(
    book_id: int,
    chapter_id: int,
    request: ChapterGenerateRequest,
    db: Session = Depends(get_db),
    current_user: dict = Depends(require_write_permission)
):
    return await generate_chapter_outline(db, book_id, chapter_id, request.user_prompt, current_user["user_id"])


@router.post("/books/{book_id}/chapters/{chapter_id}/generate-content")
async def generate_chapter_content_route(
    book_id: int,
    chapter_id: int,
    request: ChapterGenerateRequest,
    db: Session = Depends(get_db),
    current_user: dict = Depends(require_write_permission)
):
    """
    Generate chapter content with streaming support.
    The response is streamed as Server-Sent Events (SSE), and the final content is saved to the database.
    """
    return await stream_chapter_content(db, book_id, chapter_id, request)


@router.get("/chapters/{chapter_id}/characters", deprecated=True)
async def extract_chapter_characters_route(
    chapter_id: int, db: Session = Depends(get_db)
):
    return await extract_chapter_characters(db, chapter_id)


@router.patch(
    "/books/{book_id}/chapters/{chapter_id}/source-text", response_model=ChapterResponse
)
def update_chapter_source_text(
    book_id: int,
    chapter_id: int,
    update: ChapterSourceTextUpdate,
    db: Session = Depends(get_db),
    current_user: dict = Depends(require_write_permission)
):
    chapter = patch_chapter_source_text(db, book_id, chapter_id, update.source_text, current_user["user_id"])
    if not chapter:
        raise HTTPException(status_code=404, detail="Chapter not found")
    return chapter


@router.patch(
    "/books/{book_id}/chapters/{chapter_id}/state", response_model=ChapterResponse
)
def update_chapter_state(
    book_id: int,
    chapter_id: int,
    update: ChapterStateUpdate,
    db: Session = Depends(get_db),
    current_user: dict = Depends(require_write_permission)
):
    chapter = patch_chapter_state(db, book_id, chapter_id, update.state, current_user["user_id"])
    if not chapter:
        raise HTTPException(status_code=404, detail="Chapter not found")
    return chapter
