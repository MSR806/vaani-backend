from typing import Optional, Tuple

from openai import OpenAI
from portkey_ai import PORTKEY_GATEWAY_URL, createHeaders

from ..config import ENV, OPENAI_API_KEY, PORTKEY_API_KEY, XAI_API_KEY


def get_headers(model: str | None = None) -> Tuple[str, Optional[str]]:
    # Check if it's a Grok model
    virtual_key = OPENAI_API_KEY
    if model and model.startswith("grok"):
        virtual_key = XAI_API_KEY

    # Default to OpenAI
    headers = createHeaders(
        api_key=PORTKEY_API_KEY,
        virtual_key=virtual_key,
        metadata={"env": ENV, "user_id": "raghu_1282"},
    )
    return headers


def get_openai_client(model: str | None = None):
    headers = get_headers(model)

    return OpenAI(base_url=PORTKEY_GATEWAY_URL, default_headers=headers)
