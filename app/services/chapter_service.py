import time
import json
from typing import List
from fastapi.responses import StreamingResponse
from bs4 import BeautifulSoup
import logging

from app.prompts.scenes import SCENE_GENERATION_SYSTEM_PROMPT_V1
from app.prompts.chapters import CHAPTER_GENERATION_FROM_SCENE_SYSTEM_PROMPT_V1
from app.services.character_arc_service import CharacterArcService
from sqlalchemy.orm import Session
from app.models.models import Chapter, Book, Scene
from app.schemas.schemas import (
    ChapterCreate,
    ChapterUpdate,
    ChapterGenerateRequest,
    SceneOutlineResponse,
)
from app.services.ai_service import get_openai_client
from fastapi import HTTPException
from app.services.setting_service import get_setting_by_key
from app.prompts import format_prompt
from app.utils.story_generator_utils import get_character_arcs_content_by_chapter_id

logger = logging.getLogger(__name__)


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
        updated_by=user_id,
    )
    db.add(db_chapter)
    db.commit()
    db.refresh(db_chapter)
    return db_chapter


def update_chapter(
    db: Session, book_id: int, chapter_id: int, chapter_update: ChapterUpdate, user_id: str
):
    chapter = db.query(Chapter).filter(Chapter.id == chapter_id, Chapter.book_id == book_id).first()
    if not chapter:
        return None

    if chapter_update.content:
        chapter.content = chapter_update.content
    if chapter_update.source_text:
        chapter.source_text = chapter_update.source_text
    chapter.updated_at = int(time.time())
    chapter.updated_by = user_id
    db.commit()
    db.refresh(chapter)
    return chapter


def get_chapter(db: Session, book_id: int, chapter_id: int):
    return db.query(Chapter).filter(Chapter.id == chapter_id, Chapter.book_id == book_id).first()


def patch_chapter_source_text(
    db: Session, book_id: int, chapter_id: int, source_text: str | None, user_id: str
):
    chapter = db.query(Chapter).filter(Chapter.id == chapter_id, Chapter.book_id == book_id).first()
    if not chapter:
        return None

    chapter.source_text = source_text
    chapter.updated_at = int(time.time())
    chapter.updated_by = user_id
    db.commit()
    db.refresh(chapter)
    return chapter


def patch_chapter_state(
    db: Session, book_id: int, chapter_id: int, state: str | None, user_id: str
):
    chapter = db.query(Chapter).filter(Chapter.id == chapter_id, Chapter.book_id == book_id).first()
    if not chapter:
        return None

    chapter.state = state
    chapter.updated_at = int(time.time())
    chapter.updated_by = user_id
    db.commit()
    db.refresh(chapter)
    return chapter


