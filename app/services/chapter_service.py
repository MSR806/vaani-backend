from sqlalchemy.orm import Session
from ..models.models import Chapter, Book, Scene, Character
from ..schemas.schemas import (
    ChapterCreate,
    ChapterUpdate,
    ChapterResponse,
    OutlineRequest,
    ChapterOutlineResponse,
    ChapterGenerateRequest,
    SceneOutlineResponse,
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

    db_chapter = Chapter(
        book_id=book_id,
        title=chapter.title,
        chapter_no=next_chapter_no,
        content=chapter.content,
        source_text=chapter.source_text,
    )
    db.add(db_chapter)
    db.commit()
    db.refresh(db_chapter)
    return db_chapter


def update_chapter(
    db: Session, book_id: int, chapter_id: int, chapter_update: ChapterUpdate
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
    db: Session, book_id: int, chapter_id: int, source_text: str | None
):
    chapter = (
        db.query(Chapter)
        .filter(Chapter.id == chapter_id, Chapter.book_id == book_id)
        .first()
    )
    if not chapter:
        return None

    chapter.source_text = source_text
    db.commit()
    db.refresh(chapter)
    return chapter


async def generate_chapter_outline(
    db: Session, book_id: int, chapter_id: int, user_prompt: str
) -> List[SceneOutlineResponse]:
    try:
        # Initialize OpenAI client
        client = get_openai_client()

        # Get the chapter
        chapter = (
            db.query(Chapter)
            .filter(Chapter.id == chapter_id, Chapter.book_id == book_id)
            .first()
        )
        if not chapter:
            raise HTTPException(status_code=404, detail="Chapter not found")

        # Get all previous chapters in order
        previous_chapters = (
            db.query(Chapter)
            .filter(Chapter.book_id == book_id, Chapter.chapter_no < chapter.chapter_no)
            .order_by(Chapter.chapter_no)
            .all()
        )

        # Get all scenes from previous chapters
        previous_scenes = []
        for prev_chapter in previous_chapters:
            scenes = (
                db.query(Scene)
                .filter(Scene.chapter_id == prev_chapter.id)
                .order_by(Scene.scene_number)
                .all()
            )
            previous_scenes.extend(scenes)

        # Get all characters from the book
        characters = db.query(Character).filter(Character.book_id == book_id).all()

        # Prepare context from previous chapters
        previous_chapters_context = "\n\n".join(
            [
                f"Chapter {ch.chapter_no}: {ch.title}\n{ch.content}"
                for ch in previous_chapters
            ]
        )

        # Get all characters in the book
        characters_context = "\n".join(
            [f"- {c.name}: {c.description}" for c in characters]
        )

        # Prepare the messages for GPT
        messages = [
            {
                "role": "system",
                "content": """You are a creative writing assistant specialized in creating chapter outlines.
                Based on the previous chapters and the available characters,
                create a structured outline for the chapter broken down into multiple scenes.
                
                For character descriptions, use this exact format with HTML tags:
                <b>Basic Traits:</b>
                <p>Age: [age]<br>
                Appearance: [physical description]<br>
                Profession/Background: [career and background]</p>

                <b>Personality:</b>
                <p>Key Traits: [list of traits]<br>
                Moral Code: [ethical framework]<br>
                Motivations: [what drives the character]</p>

                <b>Character Development:</b>
                <p>Internal Struggles: [personal conflicts]<br>
                External Conflicts: [external challenges]<br>
                Growth Arc: [character's journey]</p>
                
                Your response must be a valid JSON object with this structure:
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
                }
                
                Important:
                1. Ensure all strings are properly escaped
                2. Do not include any trailing commas
                3. Make sure all quotes are properly closed
                4. Keep the response within the token limit""",
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

Please provide a structured outline for this chapter:""",
            },
        ]

        try:
            # Use beta.chat.completions.parse for structured outputs
            completion = client.beta.chat.completions.parse(
                model=OPENAI_MODEL,
                messages=messages,
                temperature=0.7,
                response_format=ChapterOutlineResponse,
            )

            # Get the parsed response
            outline_response = completion.choices[0].message.parsed

            # Store scenes in the database and create response objects
            scene_responses = []

            # Delete existing scenes
            db.query(Scene).filter(Scene.chapter_id == chapter_id).delete()
            db.flush()

            # Process scenes
            for scene in outline_response.scenes:
                # Create scene
                db_scene = Scene(
                    chapter_id=chapter_id,
                    scene_number=scene.scene_number,
                    title=scene.title,
                    content=scene.content,
                )
                db.add(db_scene)
                db.flush()

                # Process characters
                scene_characters = []
                for char in scene.characters:
                    character = (
                        db.query(Character)
                        .filter(
                            Character.name == char.name, Character.book_id == book_id
                        )
                        .first()
                    )

                    if not character:
                        character = Character(
                            name=char.name,
                            description=char.description,
                            book_id=book_id,
                        )
                        db.add(character)
                        db.flush()

                    db_scene.characters.append(character)
                    scene_characters.append(character)

                # Create response
                scene_responses.append(
                    SceneOutlineResponse(
                        scene_number=db_scene.scene_number,
                        title=db_scene.title,
                        characters=[
                            {"name": c.name, "description": c.description}
                            for c in scene_characters
                        ],
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


async def generate_chapter_content(
    db: Session, book_id: int, chapter_id: int, request: ChapterGenerateRequest
):
    # Get the book and chapter
    book = db.query(Book).filter(Book.id == book_id).first()
    if not book:
        return None

    chapter = (
        db.query(Chapter)
        .filter(Chapter.id == chapter_id, Chapter.book_id == book_id)
        .first()
    )
    if not chapter:
        return None

    # Get all previous chapters in order
    previous_chapters = (
        db.query(Chapter)
        .filter(Chapter.book_id == book_id, Chapter.chapter_no < chapter.chapter_no)
        .order_by(Chapter.chapter_no)
        .all()
    )

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
                f"Characters: {', '.join(c.name for c in s.characters)}\n"
                f"Content: {s.content}"
                for s in scenes
            ]
        )

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
            Then continue with the chapter content.""",
        },
        {
            "role": "user",
            "content": f"""Previous Chapters:
{previous_chapters_context}

{"Scenes for Current Chapter:" + scenes_context if scenes_context else ""}

Current Chapter Information:
- Chapter Number: {chapter.chapter_no}
- Title: {chapter.title}

User's Request: {request.user_prompt}

Please write the complete chapter:""",
        },
    ]

    try:
        client = get_openai_client()
        response = client.chat.completions.create(
            model=OPENAI_MODEL, messages=messages, temperature=0.7
        )

        # Parse the response to separate title and content
        chapter_text = response.choices[0].message.content

        # Extract title and content
        try:
            # Split the text into lines and find the title line
            lines = chapter_text.split("\n")
            title = None
            content_start = 0

            # Look for the title in the first few lines
            for i, line in enumerate(lines):
                line = line.strip()
                # Remove markdown formatting
                clean_line = line.replace("**", "").strip()

                # Check for title in various formats
                if clean_line.startswith("TITLE:"):
                    title = clean_line.replace("TITLE:", "").strip()
                    content_start = i + 1
                    break

            # If no title found, use the first non-empty line as title
            if not title:
                for i, line in enumerate(lines):
                    line = line.strip().replace("**", "")
                    if line:
                        title = line
                        content_start = i + 1
                        break

            # If still no title, use default
            if not title:
                title = f"Chapter {chapter.chapter_no}"

            # Join the remaining lines for content
            content = "\n".join(lines[content_start:]).strip()

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
                content=content,
            )

        except Exception as e:
            raise Exception(f"Failed to process the generated chapter: {str(e)}")

    except Exception as e:
        raise Exception(str(e))


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

    # Get all previous chapters in order
    previous_chapters = (
        db.query(Chapter)
        .filter(Chapter.book_id == book_id, Chapter.chapter_no < chapter.chapter_no)
        .order_by(Chapter.chapter_no)
        .all()
    )

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
                f"Characters: {', '.join(c.name for c in s.characters)}\n"
                f"Content: {s.content}"
                for s in scenes
            ]
        )

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
            
            Important: Start your response directly with the chapter content. Do not include any prefixes like "TITLE:" or other subheadings.
            The chapter title will be handled separately.""",
        },
        {
            "role": "user",
            "content": f"""Previous Chapters:
{previous_chapters_context}

{"Scenes for Current Chapter:" + scenes_context if scenes_context else ""}

Current Chapter Information:
- Chapter Number: {chapter.chapter_no}
- Title: {chapter.title}

User's Request: {request.user_prompt}

Please write the complete chapter:""",
        },
    ]

    try:
        client = get_openai_client()
        stream = client.chat.completions.create(
            model=OPENAI_MODEL,
            messages=messages,
            temperature=0.7,
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
