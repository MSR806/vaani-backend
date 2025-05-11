from .base_repository import BaseRepository
from app.models.models import Template
from sqlalchemy.orm import Session
from typing import Optional

class TemplateRepository(BaseRepository[Template]):
    def __init__(self, db: Optional[Session] = None):
        super().__init__(db)

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
        template = self.get_by_id(template_id)
        template.summary_status = status
        self.db.commit()
        self.db.refresh(template)
        return template
        
    def update_character_arc_status(self, template_id, status):
        template = self.get_by_id(template_id)
        template.character_arc_status = status
        self.db.commit()
        self.db.refresh(template)
        return template
    
    def update_plot_beats_status(self, template_id, status):
        template = self.get_by_id(template_id)
        template.plot_beats_status = status
        self.db.commit()
        self.db.refresh(template)
        return template
        
    def update_character_arc_template_status(self, template_id, status):
        template = self.get_by_id(template_id)
        template.character_arc_template_status = status
        self.db.commit()
        self.db.refresh(template)
        return template
        
    def update_plot_beat_template_status(self, template_id, status):
        template = self.get_by_id(template_id)
        template.plot_beat_template_status = status
        self.db.commit()
        self.db.refresh(template)
        return template
    
    def get_all_templates(self):
        return self.db.query(Template).all()

    def get_by_id(self, template_id):
        return self.db.query(Template).filter(Template.id == template_id).first()

    def get_by_book_id(self, book_id: int):
        return self.db.query(Template).filter(Template.book_id == book_id).first()
        