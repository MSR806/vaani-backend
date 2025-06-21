from typing import List

from fastapi import Depends, HTTPException
from sqlalchemy.orm import Session

from app.auth import require_write_permission
from app.database import get_db
from app.metrics.router import MetricsRouter
from app.schemas.schemas import TemplateRead
from app.services.template_service import TemplateService

router = MetricsRouter(tags=["templates"])


@router.post("/templates", response_model=dict)
def create_template_route(
    template_data: dict,
    db: Session = Depends(get_db),
    current_user: dict = Depends(require_write_permission),
):
    book_id = template_data.get("book_id")
    name = template_data.get("name")
    if not book_id:
        raise HTTPException(status_code=400, detail="book_id is required")
    if not name:
        raise HTTPException(status_code=400, detail="name is required")
    service = TemplateService(db)
    return service.create_template(book_id, name)


@router.get("/templates", response_model=List[TemplateRead])
def get_templates_route(db: Session = Depends(get_db)):
    service = TemplateService(db)
    return service.get_templates()


@router.get("/templates/{template_id}")
def get_template_details_route(template_id: int, db: Session = Depends(get_db)):
    service = TemplateService(db)
    result = service.get_template_details(template_id)
    if not result:
        raise HTTPException(status_code=404, detail="Template not found")
    return result


@router.get("/templates/{template_id}/status")
def get_template_status_route(template_id: int, db: Session = Depends(get_db)):
    service = TemplateService(db)
    template = service.get_template_row(template_id)
    if not template:
        raise HTTPException(status_code=404, detail="Template not found")
    return template
