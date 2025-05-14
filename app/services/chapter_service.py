from app.prompts.scenes import SCENE_GENERATION_SYSTEM_PROMPT_V1
from app.prompts.chapters import CHAPTER_GENERATION_FROM_SCENE_SYSTEM_PROMPT_V1
from app.services.character_arc_service import CharacterArcService
from sqlalchemy.orm import Session
from ..models.models import Chapter, Book, Scene
from bs4 import BeautifulSoup
import re
from ..schemas.schemas import (
    ChapterCreate,
    ChapterUpdate,
    ChapterOutlineResponse,
    ChapterGenerateRequest,
    SceneOutlineResponse,
)
from ..services.ai_service import get_openai_client
from fastapi import HTTPException
import json
from typing import List
from fastapi.responses import StreamingResponse
from ..services.setting_service import get_setting_by_key
from app.prompts import format_prompt
import time


def create_chapter(db: Session, book_id: int, chapter: ChapterCreate, user_id: str):
    # Check if book exists
    book = db.query(Book).filter(Book.id == book_id).first()
    if not book:
        return None

    # Get the highest chapter number for this book
    max_chapter = (
        db.query(Chapter)
        .filter(Chapter.book_id == book_id)
        .order_by(Chapter.chapter_no.desc())
        .first()
    )

    # Set the next chapter number
    next_chapter_no = 1 if not max_chapter else max_chapter.chapter_no + 1

    # Check if a chapter with this number already exists in the book
    existing_chapter = (
        db.query(Chapter)
        .filter(Chapter.book_id == book_id, Chapter.chapter_no == next_chapter_no)
        .first()
    )

    if existing_chapter:
        return None

    current_time = int(time.time())
    db_chapter = Chapter(
        book_id=book_id,
        title=chapter.title,
        chapter_no=next_chapter_no,
        content=chapter.content,
        source_text=chapter.source_text,
        state="DRAFT",
        created_at=current_time,
        updated_at=current_time,
        created_by=user_id,
        updated_by=user_id
    )
    db.add(db_chapter)
    db.commit()
    db.refresh(db_chapter)
    return db_chapter


def update_chapter(
    db: Session, book_id: int, chapter_id: int, chapter_update: ChapterUpdate, user_id: str
):
    chapter = (
        db.query(Chapter)
        .filter(Chapter.id == chapter_id, Chapter.book_id == book_id)
        .first()
    )
    if not chapter:
        return None

    chapter.content = chapter_update.content
    chapter.source_text = chapter_update.source_text
    chapter.updated_at = int(time.time())
    chapter.updated_by = user_id
    db.commit()
    db.refresh(chapter)
    return chapter


def get_chapter(db: Session, book_id: int, chapter_id: int):
    return (
        db.query(Chapter)
        .filter(Chapter.id == chapter_id, Chapter.book_id == book_id)
        .first()
    )


def patch_chapter_source_text(
    db: Session, book_id: int, chapter_id: int, source_text: str | None, user_id: str
):
    chapter = (
        db.query(Chapter)
        .filter(Chapter.id == chapter_id, Chapter.book_id == book_id)
        .first()
    )
    if not chapter:
        return None

    chapter.source_text = source_text
    chapter.updated_at = int(time.time())
    chapter.updated_by = user_id
    db.commit()
    db.refresh(chapter)
    return chapter


def patch_chapter_state(db: Session, book_id: int, chapter_id: int, state: str | None, user_id: str):
    chapter = (
        db.query(Chapter)
        .filter(Chapter.id == chapter_id, Chapter.book_id == book_id)
        .first()
    )
    if not chapter:
        return None

    chapter.state = state
    chapter.updated_at = int(time.time())
    chapter.updated_by = user_id
    db.commit()
    db.refresh(chapter)
    return chapter


