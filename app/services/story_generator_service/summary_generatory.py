import logging
from sqlalchemy.orm import Session
from typing import List, Dict, Any

from app.services.ai_service import get_openai_client
from app.repository.plot_beat_repository import PlotBeatRepository
from app.repository.story_board_repository import StoryBoardRepository
from app.repository.character_arcs_repository import CharacterArcsRepository
from app.repository.chapter_repository import ChapterRepository
from app.models.models import Chapter
from app.prompts.story_generator_prompts import CHAPTER_SUMMARY_SYSTEM_PROMPT, CHAPTER_SUMMARY_USER_PROMPT_TEMPLATE

logger = logging.getLogger(__name__)

class SummarizerGenerator:
    def __init__(self, db: Session, plot_beat_id: int, count: int = 10):
        self.db = db
        self.plot_beat_id = plot_beat_id
        self.count = count
        self.plot_beat_repo = PlotBeatRepository(self.db)
        self.story_board_repo = StoryBoardRepository(self.db)
        self.character_arcs_repo = CharacterArcsRepository(self.db)
        self.chapter_repo = ChapterRepository(self.db)
        
        # Initialize AI client
        try:
            self.client = get_openai_client()
        except Exception as e:
            logger.warning(f"Could not initialize OpenAI client: {str(e)}")
            self.client = None
        
    async def initialize(self):
        if self.plot_beat_id:
            self.plot_beat = self.plot_beat_repo.get_by_id(self.plot_beat_id)
            self.story_board = self.story_board_repo.get_by_id(self.plot_beat.source_id)
            self.character_arcs = self.character_arcs_repo.get_by_type_and_source_id("STORY_BOARD", self.story_board.id)
    
    async def generate_summaries(self):
        try:
            if not self.client:
                logger.error("OpenAI client not initialized")
                return []
            
            # Define the response format schema
            from pydantic import BaseModel, Field
            from typing import List
            
            class ChapterSummary(BaseModel):
                chapter_number: int = Field(..., description="The chapter number")
                title: str = Field(..., description="A descriptive title for the chapter")
                summary: str = Field(..., description="A 3-5 sentence summary of the chapter content")
            
            class ChapterSummariesResponse(BaseModel):
                summaries: List[ChapterSummary] = Field(..., description=f"List of exactly {self.count} chapter summaries")
            
            # Use prompts from story_generator_prompts.py
            system_prompt = CHAPTER_SUMMARY_SYSTEM_PROMPT
            
            # Format the user prompt template with our data
            character_arcs_content = [arc.content for arc in self.character_arcs]
            user_prompt = CHAPTER_SUMMARY_USER_PROMPT_TEMPLATE.format(
                count=self.count,
                plot_beats=self.plot_beat.content,
                character_arcs=character_arcs_content
            )
            
            # Call the OpenAI API to generate the summaries using structured JSON format
            response = await self.client.beta.chat.completions.parse(
                model="gpt-4o",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=0.7,
                response_format=ChapterSummariesResponse
            )
            
            # Get the parsed response with structured data
            summaries_response = response.choices[0].message.parsed
            
            return summaries_response.summaries
        except Exception as e:
            logger.error(f"Error generating summaries: {str(e)}")
            return []
            
    def prepare_chapter_data(self, summaries: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        chapters_data = []
        
        for summary in summaries:
            chapter_data = {
                "book_id": self.story_board.book_id,
                "title": summary["title"],
                "chapter_no": summary["chapter_number"],
                "content": "",  # Initially empty content
                "source_text": summary["summary"],
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
                
            logger.info(f"Successfully created {len(chapters)} chapters for book {self.story_board.book_id}")
            return chapters
            
        except Exception as e:
            logger.error(f"Error creating chapters: {str(e)}")
            return []
            
    async def execute(self, user_id: str = None):

        # Initialize the generator
        await self.initialize()
        self.summaries = await self.generate_summaries()
        await self.create_chapters(user_id=user_id)