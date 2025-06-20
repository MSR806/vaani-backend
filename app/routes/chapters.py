from typing import List

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ..auth import require_write_permission
from ..database import get_db
from ..schemas.schemas import (
    ChapterCreate,
    ChapterGenerateRequest,
    ChapterResponse,
    ChaptersBulkUploadRequest,
    ChapterSourceTextUpdate,
    ChapterStateUpdate,
    ChapterUpdate,
)
from ..services.book_service import get_book, get_book_chapters
from ..services.chapter_rewrite_service import stream_chapter_rewrite
from ..services.chapter_service import (
    bulk_upload_chapters,
    create_chapter,
    delete_all_chapters,
    delete_chapter,
    generate_chapter_outline,
    get_chapter,
    patch_chapter_source_text,
    patch_chapter_state,
    stream_chapter_content,
    update_chapter,
)
from ..services.character_service import extract_chapter_characters

router = APIRouter(tags=["chapters"])


@router.post("/books/{book_id}/chapters")
def create_chapter_route(
    book_id: int,
    chapter: ChapterCreate,
    db: Session = Depends(get_db),
    current_user: dict = Depends(require_write_permission),
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
    current_user: dict = Depends(require_write_permission),
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


@router.delete("/books/{book_id}/chapters")
def delete_all_chapters_route(
    book_id: int,
    db: Session = Depends(get_db),
    current_user: dict = Depends(require_write_permission),
):
    result = delete_all_chapters(db, book_id)
    return result


@router.post("/books/{book_id}/chapters/{chapter_id}/generate-scenes")
async def generate_chapter_outline_route(
    book_id: int,
    chapter_id: int,
    request: ChapterGenerateRequest,
    db: Session = Depends(get_db),
    current_user: dict = Depends(require_write_permission),
):
    return await generate_chapter_outline(
        db, book_id, chapter_id, request.user_prompt, current_user["user_id"]
    )


@router.post("/books/{book_id}/chapters/{chapter_id}/generate-content")
async def generate_chapter_content_route(
    book_id: int,
    chapter_id: int,
    request: ChapterGenerateRequest,
    db: Session = Depends(get_db),
    current_user: dict = Depends(require_write_permission),
):
    return await stream_chapter_content(db, book_id, chapter_id, request)


@router.get("/chapters/{chapter_id}/characters", deprecated=True)
async def extract_chapter_characters_route(chapter_id: int, db: Session = Depends(get_db)):
    return await extract_chapter_characters(db, chapter_id)


@router.patch("/books/{book_id}/chapters/{chapter_id}/source-text", response_model=ChapterResponse)
def update_chapter_source_text(
    book_id: int,
    chapter_id: int,
    update: ChapterSourceTextUpdate,
    db: Session = Depends(get_db),
    current_user: dict = Depends(require_write_permission),
):
    chapter = patch_chapter_source_text(
        db, book_id, chapter_id, update.source_text, current_user["user_id"]
    )
    if not chapter:
        raise HTTPException(status_code=404, detail="Chapter not found")
    return chapter


@router.patch("/books/{book_id}/chapters/{chapter_id}/state", response_model=ChapterResponse)
def update_chapter_state(
    book_id: int,
    chapter_id: int,
    update: ChapterStateUpdate,
    db: Session = Depends(get_db),
    current_user: dict = Depends(require_write_permission),
):
    chapter = patch_chapter_state(db, book_id, chapter_id, update.state, current_user["user_id"])
    if not chapter:
        raise HTTPException(status_code=404, detail="Chapter not found")
    return chapter


@router.post("/books/{book_id}/chapters/bulk-upload", response_model=List[ChapterResponse])
def bulk_upload_chapters_route(
    book_id: int,
    upload_request: ChaptersBulkUploadRequest,
    db: Session = Depends(get_db),
    current_user: dict = Depends(require_write_permission),
):
    chapters = bulk_upload_chapters(
        db, book_id, upload_request.html_content, current_user["user_id"]
    )
    if chapters is None:
        raise HTTPException(status_code=404, detail="Book not found")
    return chapters


@router.post("/books/{book_id}/chapters/{chapter_id}/rewrite")
async def rewrite_chapter_route(
    book_id: int,
    chapter_id: int,
    db: Session = Depends(get_db),
    current_user: dict = Depends(require_write_permission),
):
    return await stream_chapter_rewrite(db, book_id, chapter_id)