async def generate_chapter_outline(
    db: Session, book_id: int, chapter_id: int, user_prompt: str, user_id: str
) -> List[SceneOutlineResponse]:
    try:
        # Get AI model and temperature settings
        ai_model = get_setting_by_key(db, "create_scenes_ai_model").value
        temperature = float(get_setting_by_key(db, "create_scenes_temperature").value)

        # Initialize OpenAI client with the selected model
        client = get_openai_client(ai_model)

        # Get the chapter
        chapter = (
            db.query(Chapter)
            .filter(Chapter.id == chapter_id, Chapter.book_id == book_id)
            .first()
        )
        if not chapter:
            raise HTTPException(status_code=404, detail="Chapter not found")

        # Get context size setting for how many previous chapters to include for scene generation
        context_size = int(get_setting_by_key(db, "scenes_previous_chapters_context_size").value)
            
        # Get the specified number of previous chapters in order
        previous_chapters = (
            db.query(Chapter)
            .filter(Chapter.book_id == book_id, Chapter.chapter_no < chapter.chapter_no)
            .order_by(Chapter.chapter_no.desc())
            .limit(context_size)
            .all()
        )
        
        # Reverse to get chronological order
        previous_chapters.reverse()

        # print chapters no.
        print("Previous chapters:")
        print([ch.chapter_no for ch in previous_chapters])

        # Prepare context from previous chapters
        previous_chapters_context = "\n\n".join(
            [
                f"Chapter {ch.chapter_no}: {ch.title}\n{ch.content}"
                for ch in previous_chapters
            ]
        )

        # Prepare the messages for GPT
        system_prompt = format_prompt(
            SCENE_GENERATION_SYSTEM_PROMPT_V1,
            previous_chapters=previous_chapters_context
        )

        character_arc_service = CharacterArcService()
        character_arcs = character_arc_service.get_character_arcs_by_book_id(book_id)

        print(system_prompt)
        
        character_arcs_content = ""
        if character_arcs:
            character_arcs_content = "\n            -------- Character Arcs--------\n"
            for arc in character_arcs:
                character_arcs_content += f"{arc.content}\n\n"
        
        chapter_source_text = ""
        if chapter.source_text:
            chapter_source_text = "\n\n-------- Summary of the chapter--------\n\n"
            chapter_source_text += f"{chapter.source_text}\n\n"
        

        user_message = f"""
{character_arcs_content}
{chapter_source_text}
{user_prompt}
"""
        print(user_message)
        messages = [
            {
                "role": "system",
                "content": system_prompt,
            },
            {
                "role": "user",
                "content": user_message,
            }
        ]

        try:
            completion = client.beta.chat.completions.parse(
                model=ai_model,
                messages=messages,
                temperature=temperature,
                response_format=ChapterOutlineResponse,
            )

            # Get the parsed response
            outline_response = completion.choices[0].message.parsed

            # Store scenes in the database and create response objects
            scene_responses = []

            # Delete existing scenes
            db.query(Scene).filter(Scene.chapter_id == chapter_id).delete()
            db.flush()

            current_time = int(time.time())
            print(outline_response)
            # Process scenes
            for scene in outline_response.scenes:
                # Create scene
                db_scene = Scene(
                    chapter_id=chapter_id,
                    scene_number=scene.scene_number,
                    title=scene.title,
                    content=scene.content,
                    created_at=current_time,
                    updated_at=current_time,
                    created_by=user_id,
                    updated_by=user_id
                )
                db.add(db_scene)
                db.flush()

                # Create response
                scene_responses.append(
                    SceneOutlineResponse(
                        scene_number=db_scene.scene_number,
                        title=db_scene.title,
                        content=db_scene.content,
                    )
                )

            db.commit()
            return scene_responses

        except Exception as e:
            print(f"OpenAI API error: {str(e)}")
            raise HTTPException(status_code=500, detail=f"OpenAI API error: {str(e)}")

    except HTTPException:
        raise
    except Exception as e:
        print(f"Unexpected error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Unexpected error: {str(e)}")


