import logging

from sqlalchemy.orm import Session

from app.services.template_generator.story_abstractor import StoryAbstractor
from app.services.template_generator.story_extractor import StoryExtractor

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)


class TemplateManager:
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

            logger.info(
                f"Template creation and abstraction complete for book {self.book_id} (template_id={self.template_id})"
            )
            return self.template_id
        except Exception as e:
            logger.error(f"Error in template manager: {e}")
            raise e
