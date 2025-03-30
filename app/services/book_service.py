from sqlalchemy.orm import Session
from ..models.models import Book, Chapter
from ..schemas.schemas import BookCreate, BookUpdate, ChapterGenerateRequest
from fastapi import HTTPException
import openai
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Initialize OpenAI client
client = openai.AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY"))

def create_book(db: Session, book: BookCreate) -> Book:
    db_book = Book(title=book.title, author=book.author)
    db.add(db_book)
    db.commit()
    db.refresh(db_book)
    return db_book

def get_book(db: Session, book_id: int) -> Book:
    return db.query(Book).filter(Book.id == book_id).first()

def get_books(db: Session) -> list[Book]:
    return db.query(Book).all()

def update_book(db: Session, book_id: int, book_update: BookUpdate) -> Book:
    book = get_book(db, book_id)
    if not book:
        return None
    
    book.title = book_update.title
    db.commit()
    db.refresh(book)
    return book

def get_book_chapters(db: Session, book_id: int) -> list[Chapter]:
    """Get all chapters for a specific book."""
    return db.query(Chapter).filter(Chapter.book_id == book_id).order_by(Chapter.chapter_no).all()

async def generate_next_chapter(db: Session, book_id: int, request: ChapterGenerateRequest) -> Chapter:
    # Get the book and its latest chapter
    book = get_book(db, book_id)
    if not book:
        raise HTTPException(status_code=404, detail="Book not found")
    
    # Get all previous chapters in order
    chapters = get_book_chapters(db, book_id)
    
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
        response = await client.chat.completions.create(
            model="gpt-4",
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
            
            # Create a new chapter object (but don't save to DB)
            return Chapter(
                id=0,  # Temporary ID
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

async def generate_chapter_outline(db: Session, book_id: int, request: ChapterGenerateRequest) -> dict:
    # Get the book and its latest chapter
    book = get_book(db, book_id)
    if not book:
        raise HTTPException(status_code=404, detail="Book not found")
    
    # Get all previous chapters in order
    chapters = get_book_chapters(db, book_id)
    
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
            "content": """You are a creative writing assistant specialized in creating chapter outlines.
            Based on the previous chapters and the user's prompt,
            create a structured outline for the next chapter.
            
            Your outline should:
            1. Break down the chapter into logical sections
            2. Include key plot points and character interactions
            3. Maintain consistency with the story's style and narrative
            4. Follow any specific requirements provided in the user's prompt
            5. Set up future plot developments
            
            IMPORTANT: Your response must be a valid JSON object with the following structure:
            {
                "sections": [
                    {
                        "title": "Section Title",
                        "content": "Detailed outline of this section"
                    }
                ]
            }
            
            Do not include any text before or after the JSON object."""
        },
        {
            "role": "user",
            "content": f"""Previous Chapters:
{previous_chapters_context}

Requirements for Chapter {next_chapter_no}:
{request.user_prompt}

Please create a detailed outline for this chapter:"""
        }
    ]

    try:
        response = await client.chat.completions.create(
            model="gpt-4",
            messages=messages,
            temperature=0.7
        )
        
        # Parse the response
        try:
            outline_data = response.choices[0].message.content.strip()
            # Clean up any potential markdown formatting
            outline_data = outline_data.replace('```json', '').replace('```', '').strip()
            return outline_data
            
        except Exception as e:
            raise HTTPException(
                status_code=500,
                detail=f"Failed to process the generated outline: {str(e)}"
            )
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

async def generate_chapter_content(db: Session, book_id: int, chapter_id: int, request: ChapterGenerateRequest) -> Chapter:
    # Get the book and chapter
    book = get_book(db, book_id)
    if not book:
        raise HTTPException(status_code=404, detail="Book not found")
    
    chapter = db.query(Chapter).filter(
        Chapter.id == chapter_id,
        Chapter.book_id == book_id
    ).first()
    if not chapter:
        raise HTTPException(status_code=404, detail="Chapter not found")
    
    # Get all previous chapters in order
    chapters = get_book_chapters(db, book_id)
    previous_chapters = [ch for ch in chapters if ch.chapter_no < chapter.chapter_no]
    
    # Prepare context from previous chapters
    previous_chapters_context = "\n\n".join([
        f"Chapter {ch.chapter_no}: {ch.title}\n{ch.content}"
        for ch in previous_chapters
    ])
    
    # Prepare the messages for GPT
    messages = [
        {
            "role": "system",
            "content": """You are a creative writing assistant specialized in writing novel chapters.
            Based on the previous chapters and the provided context,
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

Current Chapter Information:
- Chapter Number: {chapter.chapter_no}
- Title: {chapter.title}

User's Request: {request.user_prompt}

Please write the complete chapter:"""
        }
    ]

    try:
        response = await client.chat.completions.create(
            model="gpt-4",
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
                title = f"Chapter {chapter.chapter_no}"
            
            # Join the remaining lines for content
            content = '\n'.join(lines[content_start:]).strip()
            
            # Update the chapter in the database
            chapter.title = title
            chapter.content = content
            db.commit()
            db.refresh(chapter)
            
            return chapter
            
        except Exception as e:
            raise HTTPException(
                status_code=500,
                detail=f"Failed to process the generated chapter: {str(e)}"
            )
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) 