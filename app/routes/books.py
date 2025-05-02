from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from ..database import get_db
from ..models.models import Book, Chapter
from ..schemas.schemas import BookCreate, BookUpdate, BookCoverResponse
from ..services.book_service import (
    create_book,
    get_book,
    get_books,
    update_book,
    get_book_chapters,
    generate_book_cover,
)

router = APIRouter(tags=["books"])


@router.get("/books/test")
def test_db(db: Session = Depends(get_db)):
    book = Book(title="Test Book", author="Test Author")
    db.add(book)
    db.commit()

    chapter = Chapter(
        book_id=book.id, title="Chapter 1", chapter_no=1, content="This is test content"
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
async def create_book_route(book: BookCreate, db: Session = Depends(get_db)):
    return await create_book(db, book)


@router.put("/books/{book_id}")
def update_book_route(
    book_id: int, book_update: BookUpdate, db: Session = Depends(get_db)
):
    book = update_book(db, book_id, book_update)
    if not book:
        raise HTTPException(status_code=404, detail="Book not found")
    return book


@router.post("/books/{book_id}/generate-cover")
async def generate_book_cover_route(book_id: int, db: Session = Depends(get_db)):
    # Call the book service to generate the cover
    try:
        book = await generate_book_cover(db, book_id)
        return BookCoverResponse(book_id=book_id, cover_url=book.cover_url)
    except HTTPException as e:
        # Re-raise HTTP exceptions from the service
        raise e
    except Exception as e:
        # Handle any other exceptions
        raise HTTPException(
            status_code=500, detail=f"Error generating book cover: {str(e)}"
        )
