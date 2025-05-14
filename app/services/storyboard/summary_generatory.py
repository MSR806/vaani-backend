import logging
from sqlalchemy.orm import Session
from typing import List, Dict, Any

from app.services.ai_service import get_openai_client
from app.repository.plot_beat_repository import PlotBeatRepository
from app.repository.storyboard_repository import StoryboardRepository
from app.repository.character_arcs_repository import CharacterArcsRepository
from app.repository.chapter_repository import ChapterRepository
from app.models.models import Chapter
from app.prompts.story_generator_prompts import CHAPTER_SUMMARY_SYSTEM_PROMPT, CHAPTER_SUMMARY_USER_PROMPT_TEMPLATE
from app.utils.model_settings import ModelSettings
from app.utils.constants import SettingKeys

# Define the response format schema
from pydantic import BaseModel, Field
from typing import List

class ChapterSummary(BaseModel):
    chapter_number: int = Field(..., description="The chapter number")
    title: str = Field(..., description="A descriptive title for the chapter")
    summary: str = Field(..., description="A 3-5 sentence summary of the chapter content")

class ChapterSummariesResponse(BaseModel):
    summaries: List[ChapterSummary] = Field(..., description=f"List of chapter summaries")

logger = logging.getLogger(__name__)

class SummarizerGenerator:
    def __init__(self, db: Session, plot_beat_id: int, count: int = 10):
        self.db = db
        self.plot_beat_id = plot_beat_id
        self.count = count
        self.plot_beat_repo = PlotBeatRepository(self.db)
        self.storyboard_repo = StoryboardRepository(self.db)
        self.character_arcs_repo = CharacterArcsRepository(self.db)
        self.chapter_repo = ChapterRepository(self.db)
        self.model_settings = ModelSettings(self.db)
        
        # Initialize AI client
        try:
            self.client = get_openai_client()
        except Exception as e:
            logger.warning(f"Could not initialize OpenAI client: {str(e)}")
            self.client = None
        
    async def initialize(self):
        if self.plot_beat_id:
            self.plot_beat = self.plot_beat_repo.get_by_id(self.plot_beat_id)
            self.storyboard = self.storyboard_repo.get_by_id(self.plot_beat.source_id)
            self.character_arcs = self.character_arcs_repo.get_by_type_and_source_id("STORYBOARD", self.storyboard.id)
            # Get the book_id for retrieving existing chapters
            self.book_id = self.storyboard.book_id
            
    def get_existing_chapters(self):
        try:
            if not hasattr(self, 'book_id') or not self.book_id:
                logger.warning("Book ID not available for retrieving existing chapters")
                return []
                
            # Get all chapters for this book, ordered by chapter number
            existing_chapters = self.chapter_repo.get_by_book_id(self.book_id)
            
            # Sort chapters by chapter number to ensure proper order
            existing_chapters.sort(key=lambda ch: ch.chapter_no)
            
            logger.info(f"Retrieved {len(existing_chapters)} existing chapters for book {self.book_id}")
            return existing_chapters
        except Exception as e:
            logger.error(f"Error retrieving existing chapters: {str(e)}")
            return []
            
    def format_previous_chapter_summaries(self, chapters: List[Chapter], max_chapters=10):
        try:
            if not chapters:
                return "No previous chapters exist."
            
            # Store the latest chapter number for continuing the sequence
            if chapters:
                self.latest_chapter_number = chapters[-1].chapter_no
            else:
                self.latest_chapter_number = 0
                
            # Select relevant chapters based on different strategies
            if len(chapters) <= max_chapters:
                # If we have fewer chapters than the maximum, use all of them
                selected_chapters = chapters
                # No strategy note needed when all chapters are included
            else:
                # If we have many chapters, only include the most recent chapters
                selected_chapters = chapters[-max_chapters:]
                
                # Add a note about omitted chapters
                gap_size = len(chapters) - max_chapters
                strategy_note = f"Note: {gap_size} earlier chapters omitted for brevity. Only the {max_chapters} most recent chapters shown."
                
                # Add the strategy note at the beginning of formatted summaries
                formatted_summaries = [strategy_note]
            
            # Initialize formatted_summaries if not already done
            if not 'formatted_summaries' in locals():
                formatted_summaries = []
            
            for chapter in selected_chapters:
                summary = f"Chapter {chapter.chapter_no}: {chapter.title}\n"
                if chapter.source_text:
                    summary += f"{chapter.source_text}\n"
                else:
                    summary += "No content available.\n"
                    
                formatted_summaries.append(summary)
            
            # Add a note about where to continue numbering
            if self.latest_chapter_number > 0:
                formatted_summaries.append(f"\nNew chapters should continue from chapter {self.latest_chapter_number + 1}.")
                
            return "\n\n".join(formatted_summaries)
        except Exception as e:
            logger.error(f"Error formatting chapter summaries: {str(e)}")
            return "Error retrieving previous chapter summaries."
    
    async def generate_summaries(self):
        try:
            if not self.client:
                logger.error("OpenAI client not initialized")
                return []
            
            # Use prompts from story_generator_prompts.py
            system_prompt = CHAPTER_SUMMARY_SYSTEM_PROMPT
            
            # Get existing chapters for context
            existing_chapters = self.get_existing_chapters()
            
            # Format previous chapter summaries using default max_chapters value
            previous_summaries = self.format_previous_chapter_summaries(existing_chapters)
            
            # Format the user prompt template with our data
            character_arcs_content = [arc.content for arc in self.character_arcs]
            user_prompt = CHAPTER_SUMMARY_USER_PROMPT_TEMPLATE.format(
                count=self.count,
                plot_beats=self.plot_beat.content,
                character_arcs=character_arcs_content,
                previous_chapter_summaries=previous_summaries
            )
            
            # Get AI model and temperature from settings using ModelSettings
            model, temperature = self.model_settings.chapter_summary_from_storyboard()
            logger.info(f"Using model {model} with temperature {temperature} for chapter summary generation")
            
            # Call the OpenAI API to generate the summaries using structured JSON format
            response = self.client.beta.chat.completions.parse(
                model=model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=temperature,
                response_format=ChapterSummariesResponse
            )
            
            # Get the parsed response with structured data
            summaries_response = response.choices[0].message.parsed
            
            return summaries_response.summaries
        except Exception as e:
            logger.error(f"Error generating summaries: {str(e)}")
            return []
            
    def prepare_chapter_data(self, summaries: List[ChapterSummary]) -> List[Dict[str, Any]]:
        chapters_data = []
        
        # Determine the starting chapter number based on existing chapters
        starting_chapter_no = 1
        if hasattr(self, 'latest_chapter_number'):
            starting_chapter_no = self.latest_chapter_number + 1
        
        # Check if the AI-generated chapter numbers align with our expected sequence
        # If not, we'll override them to ensure proper continuation
        chapter_numbers_need_adjustment = False
        if summaries and summaries[0].chapter_number != starting_chapter_no:
            logger.info(f"Adjusting chapter numbers to continue from {starting_chapter_no} (AI provided {summaries[0].chapter_number})")
            chapter_numbers_need_adjustment = True
        
        for i, summary in enumerate(summaries):
            # If we need to adjust chapter numbers, override with the correct sequence
            chapter_no = starting_chapter_no + i if chapter_numbers_need_adjustment else summary.chapter_number
            
            chapter_data = {
                "book_id": self.storyboard.book_id,
                "title": summary.title,
                "chapter_no": chapter_no,
                "content": "",  # Initially empty content
                "source_text": summary.summary,
                "state": "DRAFT"
            }
            chapters_data.append(chapter_data)
            
        return chapters_data
    
    async def create_chapters(self, user_id: str = None):
        try:
            
            # Prepare the chapter data from the summaries
            chapters_data = self.prepare_chapter_data(self.summaries)
            
            # Use the repository's batch creation method for better performance
            chapters = self.chapter_repo.batch_create(chapters_data, user_id=user_id)
                
            logger.info(f"Successfully created {len(chapters)} chapters for book {self.storyboard.book_id}")
            return chapters
            
        except Exception as e:
            logger.error(f"Error creating chapters: {str(e)}")
            return []
            
    async def execute(self, user_id: str):

        # Initialize the generator
        await self.initialize()
        self.summaries = await self.generate_summaries()
        chapters = await self.create_chapters(user_id=user_id)
        return chapters