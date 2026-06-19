import tiktoken
from fastapi import HTTPException

from app.config import settings


def count_tokens(text: str, model: str) -> int:
    try:
        enc = tiktoken.encoding_for_model(model)
    except KeyError:
        enc = tiktoken.get_encoding("cl100k_base")
    return len(enc.encode(text))


def enforce_query_length(text: str, model: str) -> None:
    n = count_tokens(text, model)
    if n > settings.max_query_tokens:
        raise HTTPException(
            status_code=400,
            detail="Message too long. Please shorten your question.",
        )
