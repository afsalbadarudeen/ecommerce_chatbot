# ShopNest Support Chatbot

A stateless customer-support chatbot for ShopNest. The backend is FastAPI + OpenAI function-calling + pandas. Conversation history lives only in the browser; the server never stores it.

---

## Local setup

**Prerequisites:** Python 3.11, a virtual environment tool (venv / pyenv).

```bash
# 1. Create and activate a virtual environment
python3.11 -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate

# 2. Install dependencies
pip install -r requirements.txt

# 3. Copy the example env file and fill in your secrets (see below)
cp .env.example .env

# 4. Start the dev server
uvicorn app.main:app --reload --port 8000
```

Open http://localhost:8000 in your browser.

---

## Environment variables

Copy `.env.example` to `.env` and set each value:

| Variable | Where to get it | Notes |
|---|---|---|
| `OPENAI_API_KEY` | platform.openai.com → API keys | Required |
| `OPENAI_MODEL` | — | Default `gpt-4o-mini`; change to `gpt-4o` for higher quality |
| `UPSTASH_REDIS_REST_URL` | Upstash console → REST API | See below |
| `UPSTASH_REDIS_REST_TOKEN` | Upstash console → REST API | See below |
| `TURNSTILE_SECRET_KEY` | Cloudflare dashboard → Turnstile | See below |
| `TURNSTILE_SITE_KEY` | Cloudflare dashboard → Turnstile | See below |
| `ALLOWED_ORIGINS` | — | Comma-separated; use `http://localhost:8000` locally, your Render URL in production |
| `DAILY_TOKEN_LIMIT` | — | Default `10000`; max tokens one IP can use per day |
| `MAX_QUERY_TOKENS` | — | Default `200`; max tokens in a single user message |
| `GLOBAL_DAILY_TOKEN_LIMIT` | — | Default `500000`; hard cap across all IPs for bill protection |

### Getting an Upstash Redis database

1. Go to [upstash.com](https://upstash.com) and create a free account.
2. Click **Create Database** → choose a region close to your Render deployment.
3. Open the database → **REST API** tab.
4. Copy **UPSTASH_REDIS_REST_URL** and **UPSTASH_REDIS_REST_TOKEN** into your `.env`.

The free tier allows 10 000 commands/day and 256 MB storage — sufficient for rate-limit keys.

### Getting Cloudflare Turnstile keys

1. Go to the [Cloudflare dashboard](https://dash.cloudflare.com) → **Turnstile** (left sidebar).
2. Click **Add widget** → give it a name → add your site's domain (e.g. `your-app.onrender.com`).
3. Choose **Managed** mode.
4. Copy the **Site Key** → `TURNSTILE_SITE_KEY` (public, shown in the widget).
5. Copy the **Secret Key** → `TURNSTILE_SECRET_KEY` (server-side only, never commit it).

For local development only, you can use Cloudflare's always-pass test keys:
- `TURNSTILE_SITE_KEY=1x00000000000000000000AA`
- `TURNSTILE_SECRET_KEY=1x0000000000000000000000000000000AA`

### OpenAI billing warning

OpenAI charges per token. **Set a monthly spend limit** before going live:
platform.openai.com → Settings → Billing → Usage limits.

`GLOBAL_DAILY_TOKEN_LIMIT` (default 500 000 tokens ≈ $0.075/day at gpt-4o-mini pricing) provides a server-side safety net, but a dashboard limit is the only hard billing cap.

---

## Deploying to Render

This repo includes `render.yaml` which Render picks up automatically.

1. Push the repo to GitHub (or GitLab).
2. Go to [render.com](https://render.com) → **New** → **Blueprint** → connect your repo.
3. Render reads `render.yaml` and creates the service with all env var slots pre-filled as **empty** (because every var is `sync: false` — meaning Render will never commit values to your repo).
4. In the Render dashboard → your service → **Environment**, add each variable:

| Variable | Value |
|---|---|
| `OPENAI_API_KEY` | your OpenAI key |
| `OPENAI_MODEL` | `gpt-4o-mini` |
| `UPSTASH_REDIS_REST_URL` | from Upstash console |
| `UPSTASH_REDIS_REST_TOKEN` | from Upstash console |
| `TURNSTILE_SECRET_KEY` | from Cloudflare dashboard |
| `TURNSTILE_SITE_KEY` | from Cloudflare dashboard |
| `ALLOWED_ORIGINS` | `https://your-app.onrender.com` |
| `DAILY_TOKEN_LIMIT` | `10000` |
| `MAX_QUERY_TOKENS` | `200` |
| `GLOBAL_DAILY_TOKEN_LIMIT` | `500000` |

5. Click **Save changes** — Render redeploys automatically.
6. The `/health` endpoint is used by Render's health checker. If it returns `{"status":"ok"}` the deploy is live.

> **Free tier note:** Render free services spin down after 15 minutes of inactivity. The first request after a cold start may take 30–60 seconds.

---

## Running tests

```bash
pytest -q                                      # all tests
pytest -q tests/test_tools.py                  # product search only
pytest -q tests/test_guards.py                 # token-length guard only
```

Tests use stub env vars defined in `conftest.py` and mock the product DataFrame — no real API calls are made.

## Linting

```bash
ruff check .
```
