from sqlalchemy.orm import Session
from ..models.models import Chapter
from ..schemas.schemas import ChatRequest, ChatResponse
from ..services.ai_service import get_openai_client, get_conversation_chain
from ..config import OPENAI_MODEL
import json
from fastapi.responses import StreamingResponse

async def chat_with_ai(request: ChatRequest):
    if not get_openai_client().api_key:
        raise Exception("OpenAI API key not configured")
    
    try:
        # Get the last user message
        last_user_message = None
        for msg in reversed(request.messages):
            if msg.role == "user":
                last_user_message = msg.content
                break
        
        if not last_user_message:
            raise Exception("No user message found in the request")
        
        # Use LangChain's conversation chain
        conversation = get_conversation_chain()
        response = conversation.predict(input=last_user_message)
        
        return ChatResponse(message=response)
        
    except Exception as e:
        raise Exception(str(e))

async def stream_chat(request: ChatRequest):
    if not get_openai_client().api_key:
        raise Exception("OpenAI API key not configured")
    
    try:
        # Get the last user message
        last_user_message = None
        for msg in reversed(request.messages):
            if msg.role == "user":
                last_user_message = msg.content
                break
        
        if not last_user_message:
            raise Exception("No user message found in the request")
        
        # Create messages for OpenAI
        messages = []
        if request.system_prompt:
            messages.append({"role": "system", "content": request.system_prompt})
        messages.append({"role": "user", "content": last_user_message})
        
        # Use OpenAI's streaming directly
        stream = get_openai_client().chat.completions.create(
            model=OPENAI_MODEL,
            messages=messages,
            stream=True,
            temperature=0.7
        )
        
        return await create_streaming_response(stream)
        
    except Exception as e:
        raise Exception(str(e))

async def chat_as_character(request: ChatRequest, db: Session):
    if not get_openai_client().api_key:
        raise Exception("OpenAI API key not configured")
    
    if not request.character_name or not request.chapter_id:
        raise Exception("character_name and chapter_id are required")
    
    try:
        # Get the chapter
        chapter = db.query(Chapter).filter(Chapter.id == request.chapter_id).first()
        if not chapter:
            raise Exception("Chapter not found")
        
        # Get the last user message
        last_user_message = None
        for msg in reversed(request.messages):
            if msg.role == "user":
                last_user_message = msg.content
                break
        
        if not last_user_message:
            raise Exception("No user message found in the request")
        
        # Prepare the messages for GPT
        messages = [
            {
                "role": "system",
                "content": f"""You are {request.character_name}, a character from the chapter "{chapter.title}".
                You should respond to messages as this character, maintaining their personality, knowledge, and context from the chapter.
                Stay in character at all times and respond based on what the character knows and how they would think and speak.
                If the character's gender or other characteristics are mentioned in the chapter, incorporate those into your responses.
                Keep responses concise and natural, as if you're actually the character speaking."""
            },
            {
                "role": "user",
                "content": f"""Chapter Title: {chapter.title}
                Chapter Content:
                {chapter.content}
                
                Now, respond to this message as {request.character_name}:
                {last_user_message}"""
            }
        ]
        
        response = get_openai_client().chat.completions.create(
            model=OPENAI_MODEL,
            messages=messages,
            temperature=0.7
        )
        
        return ChatResponse(message=response.choices[0].message.content)
        
    except Exception as e:
        raise Exception(str(e))

async def create_streaming_response(stream):
    """
    Creates a properly formatted streaming response from an OpenAI stream.
    """
    async def generate():
        try:
            for chunk in stream:
                if chunk.choices[0].delta.content:
                    yield f"data: {chunk.choices[0].delta.content}\n\n"
            
            yield "data: [DONE]\n\n"
        except Exception as e:
            yield f"data: error: {str(e)}\n\n"
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

async def stream_chat_as_character(request: ChatRequest, db: Session):
    if not get_openai_client().api_key:
        raise Exception("OpenAI API key not configured")
    
    if not request.character_name or not request.chapter_id:
        raise Exception("character_name and chapter_id are required")
    
    try:
        # Get the chapter
        chapter = db.query(Chapter).filter(Chapter.id == request.chapter_id).first()
        if not chapter:
            raise Exception("Chapter not found")
        
        # Get the last user message
        last_user_message = None
        for msg in reversed(request.messages):
            if msg.role == "user":
                last_user_message = msg.content
                break
        
        if not last_user_message:
            raise Exception("No user message found in the request")
        
        # Prepare the messages for GPT
        messages = [
            {
                "role": "system",
                "content": f"""You are {request.character_name}, a character from the chapter "{chapter.title}".
                You should respond to messages as this character, maintaining their personality, knowledge, and context from the chapter.
                Stay in character at all times and respond based on what the character knows and how they would think and speak.
                If the character's gender or other characteristics are mentioned in the chapter, incorporate those into your responses.
                Keep responses concise and natural, as if you're actually the character speaking."""
            },
            {
                "role": "user",
                "content": f"""Chapter Title: {chapter.title}
                Chapter Content:
                {chapter.content}
                
                Now, respond to this message as {request.character_name}:
                {last_user_message}"""
            }
        ]
        
        stream = get_openai_client().chat.completions.create(
            model=OPENAI_MODEL,
            messages=messages,
            stream=True,
            temperature=0.7
        )
        
        return await create_streaming_response(stream)
        
    except Exception as e:
        raise Exception(str(e)) 