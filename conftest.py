import os

# Stub secrets so app/config.py can instantiate Settings() during tests
# without a real .env file. Tests that exercise these values should mock them.
os.environ.setdefault("OPENAI_API_KEY", "test-key")
os.environ.setdefault("UPSTASH_REDIS_REST_URL", "https://test.upstash.io")
os.environ.setdefault("UPSTASH_REDIS_REST_TOKEN", "test-token")
os.environ.setdefault("TURNSTILE_SECRET_KEY", "1x0000000000000000000000000000000AA")
os.environ.setdefault("ALLOWED_ORIGINS", "http://localhost:8000")
