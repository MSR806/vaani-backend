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

class CharacterInScene(BaseModel):
    name: str
    description: str

class SceneCreate(BaseModel):
    scene_number: int
    title: str
    chapter_id: int
    content: str
    characters: List[CharacterInScene]

class SceneUpdate(BaseModel):
    scene_number: Optional[int] = None
    title: Optional[str] = None
    content: Optional[str] = None
    characters: Optional[List[CharacterInScene]] = None

class SubScene(BaseModel):
    title: str
    content: str

class SceneCompletionRequest(BaseModel):
    outline: str

class SceneCompletionResponse(BaseModel):
    subscenes: List[SubScene]

class CharacterResponse(BaseModel):
    id: int
    name: str
    description: str
    book_id: int

    class Config:
        from_attributes = True

class SceneResponse(BaseModel):
    id: int
    scene_number: int
    title: str
    chapter_id: int
    content: str
    characters: List[CharacterResponse]

    class Config:
        from_attributes = True

class SceneOutlineRequest(BaseModel):
    user_prompt: str

class SceneOutlineResponse(BaseModel):
    scene_number: int
    title: str
    characters: List[CharacterInScene]
    subscenes: List[SubScene]

class ChapterOutlineResponse(BaseModel):
    scenes: List[SceneOutlineResponse]

