from sqlalchemy.orm import Session
from ..models.models import Chapter, Book, Scene, Character
from ..schemas.schemas import (
    ChapterCreate, ChapterUpdate, ChapterResponse, OutlineRequest,
    ChapterOutlineResponse, ChapterGenerateRequest, SceneOutlineResponse
)
from ..services.ai_service import get_openai_client
from ..config import OPENAI_MODEL
from fastapi import HTTPException
import json
from typing import List
from fastapi.responses import StreamingResponse

def create_chapter(db: Session, book_id: int, chapter: ChapterCreate):
    # Check if book exists
    book = db.query(Book).filter(Book.id == book_id).first()
    if not book:
        return None
    
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
        return None
    
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

def update_chapter(db: Session, book_id: int, chapter_id: int, chapter_update: ChapterUpdate):
    chapter = db.query(Chapter).filter(
        Chapter.id == chapter_id,
        Chapter.book_id == book_id
    ).first()
    if not chapter:
        return None
    
    chapter.content = chapter_update.content
    db.commit()
    db.refresh(chapter)
    return chapter

def get_chapter(db: Session, book_id: int, chapter_id: int):
    return db.query(Chapter).filter(
        Chapter.id == chapter_id,
        Chapter.book_id == book_id
    ).first()

async def generate_chapter_outline(db: Session, book_id: int, chapter_id: int, user_prompt: str) -> List[SceneOutlineResponse]:
    try:
        # Initialize OpenAI client
        client = get_openai_client()
        
        # Get the chapter
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
                Based on the previous chapters and the available characters,
                create a structured outline for the chapter broken down into multiple scenes.
                
                For character descriptions, use this exact format with HTML tags:
                <h3>Basic Traits:</h3>
                <p>Age: [age]<br>
                Appearance: [physical description]<br>
                Profession/Background: [career and background]</p>

                <h3>Personality:</h3>
                <p>Key Traits: [list of traits]<br>
                Moral Code: [ethical framework]<br>
                Motivations: [what drives the character]</p>

                <h3>Character Development:</h3>
                <p>Internal Struggles: [personal conflicts]<br>
                External Conflicts: [external challenges]<br>
                Growth Arc: [character's journey]</p>
                
                Your response must be a JSON object with this structure:
                {
                    "scenes": [
                        {
                            "scene_number": 1,
                            "title": "Scene title",
                            "characters": [
                                {
                                    "name": "Character Name",
                                    "description": "Character description with HTML tags as shown above"
                                }
                            ],
                            "content": "Scene content"
                        }
                    ]
                }"""
            },
            {
                "role": "user",
                "content": f"""Previous Chapters:
{previous_chapters_context}

Available Characters:
{characters_context}

Current Chapter Information:
- Chapter Number: {chapter.chapter_no}
- Title: {chapter.title}

User's Request: {user_prompt}

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
                response_text = response.choices[0].message.content.strip()
                scenes_data = json.loads(response_text)
                
                # Basic validation
                if not isinstance(scenes_data, dict) or "scenes" not in scenes_data:
                    raise HTTPException(status_code=500, detail="Invalid response format")
                
                # Store scenes in the database and create response objects
                scene_responses = []
                
                # Delete existing scenes
                db.query(Scene).filter(Scene.chapter_id == chapter_id).delete()
                db.flush()
                
                # Process scenes
                for idx, scene in enumerate(scenes_data["scenes"]):
                    # Create scene
                    db_scene = Scene(
                        chapter_id=chapter_id,
                        scene_number=idx + 1,
                        title=scene.get("title", f"Scene {idx + 1}"),
                        content=scene.get("content", "")
                    )
                    db.add(db_scene)
                    db.flush()
                    
                    # Process characters
                    scene_characters = []
                    for char in scene.get("characters", []):
                        if isinstance(char, dict) and "name" in char:
                            character = db.query(Character).filter(
                                Character.name == char["name"],
                                Character.book_id == book_id
                            ).first()
                            
                            if not character:
                                character = Character(
                                    name=char["name"],
                                    description=char.get("description", ""),
                                    book_id=book_id
                                )
                                db.add(character)
                                db.flush()
                            
                            db_scene.characters.append(character)
                            scene_characters.append(character)
                    
                    # Create response
                    scene_responses.append(SceneOutlineResponse(
                        scene_number=db_scene.scene_number,
                        title=db_scene.title,
                        characters=[{
                            "name": c.name,
                            "description": c.description
                        } for c in scene_characters],
                        content=db_scene.content
                    ))
                
                db.commit()
                return scene_responses
                
            except json.JSONDecodeError as e:
                raise HTTPException(status_code=500, detail="Invalid JSON response")
            except Exception as e:
                raise HTTPException(status_code=500, detail=str(e))
                
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

async def generate_chapter_content(db: Session, book_id: int, chapter_id: int, request: ChapterGenerateRequest):
    # Get the book and chapter
    book = db.query(Book).filter(Book.id == book_id).first()
    if not book:
        return None
    
    chapter = db.query(Chapter).filter(
        Chapter.id == chapter_id,
        Chapter.book_id == book_id
    ).first()
    if not chapter:
        return None
    
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
            raise Exception(f"Failed to process the generated chapter: {str(e)}")
            
    except Exception as e:
        raise Exception(str(e))

async def stream_chapter_content(db: Session, book_id: int, chapter_id: int, request: ChapterGenerateRequest):
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
            
            If scenes are provided:
            1. Follow the scene structure exactly as provided
            2. Each scene should be a distinct section in the chapter
            3. Maintain the characters and their roles as specified in each scene
            4. Expand on the scene content while staying true to its core elements
            5. Ensure smooth transitions between scenes
            
            If no scenes are provided:
            1. Create a well-structured chapter with natural flow
            2. Include vivid descriptions and engaging dialogue
            3. Advance the plot while maintaining suspense
            4. End in a way that hooks readers for the next chapter
            
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
        client = get_openai_client()
        stream = client.chat.completions.create(
            model=OPENAI_MODEL,
            messages=messages,
            temperature=0.7,
            stream=True  # Enable streaming
        )
        
        async def generate():
            full_response = ""
            title = None
            
            try:
                for chunk in stream:
                    if chunk.choices[0].delta.content:
                        content = chunk.choices[0].delta.content
                        full_response += content
                        
                        # Try to extract title from accumulated response if not found yet
                        if not title and "TITLE:" in full_response:
                            title_line = next((line for line in full_response.split('\n') if "TITLE:" in line), None)
                            if title_line:
                                title = title_line.replace("TITLE:", "").strip()
                        
                        # Format as SSE
                        yield f"data: {content}\n\n"
                
                # After streaming is complete, update the chapter in the database
                if not title:
                    # If no title found in format, use first non-empty line or default
                    lines = full_response.split('\n')
                    title = next((line.strip() for line in lines if line.strip()), f"Chapter {chapter.chapter_no}")
                
                chapter.title = title
                chapter.content = full_response
                db.commit()
                
                # Send completion signal
                yield "data: [DONE]\n\n"
                
            except Exception as e:
                # Send error and completion signal
                yield f"data: error: {str(e)}\n\n"
                yield "data: [DONE]\n\n"
                raise HTTPException(status_code=500, detail=str(e))

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