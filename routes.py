from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from database import get_db
from models import Book, Chapter, Character, Scene
from pydantic import BaseModel
from typing import Optional, List
import openai
from fastapi.responses import StreamingResponse
import json
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Constants
OPENAI_MODEL = "gpt-4o-mini"

# Initialize OpenAI client
client = openai.OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

router = APIRouter()

# Pydantic models for request validation
class BookCreate(BaseModel):
    title: str
    author: str

class BookUpdate(BaseModel):
    title: str

class ChapterCreate(BaseModel):
    title: str
    content: str

class ChapterUpdate(BaseModel):
    content: str

class CompletionRequest(BaseModel):
    context: str
    user_prompt: str

class OutlineRequest(BaseModel):
    user_prompt: str

class OutlineSection(BaseModel):
    title: str
    content: str

class ChapterOutline(BaseModel):
    sections: List[OutlineSection]

class NextChapterRequest(BaseModel):
    user_prompt: str

class ChapterResponse(BaseModel):
    id: int
    book_id: int
    title: str
    chapter_no: int
    content: str

class CharacterCreate(BaseModel):
    name: str
    description: str
    book_id: int

class CharacterUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None

class SceneCreate(BaseModel):
    scene_number: int
    title: str
    chapter_id: int
    character_ids: List[int]

class SceneUpdate(BaseModel):
    scene_number: Optional[int] = None
    title: Optional[str] = None
    character_ids: Optional[List[int]] = None

class SubScene(BaseModel):
    title: str
    content: str

class SceneCompletionRequest(BaseModel):
    user_prompt: str

