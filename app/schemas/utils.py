from pydantic import BaseModel


class BooleanResponse(BaseModel):
    success: bool
    message: str
