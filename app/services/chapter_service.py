from sqlalchemy.orm import Session
from ..models.models import Chapter, Book, Scene, Character
from ..schemas.schemas import (
    ChapterCreate, ChapterUpdate, ChapterResponse, OutlineRequest,
    ChapterOutlineResponse, ChapterGenerateRequest
)
from ..services.ai_service import get_openai_client
from ..config import OPENAI_MODEL
import json

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

async def generate_chapter_outline(db: Session, book_id: int, request: OutlineRequest):
    # Get the book and its latest chapter
    book = db.query(Book).filter(Book.id == book_id).first()
    if not book:
        return None
    
    # Get the latest chapter
    chapter = db.query(Chapter).filter(
        Chapter.book_id == book_id
    ).order_by(Chapter.chapter_no.desc()).first()
    
    if not chapter:
        return None
    
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
            
            Format your response as HTML with the following rules:
            1. Each section title should be wrapped in <h3> tags
            2. The main content should be in <p> tags
            3. Use <br> tags for line breaks between paragraphs
            4. Do not include any other HTML tags
            5. Keep the HTML simple and clean
            
            Example format:
            <h3>Section Title</h3>
            <p>Content goes here...</p>
            <br>
            <h3>Next Section</h3>
            <p>More content...</p>
            
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
                        "content": "HTML formatted content with section titles and content"
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
        client = get_openai_client()
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
            
            # Validate each scene
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
                
                if "content" not in scene:
                    raise ValueError(f"Scene {scene_idx} must have content")
                
                if not isinstance(scene["content"], str) or not scene["content"].strip():
                    raise ValueError(f"Scene {scene_idx} must have non-empty content")
            
            # If validation passes, create the response model
            return ChapterOutlineResponse(**scenes_data)
            
        except json.JSONDecodeError as e:
            raise Exception(f"Failed to parse the AI response into proper JSON format: {str(e)}")
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
                                "content": "HTML formatted content with section titles and content"
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
                    raise Exception(f"Failed to generate a properly structured response after retry: {str(e)}")
                
                return ChapterOutlineResponse(**retry_data)
                
            except Exception as retry_error:
                raise Exception(f"Failed to generate a valid response even after retry: {str(retry_error)}")
        except Exception as e:
            raise Exception(f"Error processing the response: {str(e)}")
            
    except Exception as e:
        raise Exception(str(e))

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