class SceneCompletionResponse(BaseModel):
    subscenes: List[SubScene]

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
    
    # Get the highest chapter number for this book
    max_chapter = db.query(Chapter).filter(
        Chapter.book_id == book_id
    ).order_by(Chapter.chapter_no.desc()).first()
    
    # Set the next chapter number
    next_chapter_no = 1 if not max_chapter else max_chapter.chapter_no + 1
    
    db_chapter = Chapter(
        book_id=book_id,
        title=chapter.title,
        chapter_no=next_chapter_no,
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

@router.put("/books/{book_id}")
def update_book(book_id: int, book_update: BookUpdate, db: Session = Depends(get_db)):
    book = db.query(Book).filter(Book.id == book_id).first()
    if not book:
        raise HTTPException(status_code=404, detail="Book not found")
    
    book.title = book_update.title
    db.commit()
    db.refresh(book)
    return book

@router.post("/complete")
async def stream_completion(request: CompletionRequest):
    if not client.api_key:
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
                stream = client.chat.completions.create(
                    model=OPENAI_MODEL,
                    messages=messages,
                    stream=True,
                    temperature=0.7
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
                "X-Accel-Buffering": "no"
            }
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/books/{book_id}/chapters/outline", response_model=ChapterOutline)
async def generate_chapter_outline(book_id: int, request: OutlineRequest, db: Session = Depends(get_db)):
    # Check if book exists and get all chapters
    book = db.query(Book).filter(Book.id == book_id).first()
    if not book:
        raise HTTPException(status_code=404, detail="Book not found")
    
    # Get all chapters in order
    chapters = db.query(Chapter).filter(
        Chapter.book_id == book_id
    ).order_by(Chapter.chapter_no).all()
    
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
            Based on the previous chapters and user's prompt, create a structured outline for the next chapter.
            Your response should be in JSON format with a list of sections, where each section has a title and abstract content.
            Keep the content abstract and high-level, focusing on plot points and key events rather than detailed narrative.
            Format your response as: {"sections": [{"title": "section title", "content": "abstract content"}]}"""
        },
        {
            "role": "user",
            "content": f"""Previous Chapters:\n{previous_chapters_context}\n\n
            User's Request for Next Chapter: {request.user_prompt}\n\n
            Please provide a structured outline for the next chapter:"""
        }
    ]

    try:
        response = await client.chat.completions.create(
            model=OPENAI_MODEL,
            messages=messages,
            temperature=0.7
        )
        
        # Parse the response
        outline_text = response.choices[0].message.content
        try:
            outline_data = json.loads(outline_text)
            return ChapterOutline(**outline_data)
        except json.JSONDecodeError:
            raise HTTPException(
                status_code=500,
                detail="Failed to parse the AI response into proper outline format"
            )
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

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
            "content": f"""Previous Chapters:\n{previous_chapters_context}\n\n
            Requirements for Chapter {next_chapter_no}:\n{request.user_prompt}\n\n
            Please write the complete chapter:"""
        }
    ]

    try:
        response = await client.chat.completions.create(
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

@router.post("/characters")
def create_character(character: CharacterCreate, db: Session = Depends(get_db)):
    # Check if book exists
    book = db.query(Book).filter(Book.id == character.book_id).first()
    if not book:
        raise HTTPException(status_code=404, detail="Book not found")
    
    db_character = Character(
        name=character.name,
        description=character.description,
        book_id=character.book_id
    )
    db.add(db_character)
    db.commit()
    db.refresh(db_character)
    return db_character

@router.put("/characters/{character_id}")
def update_character(character_id: int, character_update: CharacterUpdate, db: Session = Depends(get_db)):
    character = db.query(Character).filter(Character.id == character_id).first()
    if not character:
        raise HTTPException(status_code=404, detail="Character not found")
    
    if character_update.name is not None:
        character.name = character_update.name
    if character_update.description is not None:
        character.description = character_update.description
    
    db.commit()
    db.refresh(character)
    return character

@router.get("/characters")
def get_characters(book_id: Optional[int] = None, db: Session = Depends(get_db)):
    query = db.query(Character)
    if book_id is not None:
        query = query.filter(Character.book_id == book_id)
    return query.all()

@router.post("/scenes")
def create_scene(scene: SceneCreate, db: Session = Depends(get_db)):
    # Check if chapter exists
    chapter = db.query(Chapter).filter(Chapter.id == scene.chapter_id).first()
    if not chapter:
        raise HTTPException(status_code=404, detail="Chapter not found")
    
    # Check if all characters exist
    characters = db.query(Character).filter(Character.id.in_(scene.character_ids)).all()
    if len(characters) != len(scene.character_ids):
        raise HTTPException(status_code=404, detail="One or more characters not found")
    
    # Create the scene
    db_scene = Scene(
        scene_number=scene.scene_number,
        title=scene.title,
        chapter_id=scene.chapter_id,
        characters=characters
    )
    db.add(db_scene)
    db.commit()
    db.refresh(db_scene)
    return db_scene

@router.put("/scenes/{scene_id}")
def update_scene(scene_id: int, scene_update: SceneUpdate, db: Session = Depends(get_db)):
    scene = db.query(Scene).filter(Scene.id == scene_id).first()
    if not scene:
        raise HTTPException(status_code=404, detail="Scene not found")
    
    if scene_update.scene_number is not None:
        scene.scene_number = scene_update.scene_number
    if scene_update.title is not None:
        scene.title = scene_update.title
    if scene_update.character_ids is not None:
        # Check if all characters exist
        characters = db.query(Character).filter(Character.id.in_(scene_update.character_ids)).all()
        if len(characters) != len(scene_update.character_ids):
            raise HTTPException(status_code=404, detail="One or more characters not found")
        scene.characters = characters
    
    db.commit()
    db.refresh(scene)
    return scene

@router.get("/scenes")
def get_scenes(chapter_id: Optional[int] = None, db: Session = Depends(get_db)):
    query = db.query(Scene)
    if chapter_id is not None:
        query = query.filter(Scene.chapter_id == chapter_id)
    return query.all()

@router.post("/scenes/{scene_id}/completion", response_model=SceneCompletionResponse)
async def stream_scene_completion(scene_id: int, request: SceneCompletionRequest, db: Session = Depends(get_db)):
    # Get the scene and its chapter
    scene = db.query(Scene).filter(Scene.id == scene_id).first()
    if not scene:
        raise HTTPException(status_code=404, detail="Scene not found")
    
    chapter = db.query(Chapter).filter(Chapter.id == scene.chapter_id).first()
    if not chapter:
        raise HTTPException(status_code=404, detail="Chapter not found")
    
    # Get all previous chapters in order
    previous_chapters = db.query(Chapter).filter(
        Chapter.book_id == chapter.book_id,
        Chapter.chapter_no < chapter.chapter_no
    ).order_by(Chapter.chapter_no).all()
    
    # Get all previous scenes in the current chapter
    previous_scenes = db.query(Scene).filter(
        Scene.chapter_id == chapter.id,
        Scene.scene_number < scene.scene_number
    ).order_by(Scene.scene_number).all()
    
    # Prepare context from previous chapters
    previous_chapters_context = "\n\n".join([
        f"Chapter {ch.chapter_no}: {ch.title}\n{ch.content}"
        for ch in previous_chapters
    ])
    
    # Prepare context from previous scenes
    previous_scenes_context = "\n\n".join([
        f"Scene {s.scene_number}: {s.title}\nCharacters: {', '.join(c.name for c in s.characters)}"
        for s in previous_scenes
    ])
    
    # Get current scene's characters
    current_characters = ", ".join(c.name for c in scene.characters)
    
    # Prepare the messages for GPT
    messages = [
        {
            "role": "system",
            "content": """You are a creative writing assistant specialized in creating scene outlines.
            Based on the previous chapters, previous scenes, and the current scene's characters,
            create a structured outline for the scene broken down into subscenes.
            
            Each subscene should be concise and focused on a specific moment or event.
            The content should be minimal and outline the key points rather than detailed narrative.
            
            Format your response as a JSON array of subscenes, where each subscene has:
            - title: A brief, descriptive title for the subscene
            - content: A minimal outline of what happens in this subscene
            
            Keep the content high-level and focused on plot points rather than detailed descriptions.
            
            Example format:
            [
                {
                    "title": "Initial Meeting",
                    "content": "Brief description of what happens"
                },
                {
                    "title": "Rising Tension",
                    "content": "Brief description of what happens"
                }
            ]"""
        },
        {
            "role": "user",
            "content": f"""Previous Chapters:\n{previous_chapters_context}\n\n
            Previous Scenes in Current Chapter:\n{previous_scenes_context}\n\n
            Current Scene Information:
            - Scene Number: {scene.scene_number}
            - Title: {scene.title}
            - Characters: {current_characters}\n\n
            User's Request: {request.user_prompt}\n\n
            Please provide a structured outline for this scene:"""
        }
    ]

    try:
        response = client.chat.completions.create(
            model=OPENAI_MODEL,
            messages=messages,
            temperature=0.7,
            max_tokens=1000
        )
        
        # Parse the response
        try:
            # Extract the JSON array from the response
            response_text = response.choices[0].message.content
            # Clean up the response text to ensure it's valid JSON
            response_text = response_text.strip()
            if response_text.startswith('```json'):
                response_text = response_text[7:]
            if response_text.endswith('```'):
                response_text = response_text[:-3]
            response_text = response_text.strip()
            
            # Parse the JSON into our response model
            subscenes_data = json.loads(response_text)
            return SceneCompletionResponse(subscenes=subscenes_data)
            
        except json.JSONDecodeError as e:
            raise HTTPException(
                status_code=500,
                detail=f"Failed to parse the AI response into proper format: {str(e)}"
            )
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) 
    

