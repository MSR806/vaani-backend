from pydantic import BaseModel

class StoryboardCreate(BaseModel):
    book_id: int
    template_id: int
    prompt: str

class StoryboardResponse(BaseModel):
    id: int
    book_id: int
    template_id: int
    prompt: str
    status: str
    created_at: int
    updated_at: int
    created_by: str
    updated_by: str
