from sqlalchemy.orm import Session, joinedload
from ..models.models import Scene, Chapter
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
    
    # Create the scene
    db_scene = Scene(
        scene_number=scene.scene_number,
        title=scene.title,
        chapter_id=scene.chapter_id,
        content=scene.content
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
    
    db.commit()
    db.refresh(scene)
    return scene

def get_scene(db: Session, scene_id: int):
    return db.query(Scene).filter(Scene.id == scene_id).first()

def get_scenes(db: Session, chapter_id: int = None):
    query = db.query(Scene)
    if chapter_id is not None:
        query = query.filter(Scene.chapter_id == chapter_id)
    return query.all()

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