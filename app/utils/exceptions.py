from fastapi import HTTPException
from functools import wraps
from sqlalchemy.orm import Session
from typing import Callable, TypeVar, Any

F = TypeVar("F", bound=Callable[..., Any])

def rollback_on_exception(func: F) -> F:
    @wraps(func)
    def wrapper(*args, **kwargs):
        db: Session = kwargs.get("db") or next((a for a in args if isinstance(a, Session)), None)
        # If not found, check if first arg is self and has .db
        if not db and args:
            self_obj = args[0]
            db = getattr(self_obj, "db", None)
        if not db:
            raise ValueError("SQLAlchemy session (db: Session) is required")

        try:
            return func(*args, **kwargs)
        except Exception as e:
            db.rollback()
            raise
    return wrapper  # type: ignore

class StoryboardAlreadyExistsException(HTTPException):
    def __init__(self, book_id: int):
        super().__init__(status_code=400, detail={"type": "STORYBOARD_ALREADY_EXISTS", "message": f"A story board already exists for book_id {book_id}"})

class StoryboardNotFoundException(HTTPException):
    def __init__(self, book_id: int):
        super().__init__(status_code=404, detail={"type": "STORYBOARD_NOT_FOUND", "message": f"Story board not found for book_id {book_id}"})

class StoryboardCannotBeContinuedException(HTTPException):
    def __init__(self, book_id: int, status: str):
        super().__init__(status_code=400, detail={"type": "STORYBOARD_CANNOT_BE_CONTINUED", "message": f"Story board cannot be continued for book_id {book_id} with status {status}"})

class PlotBeatNotGeneratedException(HTTPException):
    def __init__(self):
        super().__init__(status_code=400, detail={"type": "PLOT_BEAT_NOT_GENERATED", "message": f"Plot beat not generated, first generate plot beats"})
    
class CharacterArcNotFoundException(HTTPException):
    def __init__(self, character_arc_id: int):
        super().__init__(status_code=404, detail={"type": "CHARACTER_ARC_NOT_FOUND", "message": f"Character arc not found for character_arc_id {character_arc_id}"})

class PlotBeatNotFoundException(HTTPException):
    def __init__(self, message: str):
        super().__init__(status_code=404, detail={"type": "PLOT_BEAT_NOT_FOUND", "message": message})
