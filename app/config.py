from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )

    # OpenAI
    openai_api_key: str
    openai_model: str = "gpt-4o-mini"

    # Upstash Redis
    upstash_redis_rest_url: str
    upstash_redis_rest_token: str

    # Cloudflare Turnstile
    turnstile_secret_key: str
    # Public sitekey shown in the widget — not secret; safe to expose via /config
    turnstile_site_key: str = "1x00000000000000000000AA"  # Cloudflare always-pass test key

    # CORS — comma-separated string; split into a list in main.py when mounting middleware
    allowed_origins: str = ""

    # Token limits
    daily_token_limit: int = 10_000
    max_query_tokens: int = 200
    global_daily_token_limit: int = 500_000


settings = Settings()