async def stream_chapter_content(
    db: Session, book_id: int, chapter_id: int, request: ChapterGenerateRequest
):
    # Get the book and chapter
    book = db.query(Book).filter(Book.id == book_id).first()
    if not book:
        raise HTTPException(status_code=404, detail="Book not found")

    chapter = (
        db.query(Chapter)
        .filter(Chapter.id == chapter_id, Chapter.book_id == book_id)
        .first()
    )
    if not chapter:
        raise HTTPException(status_code=404, detail="Chapter not found")

    # Get context size setting for how many previous chapters to include for chapter content generation
    context_size = int(get_setting_by_key(db, "chapter_content_previous_chapters_context_size").value)
        
    # Get the specified number of previous chapters in order
    previous_chapters = (
        db.query(Chapter)
        .filter(Chapter.book_id == book_id, Chapter.chapter_no < chapter.chapter_no)
        .order_by(Chapter.chapter_no.desc())
        .limit(context_size)
        .all()
    )
    
    # Reverse to get chronological order
    previous_chapters.reverse()

    # print chapters no.
    print("Previous chapters:")
    print([ch.chapter_no for ch in previous_chapters])

    # Get all scenes for the current chapter
    scenes = (
        db.query(Scene)
        .filter(Scene.chapter_id == chapter_id)
        .order_by(Scene.scene_number)
        .all()
    )

    # Prepare context from previous chapters
    previous_chapters_context = "\n\n".join(
        [
            f"Chapter {ch.chapter_no}: {ch.title}\n{ch.content}"
            for ch in previous_chapters
        ]
    )

    # Prepare context from scenes if they exist
    scenes_context = ""
    if scenes:
        scenes_context = "\n\n".join(
            [
                f"Scene {s.scene_number}: {s.title}\n"
                f"Content: {s.content}"
                for s in scenes
            ]
        )

    # Prepare the messages for GPT
    system_prompt = format_prompt(
        CHAPTER_GENERATION_FROM_SCENE_SYSTEM_PROMPT_V1,
        previous_chapters=previous_chapters_context,
    )
    user_message = (
        "### Scene Breakdown:\n\n"
        f"{scenes_context}\n\n"
        "---\n\n"
        f"{request.user_prompt}"
    )
    
    print(system_prompt)
    print(user_message)
    messages = [
        {
            "role": "system",
            "content": system_prompt,
        },
        {
            "role": "user",
            "content": user_message,
        },
    ]

    try:
        # Get AI model and temperature settings
        ai_model = get_setting_by_key(db, "create_chapter_content_ai_model").value
        temperature = float(get_setting_by_key(db, "create_chapter_content_temperature").value)

        # Initialize OpenAI client with the selected model
        client = get_openai_client(ai_model)
        stream = client.chat.completions.create(
            model=ai_model,
            messages=messages,
            temperature=temperature,
            stream=True,  # Enable streaming
        )

        async def generate():
            full_response = ""

            try:
                for chunk in stream:
                    if chunk.choices[0].delta.content:
                        content = chunk.choices[0].delta.content
                        full_response += content

                        # Format as SSE with JSON content
                        json_content = json.dumps({"content": content})
                        yield f"data: {json_content}\n\n"

                # After streaming is complete, update the chapter in the database
                chapter.content = full_response
                db.commit()

                # Send completion signal
                yield "data: [DONE]\n\n"

            except Exception as e:
                # Send error and completion signal
                error_json = json.dumps({"error": str(e)})
                yield f"data: {error_json}\n\n"
                yield "data: [DONE]\n\n"
                raise HTTPException(status_code=500, detail=str(e))

        return StreamingResponse(
            generate(),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "X-Accel-Buffering": "no",
            },
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


def delete_chapter(db: Session, book_id: int, chapter_id: int):
    # Delete scenes first
    # db.query(Scene).filter(Scene.chapter_id == chapter_id).delete()
    # db.flush()
    
    chapter = (
        db.query(Chapter)
        .filter(Chapter.id == chapter_id, Chapter.book_id == book_id)
        .first()
    )
    if not chapter:
        return None

    db.delete(chapter)
    db.commit()
    return {"message": "Chapter deleted successfully"}


def bulk_upload_chapters(db: Session, book_id: int, html_content: str, user_id: str):
    """
    Process HTML content and create multiple chapters from it.
    
    Args:
        db: Database session
        book_id: ID of the book to add chapters to
        html_content: HTML content to process
        user_id: ID of the user performing the upload
        
    Returns:
        List of created chapters
    """
    # Check if book exists
    book = db.query(Book).filter(Book.id == book_id).first()
    if not book:
        return None
    
    # Parse the HTML
    soup = BeautifulSoup(html_content, "html.parser")
    
    # Find all headings (h1, h2, h3, etc.)
    headings = soup.find_all(['h1', 'h2', 'h3', 'h4', 'h5', 'h6'])
    chapters_data = []
    
    for i, header in enumerate(headings):
        title = header.get_text().strip()
        
        # Collect all content until the next heading
        content_parts = []
        for sibling in header.next_siblings:
            if getattr(sibling, "name", None) in ['h1', 'h2', 'h3', 'h4', 'h5', 'h6']:
                break
            content_parts.append(str(sibling))  # Save raw HTML

        # Simply join the content parts without additional processing
        chapter_content = ''.join(content_parts)
        
        # Store the title and raw HTML content
        chapters_data.append((title, chapter_content))
    
    # Get the highest chapter number for this book
    max_chapter = (
        db.query(Chapter)
        .filter(Chapter.book_id == book_id)
        .order_by(Chapter.chapter_no.desc())
        .first()
    )
    
    # Set the starting chapter number
    next_chapter_no = 1 if not max_chapter else max_chapter.chapter_no + 1
    
    created_chapters = []
    current_time = int(time.time())
    
    # Create chapters in the database
    for i, (title, content) in enumerate(chapters_data):
        chapter_no = next_chapter_no + i
        
        # Create the chapter
        db_chapter = Chapter(
            book_id=book_id,
            title=title,
            chapter_no=chapter_no,
            content=content,
            state="VERIFIED",
            created_at=current_time,
            updated_at=current_time,
            created_by=user_id,
            updated_by=user_id
        )
        
        db.add(db_chapter)
        db.commit()
        db.refresh(db_chapter)
        created_chapters.append(db_chapter)
    
    return created_chapters
