import logging
from typing import Literal

from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.config import settings
from app.data import get_company_info
from app.guards import enforce_query_length
from app.llm import chat
from app.rate_limit import check_budget, record_usage
from app.security import get_client_ip, verify_turnstile

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# App
# ---------------------------------------------------------------------------

app = FastAPI(docs_url=None, redoc_url=None)  # no public docs

# CORS — never wildcard; empty list = no cross-origin access
_origins = [o.strip() for o in settings.allowed_origins.split(",") if o.strip()]
app.add_middleware(
    CORSMiddleware,
    allow_origins=_origins,
    allow_methods=["GET", "POST"],
    allow_headers=["Content-Type"],
)

# ---------------------------------------------------------------------------
# Exception handlers — ensure no stack traces or internals reach the client
# ---------------------------------------------------------------------------

@app.exception_handler(StarletteHTTPException)
async def _http_handler(request: Request, exc: StarletteHTTPException) -> JSONResponse:
    return JSONResponse(status_code=exc.status_code, content={"detail": exc.detail})


@app.exception_handler(RequestValidationError)
async def _validation_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
    return JSONResponse(status_code=422, content={"detail": "Invalid request format."})


@app.exception_handler(Exception)
async def _generic_handler(request: Request, exc: Exception) -> JSONResponse:
    logger.error("Unhandled exception type=%s", type(exc).__name__)
    return JSONResponse(
        status_code=500,
        content={"detail": "An unexpected error occurred. Please try again."},
    )

# ---------------------------------------------------------------------------
# Pydantic models
# ---------------------------------------------------------------------------

class Message(BaseModel):
    role: Literal["user", "assistant"]
    content: str = Field(min_length=1)


class ChatRequest(BaseModel):
    messages: list[Message] = Field(min_length=1)
    turnstile_token: str = Field(min_length=1)


class ChatResponse(BaseModel):
    reply: str

# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

@app.get("/health")
async def health() -> dict:
    return {"status": "ok"}


@app.get("/config")
async def public_config() -> dict:
    """Expose non-secret config the frontend needs at runtime."""
    return {
        "turnstile_site_key": settings.turnstile_site_key,
        "company_name": get_company_info().get("name", "ShopNest"),
    }


@app.post("/chat", response_model=ChatResponse)
async def chat_endpoint(body: ChatRequest, request: Request) -> ChatResponse:
    # 1. Extract IP (synchronous header read — done first so Turnstile gets it)
    ip = get_client_ip(request)

    # 2. Verify Cloudflare Turnstile — reject bots before any further work
    if not await verify_turnstile(body.turnstile_token, ip):
        raise HTTPException(status_code=403, detail="Request verification failed.")

    # 3. Per-IP and global daily token budget (fail closed if Upstash is down)
    await check_budget(ip)

    # 4. Reject single messages that exceed the per-query token cap
    latest_user = next(
        (m for m in reversed(body.messages) if m.role == "user"),
        None,
    )
    if latest_user is None:
        raise HTTPException(status_code=400, detail="No user message provided.")
    enforce_query_length(latest_user.content, settings.openai_model)

    # 5 & 6. LLM call with tool-calling loop (search_products handled inside)
    history = [m.model_dump() for m in body.messages]
    try:
        result = await chat(history)
    except Exception:
        logger.error("LLM call failed")
        raise HTTPException(
            status_code=500,
            detail="Something went wrong. Please try again.",
        )

    # 7. Record combined token usage; fail closed if Upstash is unreachable
    await record_usage(ip, result.input_tokens + result.output_tokens)

    # 8. Return the reply — nothing is persisted
    logger.info(
        "chat status=ok input_tokens=%d output_tokens=%d",
        result.input_tokens,
        result.output_tokens,
    )
    return ChatResponse(reply=result.text)


# ---------------------------------------------------------------------------
# Static files — mounted last so API routes take priority
# html=True serves index.html for unmatched paths (SPA client-side routing)
# ---------------------------------------------------------------------------

app.mount("/", StaticFiles(directory="static", html=True), name="static")
