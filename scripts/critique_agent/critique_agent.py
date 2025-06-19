import traceback
from typing import List, Optional
import logging
from pathlib import Path

from app.services.ai_service import get_openai_client
from app.models.models import Book, Chapter

from critique_prompts import CRITIQUE_AGENT_SYSTEM_PROMPT, CRITIQUE_AGENT_USER_PROMPT

# Set up logging
logger = logging.getLogger(__name__)


async def analyze_chapter_critique(
    chapter: Chapter, previous_chapters: List[Chapter] = None
) -> Optional[str]:
    logger.info(f"Analyzing critique for chapter {chapter.chapter_no}: {chapter.title}")
    logger.info(f"Chapter content length: {len(chapter.content)} chars")

    try:
        # Prepare user prompt with previous chapters for context
        previous_chapter_content = ""
        if previous_chapters:
            # Combine previous chapters content with clear separators
            prev_chapters_text = []
            for prev_chapter in previous_chapters:
                prev_chapters_text.append(
                    f"CHAPTER {prev_chapter.chapter_no}: {prev_chapter.title}\n\n{prev_chapter.content}"
                )
                logger.info(f"Including previous chapter {prev_chapter.chapter_no} in context")

            previous_chapter_content = "\n\n---\n\n".join(prev_chapters_text)
            logger.info(f"Previous chapters context length: {len(previous_chapter_content)} chars")

        chapter_content = f"CHAPTER {chapter.chapter_no}: {chapter.title}\n\n{chapter.content}"

        user_prompt = CRITIQUE_AGENT_USER_PROMPT.format(
            previous_chapter=previous_chapter_content, chapter=chapter_content
        )

        # Call OpenAI API to analyze the chapter
        logger.info(f"Calling OpenAI API with model: o3")
        try:
            client = get_openai_client("o3")
            response = client.chat.completions.create(
                model="o3",
                messages=[
                    {"role": "system", "content": CRITIQUE_AGENT_SYSTEM_PROMPT},
                    {"role": "user", "content": user_prompt},
                ],
            )
            logger.info("OpenAI API call successful")
        except Exception as e:
            logger.error(f"OpenAI API call failed: {str(e)}")
            raise

        # Get the text response
        critique_result = response.choices[0].message.content

        logger.info(f"Successfully analyzed critique for chapter {chapter.chapter_no}")
        return critique_result

    except Exception as e:
        logger.error(f"Error analyzing critique for chapter {chapter.chapter_no}: {str(e)}")
        logger.error(traceback.format_exc())
        return None


async def save_critique_analysis(
    book: Book, chapter: Chapter, critique_text: str
) -> Optional[Path]:
    try:
        # Create directory for saving results if it doesn't exist
        output_dir = Path(f"scripts/critique_agent/output/critique_analysis/{book.id}")
        output_dir.mkdir(parents=True, exist_ok=True)
        logger.info(f"Created output directory: {output_dir}")

        # Create filename - use .txt extension for plain text
        filename = output_dir / f"chapter_{chapter.chapter_no:02d}_{chapter.id}.txt"

        # Save the raw text to file
        with open(filename, "w") as f:
            f.write(critique_text)
            logger.info(f"Critique text length: {len(critique_text)} chars")

        logger.info(f"Saved critique analysis to {filename}")
        return filename

    except Exception as e:
        logger.error(f"Error saving critique analysis: {str(e)}")
        logger.error(traceback.format_exc())
        return None
