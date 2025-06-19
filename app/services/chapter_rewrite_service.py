import datetime
import json
import logging

from fastapi import HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.models.models import Book, Chapter, Scene
from app.prompts import format_prompt
from app.prompts.chapters import (
    CHAPTER_GENERATION_FROM_SCENE_SYSTEM_PROMPT_V1 as CHAPTER_GENERATION_SYSTEM_PROMPT,
)
from app.prompts.rewrite_prompts import CHAPTER_REWRITE_PROMPT
from app.services.ai_service import get_openai_client
from app.services.chapter_service import get_context_chapters
from app.services.evaluations.critique_agent.critique_service import generate_chapter_critique
from app.services.setting_service import get_setting_by_key


async def stream_chapter_rewrite(db: Session, book_id: int, chapter_id: int):
    # Get the book and chapter
    book = db.query(Book).filter(Book.id == book_id).first()
    if not book:
        raise HTTPException(status_code=404, detail="Book not found")

    chapter = db.query(Chapter).filter(Chapter.id == chapter_id, Chapter.book_id == book_id).first()
    if not chapter:
        raise HTTPException(status_code=404, detail="Chapter not found")
    # Log the original chapter content before rewriting
    original_content = chapter.content
    logging.info(f"Original chapter content length: {len(original_content)} chars")

    # Log the original chapter content length
    logging.info(f"Starting rewrite for chapter {chapter.chapter_no}: {chapter.title}")
    try:
        # Get context size setting for how many previous chapters to include
        context_size = int(
            get_setting_by_key(db, "chapter_content_previous_chapters_context_size").value
        )

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
        # Generate critique for the chapter
        logging.info(f"Generating critique for chapter {chapter.chapter_no}")
        critique_text = await generate_chapter_critique(db, chapter)
        logging.info(f"Critique analysis: {critique_text}")
        if not critique_text:
            raise HTTPException(status_code=500, detail="Failed to generate critique for chapter")

        # Log that critique was generated
        logging.info(f"Critique generated for chapter {chapter.chapter_no}")

        # Get the AI model and temperature settings
        ai_model = get_setting_by_key(db, "create_chapter_content_ai_model").value
        temperature = float(get_setting_by_key(db, "create_chapter_content_temperature").value)

        # Get previous chapters, last chapter, and next chapter context
        previous_chapters_context, last_chapter_content, next_chapter_content = (
            get_context_chapters(db, book_id, chapter.chapter_no, context_size)
        )

        # Get scenes if they exist
        scenes = (
            db.query(Scene)
            .filter(Scene.chapter_id == chapter_id)
            .order_by(Scene.scene_number)
            .all()
        )

        # Prepare context from scenes if they exist
        scenes_context = ""
        if scenes:
            scenes_context = "\n\n".join(
                [f"Scene {s.scene_number}: {s.title}\n" f"Content: {s.content}" for s in scenes]
            )

        # Prepare the messages for GPT - use same system prompt as original chapter generation
        system_prompt = format_prompt(
            CHAPTER_GENERATION_SYSTEM_PROMPT,
            previous_chapters=previous_chapters_context,
            last_chapter=last_chapter_content,
            next_chapter=next_chapter_content,
        )

        # Use the same user message format as original chapter generation
        user_message = (
            "📌 CONTINUATION RULE:\n"
            "Begin immediately where the previous chapter ended. Do not start a new timeline or day. Do not reintroduce the characters. Flow directly from the final emotional or narrative beat of the last paragraph in the previous chapter.\n\n"
            "### Scene Breakdown:\n\n"
            f"{scenes_context}\n\n"
            "---\n\n"
            f"Generate chapter {chapter.chapter_no} titled '{chapter.title}'."
        )

        # Prepare the messages including the original chapter as assistant's response
        # and the critique as a new user message
        # Format the rewrite prompt with the critique included
        rewrite_prompt = CHAPTER_REWRITE_PROMPT.format(critique_analysis=critique_text)

        # Construct the messages for the AI
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_message},
            {"role": "assistant", "content": original_content},
            {"role": "user", "content": rewrite_prompt},
        ]

        # Get OpenAI client
        client = get_openai_client(ai_model)

        # Stream the rewritten chapter content
        logging.info(f"Streaming chapter rewrite using model: {ai_model}")
        stream = client.chat.completions.create(
            model=ai_model,
            messages=messages,
            temperature=temperature,
            stream=True,
        )

        # Define the streaming response function
        async def generate():
            rewritten_content = ""

            try:
                for chunk in stream:
                    if chunk.choices[0].delta.content:
                        content = chunk.choices[0].delta.content
                        rewritten_content += content

                        # Format as SSE with JSON content
                        json_content = json.dumps({"content": content})
                        yield f"data: {json_content}\n\n"

                # Update the chapter in the database
                chapter.content = rewritten_content
                chapter.updated_at = datetime.datetime.now()
                db.commit()
                logging.info(f"Updated chapter {chapter.chapter_no} with rewritten content")
            except Exception as e:
                logging.error(f"Error streaming chapter rewrite: {str(e)}")
                db.rollback()
                # Send error to client
                error_json = json.dumps({"error": str(e)})
                yield f"data: {error_json}\n\n"

        # Return the streaming response
        return StreamingResponse(generate(), media_type="text/event-stream")
    except Exception as e:
        logging.error(f"Error in chapter rewrite: {str(e)}")
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Error in chapter rewrite: {str(e)}")
