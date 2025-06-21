import logging
from typing import Any, Dict, List

from sqlalchemy.orm import Session

from app.repository.chapter_repository import ChapterRepository
from app.repository.plot_beat_repository import PlotBeatRepository
from app.repository.storyboard_repository import StoryboardRepository

logger = logging.getLogger(__name__)


class SummarizerGenerator:
    def __init__(self, db: Session, plot_beat_id: int):
        self.db = db
        self.plot_beat_id = plot_beat_id
        self.plot_beat_repo = PlotBeatRepository(self.db)
        self.storyboard_repo = StoryboardRepository(self.db)
        self.chapter_repo = ChapterRepository(self.db)

    async def initialize(self):
        if self.plot_beat_id:
            self.plot_beat = self.plot_beat_repo.get_by_id(self.plot_beat_id)
            self.storyboard = self.storyboard_repo.get_by_id(self.plot_beat.source_id)

    def prepare_chapter_data(self) -> List[Dict[str, Any]]:
        # Get the latest chapter number
        existing_chapters = self.chapter_repo.get_by_book_id(self.storyboard.book_id)
        starting_chapter_no = 1
        if existing_chapters:
            existing_chapters.sort(key=lambda ch: ch.chapter_no)
            starting_chapter_no = existing_chapters[-1].chapter_no + 1

        chapter_data = {
            "book_id": self.storyboard.book_id,
            "title": f"Chapter {starting_chapter_no}",
            "chapter_no": starting_chapter_no,
            "content": "",  # Initially empty content
            "source_text": self.plot_beat.content,
            "character_ids": self.plot_beat.character_ids,
            "state": "DRAFT",
        }

        return [chapter_data]

    async def create_chapters(self, user_id: str = None):
        try:
            chapters_data = self.prepare_chapter_data()
            chapters = self.chapter_repo.batch_create(chapters_data, user_id=user_id)
            logger.info(f"Successfully created chapter for book {self.storyboard.book_id}")
            return chapters
        except Exception as e:
            logger.error(f"Error creating chapter: {str(e)}")
            return []

    async def execute(self, user_id: str):
        await self.initialize()
        chapters = await self.create_chapters(user_id=user_id)
        return chapters
