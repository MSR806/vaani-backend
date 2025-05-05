from sqlalchemy.orm import Session
from ..models.models import Book, Chapter, Image
from ..schemas.schemas import BookCreate, BookUpdate, ChapterGenerateRequest, BookBase
from fastapi import HTTPException
import openai
import os
from dotenv import load_dotenv
from .image_service import store_image_from_url
from .placeholder_image import generate_placeholder_image
from .ai_service import get_openai_client
from ..config import OPENAI_MODEL
import json

# Load environment variables
load_dotenv()

# Initialize OpenAI client
client = openai.AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY"))

async def create_book(db: Session, book: BookBase) -> Book:
    # Create the book record
    db_book = Book(
        title=book.title, 
        author=book.author,
        author_id=book.author_id
    )
    db.add(db_book)
    db.commit()
    db.refresh(db_book)
    
    # Generate a placeholder image for the book cover
    try:
        # Get placeholder image URL using our helper function
        placeholder_url = await generate_placeholder_image(text=f"Title: {db_book.title}\nAuthor: {db_book.author}")
        
        # Use the image service to store the image from the URL
        placeholder_image = await store_image_from_url(
            db=db,
            url=placeholder_url,
            name=f"placeholder_book_cover_{db_book.id}"
        )
        
        # Create the internal image URL using the /images/:id format
        internal_image_url = f"/images/{placeholder_image.id}"
        
        # Update book with placeholder URL and image ID
        db_book.cover_url = internal_image_url
        db_book.cover_image_id = placeholder_image.id
        db.commit()
        db.refresh(db_book)
    except Exception as e:
        # If placeholder image generation fails, log the error but continue
        print(f"Failed to generate placeholder cover for book {db_book.id}: {str(e)}")
    
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
        # Use the global client instead of getting a new one
        response = await client.chat.completions.create(
            model=OPENAI_MODEL,
            messages=messages,
            temperature=0.7,
            response_format={"type": "json_object"}
        )
        
        # Parse the response
        try:
            outline_data = response.choices[0].message.content.strip()
            # Clean up any potential markdown formatting
            outline_data = outline_data.replace('```json', '').replace('```', '').strip()
            # Parse the JSON string into a Python object
            return json.loads(outline_data)
            
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
            model="gpt-4o-mini",
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

async def generate_book_cover(db: Session, book_id: int):
    """
    Generate a book cover for a book using OpenAI's DALL-E model.
    
    Args:
        db: Database session
        book_id: ID of the book to generate a cover for
        
    Returns:
        The book object with updated cover image information
    """
    # Step 1: Get the book and validate it exists
    book = get_book(db, book_id)
    if not book:
        raise HTTPException(status_code=404, detail="Book not found")
    
    # Step 2: Get all chapters content and extract book information
    chapters = get_book_chapters(db, book_id)
    
    # Prepare content for analysis
    book_title = book.title
    book_author = book.author
    
    # Extract content from chapters
    chapters_content = ""
    for chapter in chapters:
        # Limit the content to avoid token limits - just use the first 500 chars of each chapter
        chapter_sample = chapter.content[:500] if chapter.content else ""
        chapters_content += f"Chapter {chapter.chapter_no}: {chapter.title}\n{chapter_sample}\n\n"
    
    # Get the OpenAI client
    openai_client = openai.OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
    
    # Step 3: Generate a prompt for the book cover using OpenAI
    try:
        # Create a system message that instructs the AI to generate a book cover prompt
        messages = [
            {
                "role": "system",
                "content": """You are an expert movie poster designer. Based on the book information provided, 
                create a detailed prompt for DALL-E to generate a MOVIE-STYLE POSTER for this story.
                Your prompt should capture the essence, themes, mood, and key elements of the book.
                Format your response as a single paragraph that can be directly used as a DALL-E prompt.
                The prompt should include style, key visual elements, color scheme, and mood.
                Design a FLAT 2D movie-style poster - with NO 3D elements or mockups.
                DO NOT include any explanations, just the prompt itself."""
            },
            {
                "role": "user",
                "content": f"""Generate a MOVIE-STYLE POSTER prompt for DALL-E based on the following information:\n\n
                Story Title: {book_title}\n
                Creator: {book_author}\n
                Story Content Sample:\n{chapters_content}\n\n
                Style preference: professional movie poster style\n
                Color scheme preference: appropriate for the story theme\n
                Elements to include: key elements from the story\n
                IMPORTANT: Create a FLAT 2D movie-style poster, with NO book or 3D elements"""
            }
        ]
        
        # Call OpenAI to generate the prompt
        response = openai_client.chat.completions.create(
            model="gpt-4o-mini",
            messages=messages,
            temperature=0.7
        )
        
        # Extract the generated prompt
        dalle_prompt = response.choices[0].message.content.strip()
        
        # Step 4: Use the generated prompt to create the image with DALL-E
        try:
            # Call DALL-E API to generate the image
            image_response = openai_client.images.generate(
                model="dall-e-3",
                prompt=dalle_prompt,
                size="1024x1792",
                quality="standard",
                n=1,
            )
            
            # Get the image URL from the response
            image_url = image_response.data[0].url
            
            # Store the image in the database
            db_image = await store_image_from_url(
                db=db,
                url=image_url,
                name=f"book_cover_{book_id}_{book_title}"
            )
            
            # Create the internal image URL using the /images/:id format
            internal_image_url = f"/images/{db_image.id}"
            
            # Update book with the internal image URL and image ID
            book.cover_url = internal_image_url
            book.cover_image_id = db_image.id
            db.commit()
            
            # Log the successful generation
            print(f"Generated book cover for '{book_title}' with prompt: {dalle_prompt[:100]}...")
            
            # Return the book object
            return book
            
        except Exception as e:
            # If DALL-E generation fails, use a placeholder image from placehold.co
            print(f"DALL-E generation failed: {str(e)}")
            
            # Get placeholder image URL using our helper function
            placeholder_url = await generate_placeholder_image(text=f"Title: {db_book.title}\nAuthor: {db_book.author}")
            
            # Use the image service to store the image from the URL
            placeholder_image = await store_image_from_url(
                db=db,
                url=placeholder_url,
                name=f"placeholder_book_cover_{book_id}"
            )
            
            # Create the internal image URL using the /images/:id format
            internal_image_url = f"/images/{placeholder_image.id}"
            
            # Update book with placeholder URL and image ID
            book.cover_url = internal_image_url
            book.cover_image_id = placeholder_image.id
            db.commit()
            
            return book
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error generating book cover: {str(e)}")