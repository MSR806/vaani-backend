import logging
import traceback
from pathlib import Path
from typing import List, Optional

from sqlalchemy.orm import Session

from app.models.models import Book, Chapter
from app.prompts.critique_prompts import CRITIQUE_AGENT_SYSTEM_PROMPT, CRITIQUE_AGENT_USER_PROMPT
from app.services.ai_service import get_openai_client
from app.services.chapter_service import get_context_chapters

logger = logging.getLogger(__name__)


async def generate_chapter_critique(db: Session, chapter: Chapter) -> Optional[str]:
    logger.info(f"Generating critique for chapter {chapter.chapter_no}: {chapter.title}")
    logger.info(f"Chapter content length: {len(chapter.content)} chars")

    try:
        # Hardcoded model and temperature values
        ai_model = "o3"
        temperature = 1

        # Get appropriate context size from settings
        # Use a reasonable default if the setting doesn't exist
        context_size = 5

        # Get all three chapter contexts using our unified helper
        previous_chapters_context, last_chapter_content, next_chapter_content = (
            get_context_chapters(db, chapter.book_id, chapter.chapter_no, context_size)
        )

        logger.info(f"Previous chapters context length: {len(previous_chapters_context)} chars")
        logger.info(f"Last chapter context length: {len(last_chapter_content)} chars")
        logger.info(f"Next chapter context length: {len(next_chapter_content)} chars")

        chapter_content = f"CHAPTER {chapter.chapter_no}: {chapter.title}\n\n{chapter.content}"

        user_prompt = CRITIQUE_AGENT_USER_PROMPT.format(
            previous_chapters=previous_chapters_context,
            last_chapter=last_chapter_content,
            next_chapter=next_chapter_content,
            chapter=chapter_content,
        )

        # Call OpenAI API to analyze the chapter
        logger.info(f"Calling OpenAI API with model: {ai_model}")
        try:
            logger.info(f"User prompt: {user_prompt}")
            client = get_openai_client(ai_model)
            response = client.chat.completions.create(
                model=ai_model,
                messages=[
                    {"role": "system", "content": CRITIQUE_AGENT_SYSTEM_PROMPT},
                    {"role": "user", "content": user_prompt},
                ],
                temperature=temperature,
            )

            logger.info("OpenAI API call successful")
        except Exception as e:
            logger.error(f"OpenAI API call failed: {str(e)}")
            raise

        # Get the text response
        critique_result = response.choices[0].message.content

        logger.info(f"Successfully generated critique for chapter {chapter.chapter_no}")
        return critique_result

    except Exception as e:
        logger.error(f"Error generating critique for chapter {chapter.chapter_no}: {str(e)}")
        logger.error(traceback.format_exc())
        return None
