from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from ..database import get_db
from ..models.models import Book, Chapter
from ..schemas.schemas import BookCreate, BookUpdate, ChapterResponse, NextChapterRequest
from ..services.ai_service import get_openai_client
from ..config import OPENAI_MODEL

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

@router.put("/books/{book_id}")
def update_book(book_id: int, book_update: BookUpdate, db: Session = Depends(get_db)):
    book = db.query(Book).filter(Book.id == book_id).first()
    if not book:
        raise HTTPException(status_code=404, detail="Book not found")
    
    book.title = book_update.title
    db.commit()
    db.refresh(book)
    return book

@router.post("/books/{book_id}/chapters/next", response_model=ChapterResponse)
async def generate_next_chapter(book_id: int, request: NextChapterRequest, db: Session = Depends(get_db)):
    # Check if book exists and get all chapters
    book = db.query(Book).filter(Book.id == book_id).first()
    if not book:
        raise HTTPException(status_code=404, detail="Book not found")
    
    # Get all chapters in order
    chapters = db.query(Chapter).filter(
        Chapter.book_id == book_id
    ).order_by(Chapter.chapter_no).all()
    
    # Get the next chapter number
    next_chapter_no = 1 if not chapters else chapters[-1].chapter_no + 1
    
    # Prepare context from previous chapters
    previous_chapters_context = "\n\n".join([
        f"Chapter {ch.chapter_no}: {ch.title}\n{ch.content}"
        for ch in chapters
    ])
    
    # Prepare the messages for GPT
    messages = [
        {
            "role": "system",
            "content": """You are a creative writing assistant specialized in writing novel chapters. 
            Based on the previous chapters and the user's prompt (which may include an outline and specific requirements),
            write a complete, engaging chapter that maintains consistency with the story's style and narrative.
            
            Your chapter should:
            1. Be well-structured with natural flow between scenes
            2. Maintain consistent character voices and personalities
            3. Include vivid descriptions and engaging dialogue
            4. Follow any outline or specific requirements provided in the user's prompt
            5. Advance the plot while maintaining suspense
            6. End in a way that hooks readers for the next chapter
            
            Start your response with a suitable chapter title in the format: TITLE: Your Chapter Title
            Then continue with the chapter content."""
        },
        {
            "role": "user",
            "content": f"""Previous Chapters:
{previous_chapters_context}

Requirements for Chapter {next_chapter_no}:
{request.user_prompt}

Please write the complete chapter:"""
        }
    ]

    try:
        client = get_openai_client()
        response = client.chat.completions.create(
            model=OPENAI_MODEL,
            messages=messages,
            temperature=0.7
        )
        
        # Parse the response to separate title and content
        chapter_text = response.choices[0].message.content
        
        # Extract title and content
        try:
            # Split the text into lines and find the title line
            lines = chapter_text.split('\n')
            title = None
            content_start = 0
            
            # Look for the title in the first few lines
            for i, line in enumerate(lines):
                line = line.strip()
                # Remove markdown formatting
                clean_line = line.replace('**', '').strip()
                
                # Check for title in various formats
                if clean_line.startswith('TITLE:'):
                    title = clean_line.replace('TITLE:', '').strip()
                    content_start = i + 1
                    break
            
            # If no title found, use the first non-empty line as title
            if not title:
                for i, line in enumerate(lines):
                    line = line.strip().replace('**', '')
                    if line:
                        title = line
                        content_start = i + 1
                        break
            
            # If still no title, use default
            if not title:
                title = f"Chapter {next_chapter_no}"
            
            # Join the remaining lines for content
            content = '\n'.join(lines[content_start:]).strip()
                
            # Return the generated chapter without saving to DB
            return ChapterResponse(
                id=0,
                book_id=book_id,
                title=title,
                chapter_no=next_chapter_no,
                content=content
            )
            
        except Exception as e:
            raise HTTPException(
                status_code=500,
                detail=f"Failed to process the generated chapter: {str(e)}"
            )
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) 