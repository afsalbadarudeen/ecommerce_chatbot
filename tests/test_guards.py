import pytest
from fastapi import HTTPException

from app.guards import count_tokens, enforce_query_length


# --- count_tokens ---

def test_count_tokens_short_string():
    # "hello" is a single token in gpt-4o-mini (cl100k_base)
    assert count_tokens("hello", "gpt-4o-mini") == 1


def test_count_tokens_unknown_model_falls_back():
    # Unknown model must not raise; should fall back to cl100k_base
    n = count_tokens("hello world", "unknown-model-xyz")
    assert n > 0


# --- enforce_query_length ---

def test_enforce_passes_short_message(monkeypatch):
    monkeypatch.setattr("app.guards.count_tokens", lambda t, m: 10)
    enforce_query_length("Hi, what products do you have?", "gpt-4o-mini")


def test_enforce_passes_exactly_at_limit(monkeypatch):
    # == MAX_QUERY_TOKENS (200) is allowed; only strictly greater is rejected
    monkeypatch.setattr("app.guards.count_tokens", lambda t, m: 200)
    enforce_query_length("x", "gpt-4o-mini")


def test_enforce_rejects_over_limit(monkeypatch):
    monkeypatch.setattr("app.guards.count_tokens", lambda t, m: 201)
    with pytest.raises(HTTPException) as exc_info:
        enforce_query_length("x", "gpt-4o-mini")
    assert exc_info.value.status_code == 400


def test_enforce_rejects_real_long_string():
    # 300 repetitions of "hello " is well over 200 tokens in any encoding
    long_text = "hello " * 300
    with pytest.raises(HTTPException) as exc_info:
        enforce_query_length(long_text, "gpt-4o-mini")
    assert exc_info.value.status_code == 400
