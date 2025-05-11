import sys
import asyncio
import logging
from pathlib import Path

from app.schemas.schemas import TemplateStatusEnum
from app.services.template_generator.story_abstractor import StoryAbstractor
from app.services.template_generator.story_extractor import StoryExtractor


# Add the project root to the Python path so we can import app modules
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from sqlalchemy.orm import Session
from app.database import get_db
from app.repository.template_repository import TemplateRepository
from app.repository.base_repository import BaseRepository

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class TemplateManager:
    """
    Manages the creation of a story template for a given book.
    1. Creates a template entry in the database.
    2. Runs story extraction (summaries, character arcs, plot beats).
    3. Runs story abstraction (generalizes arcs and plot beats), passing the template_id.
    """
    def __init__(self, book_id: int, db: Session = None):
        self.book_id = book_id
        self.db = db
        self.template = None
        self.template_id = None

    async def run(self, template_id: int):

        try:
            self.template_id = template_id
            logger.info(f"Created template with ID {self.template_id} for book {self.book_id}")

            # Step 3: Run story extraction
            extractor = StoryExtractor(self.book_id, self.db, self.template_id)
            await extractor.initialize()
            await extractor.run_analysis()
            logger.info("Story extraction complete.")

            # Step 4: Run story abstraction, passing template_id
            abstractor = StoryAbstractor(self.book_id, self.db, self.template_id)
            await abstractor.initialize()
            await abstractor.abstract_all_character_arcs()
            plot_beats = await abstractor.read_plot_beats()
            await abstractor.abstract_plot_beats(plot_beats)
            logger.info("Story abstraction complete.")

            logger.info(f"Template creation and abstraction complete for book {self.book_id} (template_id={self.template_id})")
            return self.template_id
        except Exception as e:
            logger.error(f"Error in template manager: {e}")
            raise e

async def main():
    if len(sys.argv) < 2:
        print("Usage: python template_manager.py <book_id>")
        sys.exit(1)
    book_id = int(sys.argv[1])
    manager = TemplateManager(book_id)
    await manager.run()

if __name__ == "__main__":
    asyncio.run(main())
