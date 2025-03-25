from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from database import get_db
from models import Book, Chapter
from pydantic import BaseModel
from typing import Optional
import openai
from fastapi.responses import StreamingResponse
import json
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Initialize OpenAI client
openai.api_key = os.getenv("OPENAI_API_KEY")

router = APIRouter()

# Pydantic models for request validation
class BookCreate(BaseModel):
    title: str
    author: str

class ChapterCreate(BaseModel):
    title: str
    chapter_no: int
    content: str

class ChapterUpdate(BaseModel):
    content: str

class CompletionRequest(BaseModel):
    context: str
    user_prompt: str

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
def get_books(db: Session = Depends(get_db)):
    books = db.query(Book).all()
    return books

@router.get("/books/{book_id}")
def get_book(book_id: int, db: Session = Depends(get_db)):
    book = db.query(Book).filter(Book.id == book_id).first()
    if not book:
        raise HTTPException(status_code=404, detail="Book not found")
    return book

@router.get("/books/{book_id}/chapters")
def get_book_chapters(book_id: int, db: Session = Depends(get_db)):
    book = db.query(Book).filter(Book.id == book_id).first()
    if not book:
        raise HTTPException(status_code=404, detail="Book not found")
    return book.chapters

@router.get("/books/{book_id}/chapters/{chapter_id}")
def get_chapter(book_id: int, chapter_id: int, db: Session = Depends(get_db)):
    chapter = db.query(Chapter).filter(
        Chapter.id == chapter_id,
        Chapter.book_id == book_id
    ).first()
    if not chapter:
        raise HTTPException(status_code=404, detail="Chapter not found")
    return chapter

@router.post("/books")
def create_book(book: BookCreate, db: Session = Depends(get_db)):
    db_book = Book(title=book.title, author=book.author)
    db.add(db_book)
    db.commit()
    db.refresh(db_book)
    return db_book

@router.post("/books/{book_id}/chapters")
def create_chapter(book_id: int, chapter: ChapterCreate, db: Session = Depends(get_db)):
    # Check if book exists
    book = db.query(Book).filter(Book.id == book_id).first()
    if not book:
        raise HTTPException(status_code=404, detail="Book not found")
    
    # Check if chapter number already exists
    existing_chapter = db.query(Chapter).filter(
        Chapter.book_id == book_id,
        Chapter.chapter_no == chapter.chapter_no
    ).first()
    if existing_chapter:
        raise HTTPException(status_code=400, detail="Chapter number already exists")
    
    db_chapter = Chapter(
        book_id=book_id,
        title=chapter.title,
        chapter_no=chapter.chapter_no,
        content=chapter.content
    )
    db.add(db_chapter)
    db.commit()
    db.refresh(db_chapter)
    return db_chapter

@router.put("/books/{book_id}/chapters/{chapter_id}")
def update_chapter(book_id: int, chapter_id: int, chapter_update: ChapterUpdate, db: Session = Depends(get_db)):
    chapter = db.query(Chapter).filter(
        Chapter.id == chapter_id,
        Chapter.book_id == book_id
    ).first()
    if not chapter:
        raise HTTPException(status_code=404, detail="Chapter not found")
    
    chapter.content = chapter_update.content
    db.commit()
    db.refresh(chapter)
    return chapter

@router.post("/complete")
async def stream_completion(request: CompletionRequest):
    if not openai.api_key:
        raise HTTPException(status_code=500, detail="OpenAI API key not configured")
    
    try:
        # Prepare the messages for GPT
        messages = [
            {"role": "system", "content": "You are a creative writing assistant. Your task is to continue the story based on the provided context and user prompt. Write in a natural, engaging style that matches the existing narrative."},
            {"role": "user", "content": f"Context: {request.context}\n\nUser Prompt: {request.user_prompt}\n\nPlease continue the story:"}
        ]

        # Create streaming response
        async def generate():
            try:
                stream = openai.ChatCompletion.create(
                    model="gpt-3.5-turbo",
                    messages=messages,
                    stream=True,
                    temperature=0.7,
                    max_tokens=500
                )
                
                for chunk in stream:
                    if chunk.choices[0].delta.get('content'):
                        yield f"data: {json.dumps({'content': chunk.choices[0].delta.content})}\n\n"
                
                yield "data: [DONE]\n\n"
            except Exception as e:
                yield f"data: {json.dumps({'error': str(e)})}\n\n"
                yield "data: [DONE]\n\n"

        return StreamingResponse(
            generate(),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "X-Accel-Buffering": "no"  # This helps with nginx buffering
            }
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) 