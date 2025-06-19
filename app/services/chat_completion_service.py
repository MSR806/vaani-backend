from fastapi import HTTPException
import json
from ..config import OPENAI_MODEL
from fastapi.responses import StreamingResponse
from ..models.models import Chapter
from sqlalchemy.orm import Session
from ..services.setting_service import get_setting_by_key
from ..services.ai_service import get_openai_client


async def stream_completion(
    context: str,
    user_prompt: str,
    db: Session = None,
    use_source_content: bool = False,
    chapter_id: int | None = None,
    book_id: int | None = None,
):
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
                user_prompt = (
                    f"Source Content: {chapter.source_text}\n\nUser Request: {user_prompt}"
                )

        # Prepare the messages for GPT
        messages = [
            {
                "role": "system",
                "content": "You are a creative writing assistant. Your task is to follow user prompt. Write in a natural, engaging style that matches the existing narrative. Keep the content concise and to the point unless the user prompt asks for more details.",
            },
            {
                "role": "user",
                "content": f"Context: {context}\n\nUser Prompt: {user_prompt}, \n\nOnly output the answer, do not include any additional text.",
            },
        ]

        # Create streaming response
        async def generate():
            try:
                # If db is provided, get settings from database
                if db:
                    # Get AI model and temperature settings
                    model = get_setting_by_key(db, "chapter_select_and_replace_ai_model").value
                    temperature = float(
                        get_setting_by_key(db, "chapter_select_and_replace_temperature").value
                    )
                else:
                    # Use provided model if available, otherwise use default
                    model = OPENAI_MODEL
                    temperature = 0.7

                client = get_openai_client(model)

                stream = client.chat.completions.create(
                    model=model, messages=messages, stream=True, temperature=temperature
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
