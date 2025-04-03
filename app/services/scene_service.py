from sqlalchemy.orm import Session, joinedload
from ..models.models import Scene, Chapter, Character
from ..schemas.schemas import (
    SceneCreate, SceneUpdate, SceneResponse, SceneOutlineRequest,
    SceneOutlineResponse, SceneCompletionRequest, SceneCompletionResponse
)
from ..services.ai_service import get_openai_client
from ..config import OPENAI_MODEL
import json

def create_scene(db: Session, scene: SceneCreate):
    # Check if chapter exists
    chapter = db.query(Chapter).filter(Chapter.id == scene.chapter_id).first()
    if not chapter:
        return None
    
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

def update_scene(db: Session, scene_id: int, scene_update: SceneUpdate):
    scene = db.query(Scene).filter(Scene.id == scene_id).first()
    if not scene:
        return None
    
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

def get_scene(db: Session, scene_id: int):
    return db.query(Scene).filter(Scene.id == scene_id).first()

def get_scenes(db: Session, chapter_id: int = None):
    query = db.query(Scene).options(joinedload(Scene.characters))
    if chapter_id is not None:
        query = query.filter(Scene.chapter_id == chapter_id)
    return query.all()

async def generate_scene_outline(db: Session, scene_id: int, request: SceneOutlineRequest):
    # Get the scene and its chapter
    scene = db.query(Scene).filter(Scene.id == scene_id).first()
    if not scene:
        return None
    
    chapter = db.query(Chapter).filter(Chapter.id == scene.chapter_id).first()
    if not chapter:
        return None
    
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
            create a structured outline for the scene.
            
            Format your response as HTML with the following rules:
            1. Each section title should be wrapped in <b> tags
            2. The main content should be in <p> tags
            3. Use <br> tags for line breaks between paragraphs
            4. Do not include any other HTML tags
            5. Keep the HTML simple and clean
            
            Example format:
            <b>Section Title</b>
            <p>Content goes here...</p>
            <br>
            <b>Next Section</b>
            <p>More content...</p>
            
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
                "content": "HTML formatted content with section titles and content"
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
            
            if "content" not in scene_data:
                raise ValueError("Response must have content")
            
            if not isinstance(scene_data["content"], str) or not scene_data["content"].strip():
                raise ValueError("Content must be a non-empty string")
            
            return SceneOutlineResponse(**scene_data)
            
        except json.JSONDecodeError as e:
            raise Exception(f"Failed to parse the AI response into proper format: {str(e)}")
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
                        "content": "HTML formatted content with section titles and content"
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
                if not isinstance(retry_data, dict) or "title" not in retry_data or "characters" not in retry_data or "content" not in retry_data:
                    raise Exception(f"Failed to generate a properly structured response after retry: {str(e)}")
                
                return SceneOutlineResponse(**retry_data)
                
            except Exception as retry_error:
                raise Exception(f"Failed to generate a valid response even after retry: {str(retry_error)}")
        except Exception as e:
            raise Exception(f"Error processing the response: {str(e)}")
            
    except Exception as e:
        raise Exception(str(e))

async def generate_scene_content(db: Session, scene_id: int, request: SceneCompletionRequest):
    # Get the scene and its chapter
    scene = db.query(Scene).filter(Scene.id == scene_id).first()
    if not scene:
        return None
    
    chapter = db.query(Chapter).filter(Chapter.id == scene.chapter_id).first()
    if not chapter:
        return None
    
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
            <p>More content...</p>"""
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

Please write the complete scene in HTML format:"""
        }
    ]

    try:
        client = get_openai_client()
        response = client.chat.completions.create(
            model=OPENAI_MODEL,
            messages=messages,
            temperature=0.7
        )
        
        # Get the generated content
        content = response.choices[0].message.content.strip()
        
        # Update the scene in the database
        scene.content = content
        db.commit()
        db.refresh(scene)
        
        return SceneCompletionResponse(content=content)
        
    except Exception as e:
        raise Exception(str(e)) 