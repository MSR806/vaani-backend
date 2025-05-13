from fastapi import HTTPException

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
