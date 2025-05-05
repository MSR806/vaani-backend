from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from ..database import get_db
from ..models.models import Book, Chapter
from ..schemas.schemas import BookCreate, BookUpdate, BookCoverResponse, BookBase, BookResponse
from ..services.book_service import (
    create_book,
    get_book,
    get_books,
    update_book,
    get_book_chapters,
    generate_book_cover,
)
from ..auth import get_auth0_user_details, get_current_user, security, require_write_permission
from fastapi.security import HTTPAuthorizationCredentials

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


@router.get("/books", response_model=list[BookResponse])
def get_books_route(db: Session = Depends(get_db)):
    return get_books(db)


@router.get("/books/{book_id}", response_model=BookResponse)
def get_book_route(book_id: int, db: Session = Depends(get_db)):
    book = get_book(db, book_id)
    if not book:
        raise HTTPException(status_code=404, detail="Book not found")
    return book


@router.post("/books", response_model=BookResponse)
async def create_book_route(
    book: BookCreate, 
    db: Session = Depends(get_db),
    current_user: dict = Depends(require_write_permission),
    credentials: HTTPAuthorizationCredentials = Depends(security)
):
    # Get user details from Auth0 UserInfo endpoint
    user_details = await get_auth0_user_details(credentials.credentials)
    
    # Create a BookBase instance with the title and user information
    book_data = BookBase(
        title=book.title,
        author_id=current_user["user_id"],
        author=user_details["name"]  # Use the name from UserInfo
    )
    return await create_book(db, book_data, current_user["user_id"])


@router.put("/books/{book_id}", response_model=BookResponse)
def update_book_route(
    book_id: int, 
    book_update: BookUpdate, 
    db: Session = Depends(get_db),
    current_user: dict = Depends(require_write_permission)
):
    book = update_book(db, book_id, book_update, current_user["user_id"])
    if not book:
        raise HTTPException(status_code=404, detail="Book not found")
    return book


@router.post("/books/{book_id}/generate-cover")
async def generate_book_cover_route(
    book_id: int, 
    db: Session = Depends(get_db),
    current_user: dict = Depends(require_write_permission)
):
    # Call the book service to generate the cover
    try:
        book = await generate_book_cover(db, book_id, current_user["user_id"])
        return BookCoverResponse(book_id=book_id, cover_url=book.cover_url)
    except HTTPException as e:
        # Re-raise HTTP exceptions from the service
        raise e
    except Exception as e:
        # Handle any other exceptions
        raise HTTPException(
            status_code=500, detail=f"Error generating book cover: {str(e)}"
        )
