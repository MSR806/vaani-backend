import asyncio
from sqlalchemy.orm import Session
from typing import List
from app.schemas.schemas import TemplateStatusEnum, TemplateRead, CharacterArcRead, PlotBeatRead
from app.repository.template_repository import TemplateRepository
from app.repository.character_arcs_repository import CharacterArcsRepository
from app.repository.plot_beat_repository import PlotBeatRepository
from app.models.models import Template
from app.services.background_jobs.tasks import add_template_creation_task_to_bg_jobs
from app.services.template_generator.template_manager import TemplateManager

class TemplateService:
    def __init__(self):
        self.template_repo = TemplateRepository()
        self.character_arc_repo = CharacterArcsRepository()
        self.plot_beat_repo = PlotBeatRepository()

    def create_template(self, book_id: int) -> dict:
        # Check if a template already exists for this book_id
        existing = self.template_repo.get_by_book_id(book_id)
        if existing:
            return {"error": f"A template already exists for book_id {book_id}", "template_id": existing.id}
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

        add_template_creation_task_to_bg_jobs(book_id, template_id)

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