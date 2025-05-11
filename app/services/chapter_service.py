from app.prompts.scenes import SCENE_GENERATION_SYSTEM_PROMPT_V1
from app.prompts.chapters import CHAPTER_GENERATION_FROM_SCENE_SYSTEM_PROMPT_V1
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

        print(system_prompt)
        user_message = f"""
            -------- Character Arcs--------
# Emma Thornton - Character Arc Analysis

## Description
Emma Thornton is a talented and resilient individual in her late twenties, beautiful and hot. She is known for her sharp wit and an indomitable spirit that shines through her polished, professional demeanor. Emma hails from a modest background but has clawed her way up the corporate ladder through sheer determination and skill in financial consultancy. Her journey takes her through high-stakes boardrooms and international conferences, emphasizing the global impact of her career.

## Role
Protagonist

## Key Relationships
- **The Betrayer (Lucas Grant)**: Emma's ex-fiancé whose betrayal sets her on a path of transformation.
- **The Supportive Partner (Alexander Hayes)**: A wealthy businessman who becomes Emma's ally and eventual romantic partner.
- **The Rival (Olivia Brooks)**: Once Emma's closest confidant, Olivia becomes a significant antagonist.
- **The Loyal Confidant (Sophie Nguyen)**: Emma's best friend and manager, who supports her unconditionally.
- **The Professional Ally (Robert Lang)**: A senior partner in the firm who recognizes Emma's potential and aids her career comeback.

## Motivation
Emma is motivated by a fierce desire to reclaim her career and self-worth after being betrayed by those she trusted most. Her journey evolves from seeking personal vengeance to achieving professional success and self-empowerment.

## Starting State
At the story's outset, Emma is heartbroken and blindsided by Lucas's betrayal with Olivia. Initially compliant and emotionally vulnerable, she decides to take control of her life, forming a strategic partnership with Alexander Hayes, a powerful figure in the corporate world.

## Transformation
Emma's transformation is marked by several pivotal moments:
- Her decision to enter a marriage of convenience with Alexander, which empowers her to regain control.
- Her strategic maneuvers to expose Lucas and Olivia's deceit, highlighting her intelligence and resilience.
- Her triumphant return to the corporate world, reclaiming her status and gaining industry respect.
- Her growing independence and confidence, navigating complex relationships and career challenges with poise.

## Ending State
By the end of the story, Emma is a successful and self-assured individual, having overcome betrayal and manipulation. She reestablishes her career, garners public support, and enjoys a loving relationship with Alexander. Her journey embodies personal growth and empowerment, transitioning from a victim of betrayal to a formidable force in her industry.

# Lucas Grant - Character Arc Analysis

## Description
Lucas Grant is a charming and ambitious executive in his early thirties, known for his suave appearance and persuasive demeanor. With dark hair and a confident smile, he exudes charisma but harbors a manipulative and self-serving nature. Holding a senior position in a multinational corporation, Lucas is driven by a relentless pursuit of power and control.

## Role
Antagonist

## Key Relationships
- **The Betrayed Partner (Emma Thornton)**: Lucas's former fiancée, whose trust he betrays.
- **The Co-Conspirator (Olivia Brooks)**: Lucas's secret lover and ally, with whom he plots against Emma.
- **The Enabler (Matthew Grant)**: Lucas's older brother, who unwittingly becomes involved in Lucas's schemes.

## Motivation
Lucas is driven by ambition and a desire to maintain his reputation and control over his professional domain. His actions are fueled by a need to manipulate those around him to achieve his goals.

## Starting State
Lucas begins the story confident in his ability to manage his personal and professional life, maintaining a secret affair with Olivia while publicly committed to Emma.

## Transformation
Lucas's transformation is characterized by increasing desperation:
- As Emma's strategic actions expose his deceit, Lucas's confidence crumbles.
- He resorts to more manipulative tactics to regain control over Emma and his professional standing.
- His relationship with Olivia becomes strained as their plans unravel, leading to professional and personal setbacks.

## Ending State
By the story's conclusion, Lucas is disgraced and vulnerable, having lost control over Emma and facing the fallout of his actions. His professional domain is in chaos, and his personal relationships are fractured, marking his descent from power to vulnerability.

# Alexander Hayes - Character Arc Analysis

## Description
Alexander Hayes is a distinguished and affluent businessman in his late thirties, known for his strategic acumen and man of few words. With silver-streaked hair and a commanding presence, he is both intimidating. Despite his wealth, Alexander remains grounded and is driven by a strong sense of justice and loyalty.

## Role
Supporting Character

## Key Relationships
- **The Protagonist (Emma Thornton)**: Alexander's partner, whom he supports unconditionally.
- **The Rival (Olivia Brooks)**: Seen as a competitor due to her attempts to undermine Emma.
- **The Confidant (Sophie Nguyen)**: Emma's friend, privy to Alexander's role in Emma's life.
- **The Ally (Robert Lang)**: A professional acquaintance whom Alexander influences to aid Emma.

## Motivation
Alexander is motivated by his love for Emma and a desire to see her succeed, driven by a sense of justice to protect her from harm.

## Starting State
Alexander starts as a wealthy individual under pressure to marry. He enters a marriage of convenience with Emma, which gradually blossoms into a genuine relationship.

## Transformation
Alexander's transformation is subtle yet profound:
- His initial strategic marriage evolves into genuine affection and unwavering support for Emma.
- He provides emotional and logistical support, aiding Emma through personal and professional turmoil.
- His protective actions, including orchestrating interventions, demonstrate his commitment to Emma's well-being.

## Ending State
By the end of the story, Alexander is deeply in love with Emma, having transitioned from a strategic partner to a devoted spouse. His efforts have helped Emma reclaim her career and independence, resulting in a relationship defined by mutual respect and support.

# Olivia Brooks - Character Arc Analysis

## Description
Olivia Brooks is a competitive and ambitious woman in her late twenties, with a striking appearance marked by sleek black hair and a confident stride. Once a close friend of Emma, Olivia is driven by jealousy and a desire for professional success. Her willingness to betray Emma for personal gain reveals her cunning nature.

## Role
Antagonist

## Key Relationships
- **The Protagonist (Emma Thornton)**: Olivia's former close friend and now rival.
- **The Lover (Lucas Grant)**: Her romantic partner and co-conspirator in schemes against Emma.
- **The Confidant (Matthew Grant)**: Lucas's brother, who becomes entangled in their deceit.

## Motivation
Olivia is fueled by jealousy and ambition, seeking to elevate her status by undermining Emma and aligning with influential figures.

## Starting State
Olivia begins the story as Emma's close friend, secretly involved with Lucas and plotting to advance her career at Emma's expense.

## Transformation
Olivia's transformation is marked by her increasing desperation:
- Her initial confidence is shattered as Emma's strategic moves expose her duplicity.
- Olivia becomes isolated as her schemes backfire, leading to setbacks in both her professional and personal life.
- Her relationship with Lucas deteriorates, and her public image is severely tarnished.

## Ending State
By the end of the story, Olivia is left disgraced, having lost her professional standing and facing public humiliation. Her attempts to undermine Emma have failed, and she must confront the consequences of her actions, marking her fall from perceived power to vulnerability.
            
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
            # Use beta.chat.completions.parse for structured outputs
            print(f"Using model: {ai_model} with temperature: {temperature}")
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
        print(f"Using model: {ai_model}, temperature: {temperature}")
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
