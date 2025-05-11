from .base_repository import BaseRepository
from app.models.models import Template

class TemplateRepository(BaseRepository[Template]):
    def create(self, name, book_id, summary_status, character_arc_status, plot_beats_status, character_arc_template_status, plot_beat_template_status):
        template = Template(
            name=name,
            book_id=book_id,
            summary_status=summary_status,
            character_arc_status=character_arc_status,
            plot_beats_status=plot_beats_status,
            character_arc_template_status=character_arc_template_status,
            plot_beat_template_status=plot_beat_template_status
        )
        self.db.add(template)
        self.db.commit()
        self.db.refresh(template)
        return template
    
    def update_summary_status(self, template_id, status):
        template = self.db.query(Template).filter(Template.id == template_id).first()
        template.summary_status = status
        self.db.commit()
        self.db.refresh(template)
        return template
