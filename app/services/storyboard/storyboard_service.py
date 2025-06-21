import logging

from app.repository.chapter_repository import ChapterRepository
from sqlalchemy.orm import Session

from app.models.enums import StoryboardStatus
from app.repository.plot_beat_repository import PlotBeatRepository
from app.repository.storyboard_repository import StoryboardRepository
from app.services.background_jobs.tasks import (
    add_generate_character_arcs_task_to_bg_jobs,
    add_generate_plot_beats_task_to_bg_jobs,
)
from app.utils.exceptions import (
    PlotBeatNotGeneratedException,
    StoryboardAlreadyExistsException,
    StoryboardCannotBeContinuedException,
    StoryboardNotFoundException,
)
from fastapi import HTTPException

logger = logging.getLogger(__name__)


class StoryboardService:
    def __init__(self, db: Session, user_id: str | None = None):
        self.db = db
        self.storyboard_repo = StoryboardRepository(db)
        self.plot_beat_repo = PlotBeatRepository(db)
        self.chapter_repo = ChapterRepository(db)
        self.user_id = user_id

    def create_storyboard(self, book_id: int, template_id: int, prompt: str):
        try:
            existing = self.storyboard_repo.get_by_book_id(book_id)
            if existing:
                raise StoryboardAlreadyExistsException(book_id)
        except StoryboardNotFoundException:
            pass

        storyboard = self.storyboard_repo.create(book_id, template_id, prompt, self.user_id)

        storyboard = self.storyboard_repo.update(
            storyboard.id, status=StoryboardStatus.CHARACTER_ARC_GENERATION_IN_PROGRESS
        )

        add_generate_character_arcs_task_to_bg_jobs(storyboard.id)
        return storyboard

    def get_storyboard_by_id(self, storyboard_id: int):
        self.db.expire_all()
        return self.storyboard_repo.get_by_id(storyboard_id)

    def get_storyboard_by_book_id(self, book_id: int):
        return self.storyboard_repo.get_by_book_id(book_id)

    def continue_storyboard(self, storyboard_id: int):
        try:
            storyboard = self.storyboard_repo.get_by_id(storyboard_id)
            if storyboard.status not in [StoryboardStatus.CHARACTER_ARC_GENERATION_COMPLETED]:
                raise StoryboardCannotBeContinuedException(storyboard_id, storyboard.status)

            if storyboard.status == StoryboardStatus.CHARACTER_ARC_GENERATION_COMPLETED:
                storyboard = self.storyboard_repo.update(
                    storyboard.id, status=StoryboardStatus.PLOT_BEATS_GENERATION_IN_PROGRESS
                )
                add_generate_plot_beats_task_to_bg_jobs(storyboard.id)

            return storyboard
        except Exception as e:
            logger.error(f"Error getting storyboard: {str(e)}")
            raise e
        
    def generate_chapters_summary(self, storyboard_id: int):
        try:
            storyboard = self.storyboard_repo.get_by_id(storyboard_id)
            if storyboard.status != StoryboardStatus.PLOT_BEATS_GENERATION_COMPLETED:
                raise PlotBeatNotGeneratedException()

            # Check if there are already chapters for this book
            from app.models.models import Chapter
            existing_chapters = (
                self.db.query(Chapter)
                .filter(Chapter.book_id == storyboard.book_id)
                .first()
            )
            
            if existing_chapters:
                raise HTTPException(
                    status_code=400,
                    detail="There are already chapters created for this book"
                )

            # Get plot beats for this storyboard
            plot_beats = self.plot_beat_repo.get_by_storyboard_id(storyboard_id)
            if not plot_beats:
                raise PlotBeatNotGeneratedException("No plot beats found for this storyboard")

            all_chapters = []
            chapters_count = 0
            
            # Generate chapters for each plot beat
            for plot_beat in plot_beats:
                try:
                    chapters_count += 1
                    chapter_no = chapters_count
                    chapters_data = {
                        "book_id": storyboard.book_id,
                        "title": f"Chapter {chapter_no}",
                        "chapter_no": chapter_no,
                        "content": "",  # Initially empty content
                        "source_text": plot_beat.content,
                        "character_ids": plot_beat.character_ids,
                        "state": "DRAFT",
                    }
                    all_chapters.append(chapters_data)
                    logger.info(f"Generated chapter {chapter_no} for plot beat {plot_beat.id}")
                except Exception as e:
                    logger.error(f"Error generating chapters for plot beat {plot_beat.id}: {str(e)}")
                    continue

            chapters = self.chapter_repo.batch_create(all_chapters, user_id=self.user_id)
            return chapters
        except Exception as e:
            logger.error(f"Error generating chapters summary: {str(e)}")
            raise e