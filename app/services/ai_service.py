from openai import OpenAI
from typing import Tuple, Optional
from ..config import OPENAI_API_KEY, XAI_API_KEY


def get_api_config(model: str | None = None) -> Tuple[str, Optional[str]]:
    # Check if it's a Grok model
    if model and model.startswith("grok"):
        return XAI_API_KEY, "https://api.x.ai/v1"
    
    # Default to OpenAI
    return OPENAI_API_KEY, None


def get_openai_client(model: str | None = None):
    api_key, base_url = get_api_config(model)
    
    if base_url:
        return OpenAI(api_key=api_key, base_url=base_url)
    else:
        return OpenAI(api_key=api_key)