class ChapterGenerateRequest(BaseModel):
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
    
    # Get the highest chapter number for this book
    max_chapter = db.query(Chapter).filter(
        Chapter.book_id == book_id
    ).order_by(Chapter.chapter_no.desc()).first()
    
    # Set the next chapter number
    next_chapter_no = 1 if not max_chapter else max_chapter.chapter_no + 1
    
    # Check if a chapter with this number already exists in the book
    existing_chapter = db.query(Chapter).filter(
        Chapter.book_id == book_id,
        Chapter.chapter_no == next_chapter_no
    ).first()
    
    if existing_chapter:
        raise HTTPException(
            status_code=400,
            detail=f"Chapter {next_chapter_no} already exists in this book"
        )
    
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
    
    # Get or create characters
    scene_characters = []
    for char_data in scene.characters:
        # Check if character with same name exists in the book
        existing_char = db.query(Character).filter(
            Character.name == char_data.name,
            Character.book_id == chapter.book_id  # Use the book_id from the chapter
        ).first()
        
        if existing_char:
            scene_characters.append(existing_char)
        else:
            # Create new character with the correct book_id
            new_char = Character(
                name=char_data.name,
                description=char_data.description,
                book_id=chapter.book_id  # Use the book_id from the chapter
            )
            db.add(new_char)
            db.flush()  # Flush to get the new character's ID
            scene_characters.append(new_char)
    
    # Create the scene
    db_scene = Scene(
        scene_number=scene.scene_number,
        title=scene.title,
        chapter_id=scene.chapter_id,
        content=scene.content,
        characters=scene_characters
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
    if scene_update.content is not None:
        scene.content = scene_update.content
    if scene_update.characters is not None:
        # Get or create characters
        scene_characters = []
        for char_data in scene_update.characters:
            # Check if character with same name exists in the book
            existing_char = db.query(Character).filter(
                Character.name == char_data.name,
                Character.book_id == scene.chapter.book_id  # Use the book_id from the chapter
            ).first()
            
            if existing_char:
                scene_characters.append(existing_char)
            else:
                # Create new character with the correct book_id
                new_char = Character(
                    name=char_data.name,
                    description=char_data.description,
                    book_id=scene.chapter.book_id  # Use the book_id from the chapter
                )
                db.add(new_char)
                db.flush()  # Flush to get the new character's ID
                scene_characters.append(new_char)
        
        scene.characters = scene_characters
    
    db.commit()
    db.refresh(scene)
    return scene

@router.get("/scenes", response_model=List[SceneResponse])
def get_scenes(chapter_id: Optional[int] = None, db: Session = Depends(get_db)):
    query = db.query(Scene)
    if chapter_id is not None:
        query = query.filter(Scene.chapter_id == chapter_id)
    return query.all()

@router.post("/scenes/{scene_id}/outline-generation", response_model=SceneOutlineResponse)
async def generate_scene_outline(scene_id: int, request: SceneOutlineRequest, db: Session = Depends(get_db)):
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
    
    # Get current scene's characters with their descriptions
    current_characters = [{"name": c.name, "description": c.description} for c in scene.characters]
    
    # Prepare the messages for GPT
    messages = [
        {
            "role": "system",
            "content": """You are a creative writing assistant specialized in creating scene outlines.
            Based on the previous chapters, previous scenes, and the current scene's characters,
            create a structured outline for the scene broken down into subscenes.
            
            Each subscene should be concise and focused on a specific moment or event.
            The content should be minimal and outline the key points rather than detailed narrative.
            
            Your response must be a valid JSON object with the following structure:
            {
                "scene_number": 1,
                "title": "Scene title",
                "characters": [
                    {
                        "name": "Character Name",
                        "description": "Character's description and role in the scene"
                    }
                ],
                "subscenes": [
                    {
                        "title": "Subscene title",
                        "content": "Brief description of what happens"
                    }
                ]
            }
            
            Keep the content high-level and focused on plot points rather than detailed descriptions.
            Ensure your response strictly follows this JSON structure.
            Include character descriptions that reflect their role and significance in this specific scene."""
        },
        {
            "role": "user",
            "content": f"""Previous Chapters:
{previous_chapters_context}

Previous Scenes in Current Chapter:
{previous_scenes_context}

Current Scene Information:
- Scene Number: {scene.scene_number}
- Title: {scene.title}
- Characters: {', '.join(c['name'] for c in current_characters)}

User's Request: {request.user_prompt}

Please provide a structured outline for this scene:"""
        }
    ]

    try:
        response = client.chat.completions.create(
            model=OPENAI_MODEL,
            messages=messages,
            temperature=0.7,
            max_tokens=2000,
            response_format={"type": "json_object"}
        )
        
        # Parse the response
        try:
            # Extract the JSON object from the response
            response_text = response.choices[0].message.content
            # Clean up the response text to ensure it's valid JSON
            response_text = response_text.strip()
            
            # Parse the JSON into our response model
            scene_data = json.loads(response_text)
            
            # Add the scene number from the database
            scene_data["scene_number"] = scene.scene_number
            
            # Validate the response structure
            if not isinstance(scene_data, dict):
                raise ValueError("Response must be a JSON object")
            
            if "title" not in scene_data:
                raise ValueError("Response must have a title")
            
            if not isinstance(scene_data["title"], str) or not scene_data["title"].strip():
                raise ValueError("Title must be a non-empty string")
            
            if "characters" not in scene_data:
                raise ValueError("Response must have a characters array")
            
            if not isinstance(scene_data["characters"], list):
                raise ValueError("Characters must be an array")
            
            # Validate each character
            for char_idx, char in enumerate(scene_data["characters"]):
                if not isinstance(char, dict):
                    raise ValueError(f"Character {char_idx} must be an object")
                
                if "name" not in char:
                    raise ValueError(f"Character {char_idx} must have a name")
                
                if not isinstance(char["name"], str) or not char["name"].strip():
                    raise ValueError(f"Character {char_idx} name must be a non-empty string")
                
                if "description" not in char:
                    raise ValueError(f"Character {char_idx} must have a description")
                
                if not isinstance(char["description"], str) or not char["description"].strip():
                    raise ValueError(f"Character {char_idx} description must be a non-empty string")
            
            if "subscenes" not in scene_data:
                raise ValueError("Response must have subscenes")
            
            if not isinstance(scene_data["subscenes"], list):
                raise ValueError("Subscenes must be an array")
            
            if not scene_data["subscenes"]:
                raise ValueError("Response must have at least one subscene")
            
            # Validate each subscene
            for subscene_idx, subscene in enumerate(scene_data["subscenes"]):
                if not isinstance(subscene, dict):
                    raise ValueError(f"Subscene {subscene_idx} must be an object")
                
                if "title" not in subscene:
                    raise ValueError(f"Subscene {subscene_idx} must have a title")
                
                if not isinstance(subscene["title"], str) or not subscene["title"].strip():
                    raise ValueError(f"Subscene {subscene_idx} title must be a non-empty string")
                
                if "content" not in subscene:
                    raise ValueError(f"Subscene {subscene_idx} must have content")
                
                if not isinstance(subscene["content"], str) or not subscene["content"].strip():
                    raise ValueError(f"Subscene {subscene_idx} content must be a non-empty string")
            
            return SceneOutlineResponse(**scene_data)
            
        except json.JSONDecodeError as e:
            raise HTTPException(
                status_code=500,
                detail=f"Failed to parse the AI response into proper format: {str(e)}"
            )
        except ValueError as e:
            # If the response doesn't match our schema, try to fix it with another API call
            retry_messages = messages + [
                {
                    "role": "assistant",
                    "content": response_text
                },
                {
                    "role": "user",
                    "content": f"""The previous response did not match the required format. Please provide a response in exactly this format:
                    {{
                        "scene_number": {scene.scene_number},
                        "title": "Scene Title",
                        "characters": [
                            {{
                                "name": "Character Name",
                                "description": "Character's description and role in the scene"
                            }}
                        ],
                        "subscenes": [
                            {{
                                "title": "Subscene Title",
                                "content": "Description of what happens"
                            }}
                        ]
                    }}
                    
                    Available characters: {', '.join(c['name'] for c in current_characters)}"""
                }
            ]
            
            try:
                retry_response = client.chat.completions.create(
                    model=OPENAI_MODEL,
                    messages=retry_messages,
                    temperature=0.7,
                    max_tokens=2000,
                    response_format={"type": "json_object"}
                )
                
                retry_text = retry_response.choices[0].message.content.strip()
                retry_data = json.loads(retry_text)
                
                # Add the scene number from the database
                retry_data["scene_number"] = scene.scene_number
                
                # Validate the retry response with the same checks
                if not isinstance(retry_data, dict) or "title" not in retry_data or "characters" not in retry_data or "subscenes" not in retry_data:
                    raise HTTPException(
                        status_code=500,
                        detail=f"Failed to generate a properly structured response after retry: {str(e)}"
                    )
                
                return SceneOutlineResponse(**retry_data)
                
            except Exception as retry_error:
                raise HTTPException(
                    status_code=500,
                    detail=f"Failed to generate a valid response even after retry: {str(retry_error)}"
                )
        except Exception as e:
            raise HTTPException(
                status_code=500,
                detail=f"Error processing the response: {str(e)}"
            )
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/scenes/{scene_id}/completion")
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
        f"Scene {s.scene_number}: {s.title}\nCharacters: {', '.join(c.name for c in s.characters)}\n{s.content}"
        for s in previous_scenes
    ])
    
    # Get current scene's characters
    current_characters = ", ".join(c.name for c in scene.characters)
    
    # Prepare the messages for GPT
    messages = [
        {
            "role": "system",
            "content": """You are a creative writing assistant specialized in writing detailed scenes.
            Based on the previous chapters, previous scenes, and the provided outline,
            write a complete, engaging scene that maintains consistency with the story's style and narrative.
            
            Your scene should:
            1. Follow the provided outline structure
            2. Include vivid descriptions and engaging dialogue
            3. Maintain consistent character voices and personalities
            4. Create a natural flow between different moments
            5. Include sensory details and emotional depth
            6. End in a way that maintains narrative momentum
            
            Write in a natural, flowing style that brings the scene to life."""
        },
        {
            "role": "user",
            "content": f"""Previous Chapters:
{previous_chapters_context}

Previous Scenes in Current Chapter:
{previous_scenes_context}

Current Scene Information:
- Scene Number: {scene.scene_number}
- Title: {scene.title}
- Characters: {current_characters}

Scene Outline:
{request.outline}

Please write the complete scene:"""
        }
    ]

    try:
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
                    if hasattr(chunk.choices[0].delta, 'content') and chunk.choices[0].delta.content:
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

