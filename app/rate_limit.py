import datetime
import logging

import httpx
from fastapi import HTTPException

from app.config import settings

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Key helpers
# ---------------------------------------------------------------------------

def _date_str() -> str:
    return datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%d")


def _seconds_until_midnight() -> int:
    now = datetime.datetime.now(datetime.timezone.utc)
    midnight = (now + datetime.timedelta(days=1)).replace(
        hour=0, minute=0, second=0, microsecond=0
    )
    return max(1, int((midnight - now).total_seconds()))


def _ip_key(ip: str) -> str:
    return f"tok:{ip}:{_date_str()}"


def _global_key() -> str:
    return f"tok:global:{_date_str()}"


# ---------------------------------------------------------------------------
# Upstash REST transport
# ---------------------------------------------------------------------------

async def _pipeline(commands: list[list]) -> list:
    """
    Execute a batch of Redis commands in one HTTP round-trip.
    Raises HTTPException(503) on any transport or Upstash error (fail closed).
    """
    try:
        async with httpx.AsyncClient() as client:
            resp = await client.post(
                f"{settings.upstash_redis_rest_url}/pipeline",
                headers={"Authorization": f"Bearer {settings.upstash_redis_rest_token}"},
                json=commands,
                timeout=5.0,
            )
            resp.raise_for_status()
    except httpx.HTTPError as exc:
        logger.warning("Upstash unreachable: %s", type(exc).__name__)
        raise HTTPException(status_code=503, detail="Service temporarily unavailable.")

    results = resp.json()
    for item in results:
        if "error" in item:
            logger.warning("Upstash pipeline error: %s", item["error"])
            raise HTTPException(status_code=503, detail="Service temporarily unavailable.")

    return [item["result"] for item in results]


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

async def check_budget(ip: str) -> None:
    """
    Read today's token counters for *ip* and globally.
    Raises HTTPException(429) if either limit is reached.
    Raises HTTPException(503) if Upstash is unreachable (fail closed).
    """
    ip_k = _ip_key(ip)
    global_k = _global_key()

    ip_used, global_used = await _pipeline([
        ["GET", ip_k],
        ["GET", global_k],
    ])

    if int(ip_used or 0) >= settings.daily_token_limit:
        raise HTTPException(
            status_code=429,
            detail="Daily limit reached. Please try again tomorrow.",
        )
    if int(global_used or 0) >= settings.global_daily_token_limit:
        raise HTTPException(
            status_code=429,
            detail="Service capacity reached. Please try again later.",
        )


async def record_usage(ip: str, tokens: int) -> None:
    """
    Atomically add *tokens* to today's per-IP and global counters.
    Sets the TTL to expire at midnight UTC so keys self-clean.
    Raises HTTPException(503) if Upstash is unreachable (fail closed).
    """
    ip_k = _ip_key(ip)
    global_k = _global_key()
    ttl = _seconds_until_midnight()

    await _pipeline([
        ["INCRBY", ip_k,     tokens],
        ["EXPIRE", ip_k,     ttl],
        ["INCRBY", global_k, tokens],
        ["EXPIRE", global_k, ttl],
    ])
