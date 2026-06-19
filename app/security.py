import logging
from typing import Optional

import httpx
from fastapi import Request

from app.config import settings

logger = logging.getLogger(__name__)

_TURNSTILE_URL = "https://challenges.cloudflare.com/turnstile/v0/siteverify"


def get_client_ip(request: Request) -> str:
    forwarded_for = request.headers.get("x-forwarded-for")
    if forwarded_for:
        return forwarded_for.split(",")[0].strip()
    if request.client:
        return request.client.host
    return "unknown"


async def verify_turnstile(token: str, remote_ip: Optional[str] = None) -> bool:
    if not token:
        return False

    payload: dict[str, str] = {
        "secret": settings.turnstile_secret_key,
        "response": token,
    }
    if remote_ip:
        payload["remoteip"] = remote_ip

    try:
        async with httpx.AsyncClient() as client:
            resp = await client.post(
                _TURNSTILE_URL,
                data=payload,
                timeout=5.0,
            )
            resp.raise_for_status()
            return bool(resp.json().get("success", False))
    except (httpx.HTTPError, ValueError) as exc:
        logger.warning("Turnstile verification failed: %s", type(exc).__name__)
        return False
