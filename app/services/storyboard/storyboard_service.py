import logging
from sqlalchemy.orm import Session

from app.repository.storyboard_repository import StoryboardRepository
from app.repository.plot_beat_repository import PlotBeatRepository
from app.services.storyboard.summary_generatory import SummarizerGenerator
from app.services.background_jobs.tasks import add_generate_character_arcs_task_to_bg_jobs, add_generate_plot_beats_task_to_bg_jobs
from app.models.enums import StoryboardStatus
from app.utils.exceptions import (
    StoryboardAlreadyExistsException, 
    StoryboardNotFoundException, 
    StoryboardCannotBeContinuedException,
    PlotBeatNotGeneratedException
)

logger = logging.getLogger(__name__)

class StoryboardService:
    def __init__(self, db: Session, user_id: str | None = None):
        self.db = db
        self.storyboard_repo = StoryboardRepository()
        self.plot_beat_repo = PlotBeatRepository()
        self.user_id = user_id
    
    def create_storyboard(self, book_id: int, template_id: int, prompt: str):
        try:
            existing = self.storyboard_repo.get_by_book_id(book_id)
            if existing:
                raise StoryboardAlreadyExistsException(book_id)
        except StoryboardNotFoundException:
            pass
        
        storyboard = self.storyboard_repo.create(book_id, template_id, prompt, user_id)

        storyboard = self.storyboard_repo.update(storyboard.id, status=StoryboardStatus.CHARACTER_ARC_GENERATION_IN_PROGRESS)
        
        add_generate_character_arcs_task_to_bg_jobs(storyboard.id)
        return storyboard
    
    def get_storyboard_by_id(self, storyboard_id: int):
        return self.storyboard_repo.get_by_id(storyboard_id)
    
    def get_storyboard_by_book_id(self, book_id: int):
        return self.storyboard_repo.get_by_book_id(book_id)
    
    def continue_storyboard(self, storyboard_id: int):
        try:
            storyboard = self.storyboard_repo.get_by_id(storyboard_id)
            if storyboard.status not in [StoryboardStatus.CHARACTER_ARC_GENERATION_COMPLETED]:
                raise StoryboardCannotBeContinuedException(storyboard_id, storyboard.status)
            
            if storyboard.status == StoryboardStatus.CHARACTER_ARC_GENERATION_COMPLETED:
                storyboard = self.storyboard_repo.update(storyboard.id, status=StoryboardStatus.PLOT_BEATS_GENERATION_IN_PROGRESS)
                add_generate_plot_beats_task_to_bg_jobs(storyboard.id)
            
            return storyboard
        except Exception as e:
            logger.error(f"Error getting storyboard: {str(e)}")
            raise e
    
    async def generate_chapters_summary(self, storyboard_id: int, plot_beat_id: int):
        try:
            existing = self.storyboard_repo.get_by_id(storyboard_id)
            if existing.status != StoryboardStatus.PLOT_BEATS_GENERATION_COMPLETED:
                raise PlotBeatNotGeneratedException()
            
            # Will throw exception if plot beat not found
            self.plot_beat_repo.get_by_id(plot_beat_id)

            summarizer_generator = SummarizerGenerator(self.db, plot_beat_id)
            chapters = await summarizer_generator.execute(self.user_id)
            
            return chapters
        except Exception as e:
            logger.error(f"Error getting storyboard: {str(e)}")
            raise e
            