def get_context_chapters(
    db: Session, book_id: int, current_chapter_no: int, context_size: int
) -> tuple[str, str, str]:  # Returns (previous_ctx, last_ctx, next_ctx)
    from sqlalchemy import or_, and_

    previous_chapters_lower_bound = current_chapter_no - context_size

    queried_chapters = (
        db.query(Chapter)
        .filter(
            Chapter.book_id == book_id,
            or_(
                # Previous chapters: context_size chapters immediately before the current one
                and_(
                    Chapter.chapter_no < current_chapter_no,
                    Chapter.chapter_no >= previous_chapters_lower_bound,
                ),
                # Next chapter: the one immediately after the current one
                Chapter.chapter_no == current_chapter_no + 1,
            ),
        )
        .order_by(Chapter.chapter_no)  # Ensures previous chapters are first, then next chapter
        .all()
    )

    all_previous_chapters_list = []
    next_chapter_obj = None

    for ch_obj in queried_chapters:
        if ch_obj.chapter_no < current_chapter_no:
            all_previous_chapters_list.append(ch_obj)  # Already sorted chronologically
        elif ch_obj.chapter_no == current_chapter_no + 1:
            next_chapter_obj = ch_obj

    # Separate all_previous_chapters_list into previous (n-1-k) and last (n-1)
    actual_previous_chapters = []
    last_chapter_obj = None
    if all_previous_chapters_list:
        if len(all_previous_chapters_list) > 0:
            last_chapter_obj = all_previous_chapters_list[-1]
            actual_previous_chapters = all_previous_chapters_list[:-1]
        else:  # Should not happen if context_size >=1 and chapters exist
            pass  # last_chapter_obj remains None, actual_previous_chapters remains []
    # Prepare context from previous chapters (n-1-k)
    if actual_previous_chapters:
        previous_chapters_context_str = "\n\n".join(
            [
                f"Chapter {ch.chapter_no}: {ch.title}\n{ch.source_text}"  # summary
                for ch in actual_previous_chapters
            ]
        )
        print("Previous chapters (n-1-k) for context:")
        print([ch.chapter_no for ch in actual_previous_chapters])
    else:
        previous_chapters_context_str = "No previous chapters (n-1-k) available."
        print("Previous chapters (n-1-k) for context: None")

    # Prepare context for last chapter (n-1)
    if last_chapter_obj:
        last_chapter_content_str = f"Chapter {last_chapter_obj.chapter_no}: {last_chapter_obj.title}\n{last_chapter_obj.content}"
        print("Last chapter (n-1) for context:")
        print(last_chapter_obj.chapter_no)
    else:
        last_chapter_content_str = "No last chapter (n-1) available."
        print("Last chapter (n-1) for context: None")

    # Format next chapter content (n+1)
    if next_chapter_obj:
        next_chapter_content_str = f"Chapter {next_chapter_obj.chapter_no}: {next_chapter_obj.title}\n{next_chapter_obj.source_text or 'No content yet.'}"
        print("Next chapter (n+1) for context:")
        print(next_chapter_obj.chapter_no)
    else:
        next_chapter_content_str = "No next chapter (n+1) available."
        print("Next chapter (n+1) for context: None")

    return previous_chapters_context_str, last_chapter_content_str, next_chapter_content_str


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
            db.query(Chapter).filter(Chapter.id == chapter_id, Chapter.book_id == book_id).first()
        )
        if not chapter:
            raise HTTPException(status_code=404, detail="Chapter not found")

        # Get context size setting for how many previous chapters to include for scene generation
        # context_size includes both previous chapters (n-1-k) and the last chapter (n-1)
        context_size = int(get_setting_by_key(db, "scenes_previous_chapters_context_size").value)

        previous_chapters_context, last_chapter_content, next_chapter_content = (
            get_context_chapters(db, book_id, chapter.chapter_no, context_size)
        )

        # Prepare the messages for GPT
        system_prompt = format_prompt(
            SCENE_GENERATION_SYSTEM_PROMPT_V1,
            previous_chapters=previous_chapters_context,
            last_chapter=last_chapter_content,
            next_chapter=next_chapter_content,
        )

        character_arc_service = CharacterArcService(db)
        character_arcs_models = character_arc_service.get_character_arcs_by_book_id(book_id)
        logger.info(f"Found {len(character_arcs_models)} character arcs for book {book_id}")
        character_arcs = get_character_arcs_content_by_chapter_id(
            character_arcs_models, chapter.chapter_no
        )
        logger.info(f"Found {len(character_arcs)} character arcs for chapter {chapter.chapter_no}")
        character_arcs = [
            (arc[0], arc[1]) for arc in character_arcs if arc[2] in chapter.character_ids
        ]
        # log character names
        logger.info(
            f"Considering only {len(character_arcs)} character arcs: {', '.join([arc[0] for arc in character_arcs])}"
        )

        print(system_prompt)

        character_arcs_content = ""
        if character_arcs:
            character_arcs_content = "\n            -------- Character Arcs--------\n"
            for arc in character_arcs:
                character_arcs_content += f"{arc[1]}\n\n"

        chapter_source_text = ""
        if chapter.source_text:
            chapter_source_text = "\n\n-------- Summary of the current chapter--------\n\n"
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
            },
        ]

        try:
            completion = client.chat.completions.create(
                model=ai_model,
                messages=messages,
                temperature=temperature,
            )

            # Get the response text
            response_text = completion.choices[0].message.content
            print("Raw response text:", response_text)

            # Extract scenes using regex pattern matching
            import re

            scene_pattern = r"<scene-([0-9]+)>\s*<title>(.*?)</title>\s*([\s\S]*?)\s*</scene-\1>"
            scene_matches = list(re.finditer(scene_pattern, response_text))

            # If no scenes were found with the pattern, try a fallback approach
            if not scene_matches:
                logger.warning(
                    "No scenes matched the expected format. Attempting fallback parsing."
                )
                # Try a more lenient pattern that might catch variations
                alt_pattern = r"(?:scene|SCENE)[\s-]*([0-9]+)[:\s]*\s*(?:title|TITLE)?[:\s]*\s*([^\n]+)\n([\s\S]*?)(?=(?:scene|SCENE)[\s-]*[0-9]+|$)"
                scene_matches = list(re.finditer(alt_pattern, response_text))

            if not scene_matches:
                logger.error("Failed to extract any scenes from the response.")
                raise HTTPException(
                    status_code=500,
                    detail="Failed to extract scenes from AI response. Please try again.",
                )

            # Store scenes in the database and create response objects
            scene_responses = []

            # Delete existing scenes
            db.query(Scene).filter(Scene.chapter_id == chapter_id).delete()
            db.flush()

            current_time = int(time.time())

            # Process extracted scenes
            for match in scene_matches:
                # Extract scene information from regex match
                scene_number = int(match.group(1))
                scene_title = match.group(2).strip()
                scene_content = match.group(3).strip()

                # Create scene
                db_scene = Scene(
                    chapter_id=chapter_id,
                    scene_number=scene_number,
                    title=scene_title,
                    content=scene_content,
                    created_at=current_time,
                    updated_at=current_time,
                    created_by=user_id,
                    updated_by=user_id,
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

    chapter = db.query(Chapter).filter(Chapter.id == chapter_id, Chapter.book_id == book_id).first()
    if not chapter:
        raise HTTPException(status_code=404, detail="Chapter not found")

    # Get context size setting for how many previous chapters to include for chapter content generation
    context_size = int(
        get_setting_by_key(db, "chapter_content_previous_chapters_context_size").value
    )

    # Get all three chapter contexts: previous chapters, last chapter, and next chapter
    previous_chapters_context, last_chapter_content, next_chapter_content = get_context_chapters(
        db, book_id, chapter.chapter_no, context_size
    )

    # Get all scenes for the current chapter
    scenes = (
        db.query(Scene).filter(Scene.chapter_id == chapter_id).order_by(Scene.scene_number).all()
    )

    # Prepare context from scenes if they exist
    scenes_context = ""
    if scenes:
        scenes_context = "\n\n".join(
            [f"Scene {s.scene_number}: {s.title}\n" f"Content: {s.content}" for s in scenes]
        )

    character_arc_service = CharacterArcService(db)
    character_arcs_models = character_arc_service.get_character_arcs_by_book_id(book_id)
    character_arcs = get_character_arcs_content_by_chapter_id(
        character_arcs_models, chapter.chapter_no
    )
    character_arcs = [(arc[0], arc[1]) for arc in character_arcs if arc[2] in chapter.character_ids]
    # log character names
    logger.info(
        f"Considering only {len(character_arcs)} character arcs: {', '.join([arc[0] for arc in character_arcs])}"
    )

    character_arcs_content = ""
    if character_arcs:
        character_arcs_content = "\n            -------- Character Arcs--------\n"
        for arc in character_arcs:
            character_arcs_content += f"{arc[1]}\n\n"

    # Prepare the messages for GPT
    system_prompt = format_prompt(
        CHAPTER_GENERATION_FROM_SCENE_SYSTEM_PROMPT_V1,
        previous_chapters=previous_chapters_context,
        last_chapter=last_chapter_content,
        next_chapter=next_chapter_content,
        character_arcs=character_arcs_content,
    )
    user_message = (
        "📌 CONTINUATION RULE:\n"
        "Begin immediately where the previous chapter ended. Do not start a new timeline or day. Do not reintroduce the characters. Flow directly from the final emotional or narrative beat of the last paragraph in the previous chapter.\n\n"
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
    db.query(Scene).filter(Scene.chapter_id == chapter_id).delete()
    db.flush()

    chapter = db.query(Chapter).filter(Chapter.id == chapter_id, Chapter.book_id == book_id).first()
    if not chapter:
        return None

    db.delete(chapter)
    db.commit()
    return {"message": "Chapter deleted successfully"}


def delete_all_chapters(db: Session, book_id: int):
    """Delete all chapters for a book"""
    # Get all chapter IDs for this book
    chapter_ids = db.query(Chapter.id).filter(Chapter.book_id == book_id).all()
    chapter_ids = [c.id for c in chapter_ids]

    if not chapter_ids:
        return {"message": "No chapters found to delete"}

    # Delete all scenes for these chapters
    db.query(Scene).filter(Scene.chapter_id.in_(chapter_ids)).delete(synchronize_session=False)
    db.flush()

    # Delete all chapters
    deleted_count = (
        db.query(Chapter).filter(Chapter.book_id == book_id).delete(synchronize_session=False)
    )
    db.commit()

    return {"message": f"Successfully deleted {deleted_count} chapters"}


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
    headings = soup.find_all(["h1", "h2", "h3", "h4", "h5", "h6"])
    chapters_data = []

    for i, header in enumerate(headings):
        title = header.get_text().strip()

        # Collect all content until the next heading
        content_parts = []
        for sibling in header.next_siblings:
            if getattr(sibling, "name", None) in ["h1", "h2", "h3", "h4", "h5", "h6"]:
                break
            content_parts.append(str(sibling))  # Save raw HTML

        # Simply join the content parts without additional processing
        chapter_content = "".join(content_parts)

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
            updated_by=user_id,
        )

        db.add(db_chapter)
        db.commit()
        db.refresh(db_chapter)
        created_chapters.append(db_chapter)

    return created_chapters
