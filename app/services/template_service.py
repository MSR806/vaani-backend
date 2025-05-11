import asyncio
from sqlalchemy.orm import Session
from typing import List
from app.schemas.schemas import TemplateStatusEnum, TemplateRead, CharacterArcRead, PlotBeatRead
from app.repository.template_repository import TemplateRepository
from app.repository.character_arcs_repository import CharacterArcsRepository
from app.repository.plot_beat_repository import PlotBeatRepository
from app.models.models import Template
from app.services.template_generator.template_manager import TemplateManager

class TemplateService:
    def __init__(self):
        self.template_repo = TemplateRepository()
        self.character_arc_repo = CharacterArcsRepository()
        self.plot_beat_repo = PlotBeatRepository()

    def create_template(self, book_id: int) -> dict:
        # Step 1: Create the template entry in DB (synchronously)
        template = self.template_repo.create(
            name=f"Template for Book {book_id}",
            book_id=book_id,
            summary_status=TemplateStatusEnum.NOT_STARTED,
            character_arc_status=TemplateStatusEnum.NOT_STARTED,
            plot_beats_status=TemplateStatusEnum.NOT_STARTED,
            character_arc_template_status=TemplateStatusEnum.NOT_STARTED,
            plot_beat_template_status=TemplateStatusEnum.NOT_STARTED
        )
        template_id = template.id

        # Step 2: Start the async process in the background
        async def run_manager():
            manager = TemplateManager(book_id, self.template_repo.db)
            await manager.run(template_id)
        try:
            loop = asyncio.get_running_loop()
            loop.create_task(run_manager())
        except RuntimeError:
            # If no running loop, create a new one (for sync context, e.g. tests)
            asyncio.run(run_manager())

        return {"template_id": template_id, "status": template.summary_status}

    def get_templates(self) -> List[TemplateRead]:
        templates = self.template_repo.get_all_templates()
        return templates

    def get_template_details(self, template_id: int) -> dict:
        template = self.template_repo.get_by_id(template_id)
        if not template:
            return None
        character_arcs = self.character_arc_repo.get_by_type_and_source_id('TEMPLATE', template_id)
        plot_beats = self.plot_beat_repo.get_by_source_id_and_type(template_id, 'TEMPLATE')
        # Order plot beats by id
        plot_beats = sorted(plot_beats, key=lambda pb: pb.id)
        return {
            "template": template,
            "character_arcs": character_arcs,
            "plot_beats": plot_beats
        }

    def get_template_row(self, template_id: int):
        return self.template_repo.get_by_id(template_id) 