import os
from openai import OpenAI


def get_openai_client(model: str | None = None):
    # Check if it's a Grok model
    if model and model.startswith("grok"):
        return OpenAI(api_key=os.getenv("XAI_API_KEY"), base_url="https://api.x.ai/v1")

    # Default to OpenAI
    return OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