@router.post("/books/{book_id}/chapters/outline", response_model=ChapterOutlineResponse)
async def generate_chapter_outline(book_id: int, request: OutlineRequest, db: Session = Depends(get_db)):
    # Get the book and its latest chapter
    book = db.query(Book).filter(Book.id == book_id).first()
    if not book:
        raise HTTPException(status_code=404, detail="Book not found")
    
    # Get the latest chapter
    chapter = db.query(Chapter).filter(
        Chapter.book_id == book_id
    ).order_by(Chapter.chapter_no.desc()).first()
    
    if not chapter:
        raise HTTPException(status_code=404, detail="No chapters found in this book")
    
    # Get all previous chapters in order
    previous_chapters = db.query(Chapter).filter(
        Chapter.book_id == book_id,
        Chapter.chapter_no < chapter.chapter_no
    ).order_by(Chapter.chapter_no).all()
    
    # Get all scenes from previous chapters
    previous_scenes = []
    for prev_chapter in previous_chapters:
        scenes = db.query(Scene).filter(
            Scene.chapter_id == prev_chapter.id
        ).order_by(Scene.scene_number).all()
        previous_scenes.extend(scenes)
    
    # Get all characters from the book
    characters = db.query(Character).filter(
        Character.book_id == book_id
    ).all()
    
    # Prepare context from previous chapters
    previous_chapters_context = "\n\n".join([
        f"Chapter {ch.chapter_no}: {ch.title}\n{ch.content}"
        for ch in previous_chapters
    ])
    
    # Prepare context from previous scenes
    previous_scenes_context = "\n\n".join([
        f"Scene {s.scene_number} from Chapter {s.chapter.chapter_no}: {s.title}\n"
        f"Characters: {', '.join(c.name for c in s.characters)}\n"
        f"Content: {s.content}"
        for s in previous_scenes
    ])
    
    # Get all characters in the book
    characters_context = "\n".join([
        f"- {c.name}: {c.description}"
        for c in characters
    ])
    
    # Prepare the messages for GPT
    messages = [
        {
            "role": "system",
            "content": """You are a creative writing assistant specialized in creating chapter outlines.
            Based on the previous chapters, previous scenes, and the available characters,
            create a structured outline for the chapter broken down into multiple scenes.
            
            Each scene should be concise and focused on specific events or character interactions.
            The content should be minimal and outline the key points rather than detailed narrative.
            
            Your response must be a valid JSON object with the following structure:
            {
                "scenes": [
                    {
                        "scene_number": 1,
                        "title": "Scene title",
                        "characters": [
                            {
                                "name": "Character Name",
                                "description": "Character's description and role in the scene"
                            }
                        ],
                        "subscenes": [
                            {
                                "title": "Subscene title",
                                "content": "Brief description of what happens"
                            }
                        ]
                    }
                ]
            }
            
            Keep the content high-level and focused on plot points rather than detailed descriptions.
            Ensure your response strictly follows this JSON structure.
            Include relevant characters for each scene from the available characters list.
            Each scene must have a scene_number field starting from 1.
            Each character must be an object with name and description fields."""
        },
        {
            "role": "user",
            "content": f"""Previous Chapters:
{previous_chapters_context}

Previous Scenes:
{previous_scenes_context}

Available Characters:
{characters_context}

Current Chapter Information:
- Chapter Number: {chapter.chapter_no}
- Title: {chapter.title}

User's Request: {request.user_prompt}

Please provide a structured outline for this chapter:"""
        }
    ]

    try:
        response = client.chat.completions.create(
            model=OPENAI_MODEL,
            messages=messages,
            temperature=0.7,
            max_tokens=2000,
            response_format={"type": "json_object"}
        )
        
        # Parse the response
        try:
            # Extract the JSON object from the response
            response_text = response.choices[0].message.content
            # Clean up the response text to ensure it's valid JSON
            response_text = response_text.strip()
            
            # Parse the JSON
            scenes_data = json.loads(response_text)
            
            # Validate the response structure
            if not isinstance(scenes_data, dict):
                raise ValueError("Response must be a JSON object")
            
            if "scenes" not in scenes_data:
                raise ValueError("Response must contain a 'scenes' array")
            
            if not isinstance(scenes_data["scenes"], list):
                raise ValueError("'scenes' must be an array")
            
            # Get all available character names for validation
            available_characters = {c.name for c in characters}
            
            # Validate each scene and subscene
            for scene_idx, scene in enumerate(scenes_data["scenes"]):
                if not isinstance(scene, dict):
                    raise ValueError(f"Scene {scene_idx} must be an object")
                
                if "title" not in scene:
                    raise ValueError(f"Scene {scene_idx} must have a title")
                
                if not isinstance(scene["title"], str) or not scene["title"].strip():
                    raise ValueError(f"Scene {scene_idx} must have a non-empty title")
                
                if "characters" not in scene:
                    raise ValueError(f"Scene {scene_idx} must have a characters array")
                
                if not isinstance(scene["characters"], list):
                    raise ValueError(f"Scene {scene_idx} characters must be an array")
                
                # Validate each character exists in our available characters
                for char_idx, char_name in enumerate(scene["characters"]):
                    if not isinstance(char_name, str) or not char_name.strip():
                        raise ValueError(f"Character {char_idx} in scene {scene_idx} must be a non-empty string")
                    if char_name not in available_characters:
                        raise ValueError(f"Character '{char_name}' in scene {scene_idx} is not in the available characters list")
                
                if "subscenes" not in scene:
                    raise ValueError(f"Scene {scene_idx} must have subscenes")
                
                if not isinstance(scene["subscenes"], list):
                    raise ValueError(f"Scene {scene_idx} subscenes must be an array")
                
                if not scene["subscenes"]:
                    raise ValueError(f"Scene {scene_idx} must have at least one subscene")
                
                for subscene_idx, subscene in enumerate(scene["subscenes"]):
                    if not isinstance(subscene, dict):
                        raise ValueError(f"Subscene {subscene_idx} in scene {scene_idx} must be an object")
                    
                    if "title" not in subscene:
                        raise ValueError(f"Subscene {subscene_idx} in scene {scene_idx} must have a title")
                    
                    if not isinstance(subscene["title"], str) or not subscene["title"].strip():
                        raise ValueError(f"Subscene {subscene_idx} in scene {scene_idx} must have a non-empty title")
                    
                    if "content" not in subscene:
                        raise ValueError(f"Subscene {subscene_idx} in scene {scene_idx} must have content")
                    
                    if not isinstance(subscene["content"], str) or not subscene["content"].strip():
                        raise ValueError(f"Subscene {subscene_idx} in scene {scene_idx} must have non-empty content")
            
            # If validation passes, create the response model
            return ChapterOutlineResponse(**scenes_data)
            
        except json.JSONDecodeError as e:
            raise HTTPException(
                status_code=500,
                detail=f"Failed to parse the AI response into proper JSON format: {str(e)}"
            )
        except ValueError as e:
            # If the response doesn't match our schema, try to fix it with another API call
            retry_messages = messages + [
                {
                    "role": "assistant",
                    "content": response_text
                },
                {
                    "role": "user",
                    "content": f"""The previous response did not match the required format. Please provide a response in exactly this format:
                    {{
                        "scenes": [
                            {{
                                "scene_number": 1,
                                "title": "Scene Title",
                                "characters": [
                                    {{
                                        "name": "Character Name",
                                        "description": "Character's description and role in the scene"
                                    }}
                                ],
                                "subscenes": [
                                    {{
                                        "title": "Subscene Title",
                                        "content": "Description of what happens"
                                    }}
                                ]
                            }}
                        ]
                    }}
                    
                    Available characters: {', '.join(available_characters)}"""
                }
            ]
            
            try:
                retry_response = client.chat.completions.create(
                    model=OPENAI_MODEL,
                    messages=retry_messages,
                    temperature=0.7,
                    max_tokens=2000,
                    response_format={"type": "json_object"}
                )
                
                retry_text = retry_response.choices[0].message.content.strip()
                retry_data = json.loads(retry_text)
                
                # Validate the retry response with the same checks
                if not isinstance(retry_data, dict) or "scenes" not in retry_data:
                    raise HTTPException(
                        status_code=500,
                        detail=f"Failed to generate a properly structured response after retry: {str(e)}"
                    )
                
                return ChapterOutlineResponse(**retry_data)
                
            except Exception as retry_error:
                raise HTTPException(
                    status_code=500,
                    detail=f"Failed to generate a valid response even after retry: {str(retry_error)}"
                )
        except Exception as e:
            raise HTTPException(
                status_code=500,
                detail=f"Error processing the response: {str(e)}"
            )
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/books/{book_id}/chapters/{chapter_id}/generate", response_model=ChapterResponse)
async def generate_chapter_content(book_id: int, chapter_id: int, request: ChapterGenerateRequest, db: Session = Depends(get_db)):
    # Get the book and chapter
    book = db.query(Book).filter(Book.id == book_id).first()
    if not book:
        raise HTTPException(status_code=404, detail="Book not found")
    
    chapter = db.query(Chapter).filter(
        Chapter.id == chapter_id,
        Chapter.book_id == book_id
    ).first()
    if not chapter:
        raise HTTPException(status_code=404, detail="Chapter not found")
    
    # Get all previous chapters in order
    previous_chapters = db.query(Chapter).filter(
        Chapter.book_id == book_id,
        Chapter.chapter_no < chapter.chapter_no
    ).order_by(Chapter.chapter_no).all()
    
    # Get all scenes for the current chapter
    scenes = db.query(Scene).filter(
        Scene.chapter_id == chapter_id
    ).order_by(Scene.scene_number).all()
    
    # Prepare context from previous chapters
    previous_chapters_context = "\n\n".join([
        f"Chapter {ch.chapter_no}: {ch.title}\n{ch.content}"
        for ch in previous_chapters
    ])
    
    # Prepare context from scenes if they exist
    scenes_context = ""
    if scenes:
        scenes_context = "\n\n".join([
            f"Scene {s.scene_number}: {s.title}\n"
            f"Characters: {', '.join(c.name for c in s.characters)}\n"
            f"Content: {s.content}"
            for s in scenes
        ])
    
    # Prepare the messages for GPT
    messages = [
        {
            "role": "system",
            "content": """You are a creative writing assistant specialized in writing novel chapters.
            Based on the previous chapters and the provided context (including scenes if available),
            write a complete, engaging chapter that maintains consistency with the story's style and narrative.
            
            Your chapter should:
            1. Follow any provided scene structure if available
            2. Be well-structured with natural flow between scenes
            3. Maintain consistent character voices and personalities
            4. Include vivid descriptions and engaging dialogue
            5. Advance the plot while maintaining suspense
            6. End in a way that hooks readers for the next chapter
            
            Start your response with a suitable chapter title in the format: TITLE: Your Chapter Title
            Then continue with the chapter content."""
        },
        {
            "role": "user",
            "content": f"""Previous Chapters:
{previous_chapters_context}

{'Scenes for Current Chapter:' + scenes_context if scenes_context else ''}

Current Chapter Information:
- Chapter Number: {chapter.chapter_no}
- Title: {chapter.title}

User's Request: {request.user_prompt}

Please write the complete chapter:"""
        }
    ]

    try:
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
                title = f"Chapter {chapter.chapter_no}"
            
            # Join the remaining lines for content
            content = '\n'.join(lines[content_start:]).strip()
            
            # Update the chapter in the database
            chapter.title = title
            chapter.content = content
            db.commit()
            db.refresh(chapter)
            
            return ChapterResponse(
                id=chapter.id,
                book_id=book_id,
                title=title,
                chapter_no=chapter.chapter_no,
                content=content
            )
            
        except Exception as e:
            raise HTTPException(
                status_code=500,
                detail=f"Failed to process the generated chapter: {str(e)}"
            )
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) 
    

