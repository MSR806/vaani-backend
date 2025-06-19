from typing import List, Optional

from sqlalchemy.orm import Session

from ..models.enums import PromptSource
from ..models.models import Prompt


class PromptRepository:
    def __init__(self, db: Session):
        self.db = db

    def create(self, prompt: Prompt) -> Prompt:
        self.db.add(prompt)
        self.db.commit()
        self.db.refresh(prompt)
        return prompt

    def get_by_id(self, prompt_id: int) -> Optional[Prompt]:
        return self.db.query(Prompt).filter(Prompt.id == prompt_id).first()

    def get_all(self, source: Optional[PromptSource] = None) -> List[Prompt]:
        query = self.db.query(Prompt)
        if source:
            query = query.filter(Prompt.source == source)
        return query.all()

    def update(self, prompt: Prompt) -> Prompt:
        self.db.commit()
        self.db.refresh(prompt)
        return prompt

    def delete(self, prompt: Prompt) -> None:
        self.db.delete(prompt)
        self.db.commit()
