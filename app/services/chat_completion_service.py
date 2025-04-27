from fastapi import HTTPException
from openai import OpenAI
from ..config import OPENAI_MODEL
import json
from fastapi.responses import StreamingResponse
from ..models.models import Chapter
from sqlalchemy.orm import Session


async def stream_completion(
    context: str,
    user_prompt: str,
    client: OpenAI,
    db: Session = None,
    use_source_content: bool = False,
    chapter_id: int | None = None,
    book_id: int | None = None,
):
    if not client.api_key:
        raise HTTPException(status_code=500, detail="OpenAI API key not configured")

    try:
        # If use_source_content is True, get the chapter's source_text
        if use_source_content and db and chapter_id and book_id:
            chapter = (
                db.query(Chapter)
                .filter(Chapter.id == chapter_id, Chapter.book_id == book_id)
                .first()
            )
            if chapter and chapter.source_text:
                # Append source text to the prompt
                user_prompt = f"Source Content: {chapter.source_text}\n\nUser Request: {user_prompt}"

        # Prepare the messages for GPT
        messages = [
            {
                "role": "system",
                "content": "You are a creative writing assistant. Your task is to continue the story based on the provided context and user prompt. Write in a natural, engaging style that matches the existing narrative. Keep the content concise and to the point unless the user prompt asks for more details.",
            },
            {
                "role": "user",
                "content": f"Context: {context}\n\nUser Prompt: {user_prompt}\n\nPlease continue the story:",
            },
        ]

        # Create streaming response
        async def generate():
            try:
                stream = client.chat.completions.create(
                    model=OPENAI_MODEL, messages=messages, stream=True, temperature=0.7
                )

                for chunk in stream:
                    if (
                        hasattr(chunk.choices[0].delta, "content")
                        and chunk.choices[0].delta.content
                    ):
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
                "X-Accel-Buffering": "no",
            },
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
