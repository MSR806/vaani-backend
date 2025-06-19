from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from ..database import get_db
from ..schemas.schemas import ChatRequest, CompletionRequest
from ..services.chat_service import (
    stream_chat,
    chat_as_character,
    stream_chat_as_character,
)
from ..services.chat_completion_service import stream_completion
from ..services.ai_service import get_openai_client
from ..auth import require_write_permission

router = APIRouter(tags=["chat"])


@router.post("/chat/stream")
async def stream_chat_route(
    request: ChatRequest, current_user: dict = Depends(require_write_permission)
):
    try:
        return await stream_chat(request)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/chat/character")
async def chat_as_character_route(
    request: ChatRequest,
    db: Session = Depends(get_db),
    current_user: dict = Depends(require_write_permission),
):
    return await chat_as_character(request, db)


@router.post("/chat/character/stream")
async def stream_chat_as_character_route(
    request: ChatRequest,
    db: Session = Depends(get_db),
    current_user: dict = Depends(require_write_permission),
):
    try:
        return await stream_chat_as_character(request, db)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/complete")
async def stream_completion_route(
    request: CompletionRequest,
    db: Session = Depends(get_db),
    current_user: dict = Depends(require_write_permission),
):
    try:
        return await stream_completion(
            request.context,
            request.user_prompt,
            db,
            request.use_source_content,
            request.chapter_id,
            request.book_id,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
