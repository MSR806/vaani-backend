import logging

from app.repository.storyboard_repository import StoryboardRepository
from app.services.background_jobs.tasks import add_generate_character_arcs_task_to_bg_jobs, add_generate_plot_beats_task_to_bg_jobs
from app.utils.exceptions import StoryboardAlreadyExistsException, StoryboardNotFoundException, StoryboardCannotBeContinuedException
from app.models.enums import StoryboardStatus

logger = logging.getLogger(__name__)

class StoryboardService:
    def __init__(self):
        self.storyboard_repo = StoryboardRepository()
    
    def create_storyboard(self, book_id: int, template_id: int, prompt: str, user_id: str):
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