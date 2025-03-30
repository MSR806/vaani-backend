from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from ..database import get_db
from ..schemas.schemas import ChatRequest, ChatResponse
from ..services.chat_service import chat_with_ai, chat_as_character, stream_chat, stream_chat_as_character
from ..services.ai_service import get_openai_client
from ..config import OPENAI_API_KEY
import json
from fastapi.responses import StreamingResponse

router = APIRouter()

@router.post("/chat", response_model=ChatResponse)
async def chat_with_ai_endpoint(request: ChatRequest):
    if not OPENAI_API_KEY:
        raise HTTPException(status_code=500, detail="OpenAI API key not configured")
    
    try:
        response = chat_with_ai(request.messages, request.system_prompt)
        return ChatResponse(message=response)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/chat/stream")
async def stream_chat_endpoint(request: ChatRequest):
    if not OPENAI_API_KEY:
        raise HTTPException(status_code=500, detail="OpenAI API key not configured")
    
    try:
        async def generate():
            try:
                stream = await stream_chat(request.messages, request.system_prompt)
                
                for chunk in stream:
                    if chunk.choices[0].delta.content:
                        yield f"data: {json.dumps({'content': chunk.choices[0].delta.content})}\n\n"
                
                yield "data: [DONE]\n\n"
            except Exception as e:
                yield f"data: {json.dumps({'error': str(e)})}\n\n"
                yield "data: [DONE]\n\n"

        return StreamingResponse(
            generate(),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "X-Accel-Buffering": "no"
            }
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/chat/character", response_model=ChatResponse)
async def chat_as_character_endpoint(request: ChatRequest, db: Session = Depends(get_db)):
    if not OPENAI_API_KEY:
        raise HTTPException(status_code=500, detail="OpenAI API key not configured")
    
    if not request.character_name or not request.chapter_id:
        raise HTTPException(status_code=400, detail="character_name and chapter_id are required")
    
    try:
        response = chat_as_character(request.messages, request.character_name, request.chapter_id, db)
        return ChatResponse(message=response)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/chat/character/stream")
async def stream_chat_as_character_endpoint(request: ChatRequest, db: Session = Depends(get_db)):
    if not OPENAI_API_KEY:
        raise HTTPException(status_code=500, detail="OpenAI API key not configured")
    
    if not request.character_name or not request.chapter_id:
        raise HTTPException(status_code=400, detail="character_name and chapter_id are required")
    
    try:
        async def generate():
            try:
                stream = await stream_chat_as_character(request.messages, request.character_name, request.chapter_id, db)
                
                for chunk in stream:
                    if chunk.choices[0].delta.content:
                        yield f"data: {json.dumps({'content': chunk.choices[0].delta.content})}\n\n"
                
                yield "data: [DONE]\n\n"
            except Exception as e:
                yield f"data: {json.dumps({'error': str(e)})}\n\n"
                yield "data: [DONE]\n\n"

        return StreamingResponse(
            generate(),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "X-Accel-Buffering": "no"
            }
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) 