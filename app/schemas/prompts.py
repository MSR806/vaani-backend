from pydantic import BaseModel
from ..models.enums import PromptSource


class PromptBase(BaseModel):
    title: str
    content: str
    source: PromptSource


class PromptCreate(PromptBase):
    pass


class PromptUpdate(BaseModel):
    title: str | None = None
    content: str | None = None
    source: PromptSource | None = None


class PromptResponse(PromptBase):
    id: int
    created_at: int
    updated_at: int
    created_by: str
    updated_by: str
    
    class Config:
        from_attributes = True
