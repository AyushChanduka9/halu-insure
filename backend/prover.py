"""
Prover module — real AI answers via Groq (OpenAI-compatible Chat API).

Flow (high level):
  1. `mock_prove_query` is what FastAPI `/query` still calls (main.py unchanged).
  2. It calls `generate_answer(question)`, which asks Groq for a short JSON object.
  3. We parse that JSON and validate it with Pydantic (correct types, confidence 0–1).
  4. If anything goes wrong (no key, network error, bad JSON), we use a safe fallback.
  5. Extra fields on the HTTP response (`evidence`, `tx_hash`, etc.) stay mocked for now —
     only the answer + confidence come from the model.

Groq docs (base URL & models): https://console.groq.com/docs/openai

Important: Groq sits behind Cloudflare. The default Python `urllib` User-Agent is often blocked
(HTTP 403, error code 1010). We send a normal `User-Agent` header on every request — see `_API_USER_AGENT`.
"""

from __future__ import annotations

import json
import logging
import os
import re
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field, ValidationError, field_validator

from models import QueryResponse

# -----------------------------------------------------------------------------
# Logging (temporary diagnostics — flip _PROVER_DEBUG to False when stable)
# -----------------------------------------------------------------------------

_LOGGER = logging.getLogger(__name__)

# Set to False to silence detailed prover diagnostics (fallback behavior unchanged).
_PROVER_DEBUG = True


def _dbg(msg: str, *args: Any) -> None:
    """Log a debug line only when _PROVER_DEBUG is True."""
    if _PROVER_DEBUG:
        _LOGGER.info("[prover] " + msg, *args)


def _masked_key_preview(api_key: str) -> str:
    """
    Show whether a key looks present without leaking it.

    User asked for a hint from the first ~10 characters, masked:
    we keep the first 3 characters and mask the rest of that window.
    """
    if len(api_key) <= 3:
        return "len=<too_short_to_preview_safely>"
    window = api_key[:10]
    masked_window = api_key[:3] + "*" * (len(window) - 3)
    suffix = "…" if len(api_key) > 10 else ""
    return f"len={len(api_key)} first10_masked={masked_window!s}{suffix!s}"


# -----------------------------------------------------------------------------
# Configuration
# -----------------------------------------------------------------------------

# Verified against Groq OpenAI-compat docs / models page.
_GROQ_CHAT_URL = "https://api.groq.com/openai/v1/chat/completions"

_DEFAULT_MODEL = "llama-3.3-70b-versatile"

# Cloudflare rejects the default User-Agent sent by urllib ("Python-urllib/3.x")
# with HTTP 403 error 1010. Use any explicit, descriptive client string instead.
_API_USER_AGENT = "Halu-Insure-Prover/0.1 (+local dev; FastAPI)"

# Absolute path used for `.env` (logged once at import).
_DOTENV_RESOLVED_PATH = Path(__file__).resolve().parent / ".env"

# When the API or parsing fails, we return this instead of crashing the server.
_FALLBACK_MESSAGE = (
    "I could not produce a verified answer right now. "
    "Please check GROQ_API_KEY, your network connection, or try again in a moment."
)


# -----------------------------------------------------------------------------
# Env: load backend/.env (sets GROQ_API_KEY alongside any other vars you keep there)
# -----------------------------------------------------------------------------


def _load_env_from_dotenv_file() -> None:
    """
    Load variables from backend/.env into os.environ.

    Does not overwrite keys already set in the environment (so CI / hosting wins).
    """
    env_path = _DOTENV_RESOLVED_PATH
    if not env_path.is_file():
        _dbg(".env path (expected): %s — file_exists=False", env_path)
        return
    keys_loaded = 0
    try:
        for raw_line in env_path.read_text(encoding="utf-8").splitlines():
            line = raw_line.strip()
            if not line or line.startswith("#"):
                continue
            if "=" not in line:
                continue
            key, _, value = line.partition("=")
            key = key.strip()
            value = value.strip().strip('"').strip("'")
            if key and key not in os.environ:
                os.environ[key] = value
                keys_loaded += 1
        _dbg(
            ".env path: %s — file_exists=True — lines_written_to_environ=%s (only keys not already set)",
            env_path,
            keys_loaded,
        )
    except OSError as exc:
        _dbg("Could not read .env at %s: %s", env_path, exc)


_load_env_from_dotenv_file()


# After load — key visibility diagnostics (masked).
_groq_key_present = bool(os.environ.get("GROQ_API_KEY"))
_dbg(
    "GROQ_API_KEY detected=%s preview=%s",
    _groq_key_present,
    _masked_key_preview(os.environ["GROQ_API_KEY"]) if _groq_key_present else "n/a",
)
_dbg(
    "Groq config check: endpoint=%s model=%s user_agent_header=%s",
    _GROQ_CHAT_URL,
    _DEFAULT_MODEL,
    _API_USER_AGENT.split(";", 1)[0] + "...",
)


# -----------------------------------------------------------------------------
# JSON shape from the model (validated with Pydantic)
# -----------------------------------------------------------------------------


class AIModelAnswer(BaseModel):
    """
    The model must reply with JSON matching this exactly:
      { "answer": "...", "confidence": 0.0–1.0 }
    """

    answer: str = Field(..., min_length=1, description='Main answer text')
    confidence: float = Field(..., ge=0.0, le=1.0, description='0.0 = unsure, 1.0 = very sure')

    @field_validator('confidence', mode='before')
    @classmethod
    def _coerce_confidence(cls, value: object) -> object:
        """
        Sometimes models emit 85 instead of 0.85. Accept 0–100 and normalize once.
        """
        if isinstance(value, (int, float)):
            x = float(value)
            if x > 1.0 and x <= 100.0:
                x = x / 100.0
            return x
        return value


def _extract_json_object(text: str) -> dict:
    """Strip optional ```json fences and parse the first JSON object."""
    cleaned = text.strip()
    fence = re.search(r'```(?:json)?\s*([\s\S]*?)```', cleaned, re.IGNORECASE)
    if fence:
        cleaned = fence.group(1).strip()
    return json.loads(cleaned)


def _groq_chat_json_content(
    *,
    system_prompt: str,
    user_message: str,
    model: str = _DEFAULT_MODEL,
    timeout_seconds: int = 60,
) -> str:
    """
    Call Groq's Chat Completions API (OpenAI-compatible) and return assistant `content`.

    Uses JSON Object mode (`response_format`) plus our system prompt — same pattern as Groq docs.
    """
    api_key = os.environ.get('GROQ_API_KEY')
    if not api_key:
        raise ValueError(
            'GROQ_API_KEY is missing — add it to backend/.env or export it in your shell.'
        )

    payload: dict = {
        'model': model,
        'messages': [
            {'role': 'system', 'content': system_prompt},
            {'role': 'user', 'content': user_message},
        ],
        'response_format': {'type': 'json_object'},
        'temperature': 0.2,
    }

    data = json.dumps(payload).encode('utf-8')
    request_obj = urllib.request.Request(
        _GROQ_CHAT_URL,
        data=data,
        headers={
            'Authorization': f'Bearer {api_key}',
            'Content-Type': 'application/json',
            'User-Agent': _API_USER_AGENT,
        },
        method='POST',
    )

    try:
        with urllib.request.urlopen(request_obj, timeout=timeout_seconds) as resp:
            raw_body = resp.read().decode('utf-8')
            _dbg("Groq HTTP status=%s bytes=%s", getattr(resp, "status", 200), len(raw_body))
    except urllib.error.HTTPError as exc:
        err_body = b''
        try:
            err_body = exc.read()
        except OSError as read_exc:
            _dbg("Groq HTTPError: could not read error body: %s", read_exc)
        snippet = err_body.decode('utf-8', errors='replace')[:2000]
        _dbg(
            "Groq request failed HTTP status=%s raw_error_body(first 2000 chars)=%r",
            exc.code,
            snippet,
        )
        raise

    try:
        parsed = json.loads(raw_body)
    except json.JSONDecodeError as exc:
        _dbg(
            "JSONDecodeError parsing Groq HTTP body (not valid JSON): %s snippet=%r",
            exc,
            (raw_body[:1200] + "…") if len(raw_body) > 1200 else raw_body,
        )
        raise
    try:
        return parsed['choices'][0]['message']['content']
    except (KeyError, IndexError, TypeError) as exc:
        _dbg("Unexpected Groq JSON shape keys sample=%r err=%s", parsed, exc)
        raise ValueError(f'Unexpected Groq response shape: {parsed!r}') from exc


def generate_answer(question: str) -> AIModelAnswer:
    """
    Ask Groq for an answer plus a confidence score (0.0–1.0).

    Returns a validated AIModelAnswer, or on failure returns a deterministic fallback
    (same friendly message + confidence 0.0) instead of raising to the caller.
    """
    system_prompt = """You are Halu-Insure's factual assistant.

You MUST respond with a single JSON object and nothing else (no markdown, no prose outside JSON).
Use this exact schema:
{"answer":"<string>","confidence":<number>}

Rules:
- "answer": clear, helpful, concise plain text answering the user's question.
- "confidence": a float strictly between 0.0 and 1.0 inclusive (how sure you are).
- Never invent citations or pretend you browsed the web unless the user explicitly asked for fiction — be honest when uncertain (use a lower confidence).
"""

    trimmed = question.strip()
    if not trimmed:
        return AIModelAnswer(answer='Please provide a non-empty question.', confidence=0.0)

    try:
        raw_content = _groq_chat_json_content(system_prompt=system_prompt, user_message=trimmed)
        if raw_content is None:
            _dbg('Groq assistant content is None (unexpected)')
            return AIModelAnswer(answer=_FALLBACK_MESSAGE, confidence=0.0)

        try:
            blob = _extract_json_object(raw_content)
        except json.JSONDecodeError as exc:
            _dbg(
                "JSONDecodeError parsing model content: %s snippet=%r",
                exc,
                (raw_content[:1200] + '…') if len(raw_content) > 1200 else raw_content,
            )
            return AIModelAnswer(answer=_FALLBACK_MESSAGE, confidence=0.0)

        try:
            return AIModelAnswer.model_validate(blob)
        except ValidationError as exc:
            _dbg("Pydantic ValidationError on model JSON: %s raw_dict=%r", exc, blob)
            return AIModelAnswer(answer=_FALLBACK_MESSAGE, confidence=0.0)

    except urllib.error.HTTPError as exc:
        # Body already logged inside _groq_chat_json_content before re-raise.
        try:
            _ = exc.read()
        except OSError:
            pass
        return AIModelAnswer(answer=_FALLBACK_MESSAGE, confidence=0.0)
    except (
        urllib.error.URLError,
        TimeoutError,
        OSError,
        ValueError,
        json.JSONDecodeError,
        ValidationError,
    ) as exc:
        _dbg("generate_answer caught %s: %s", type(exc).__name__, exc)
        return AIModelAnswer(answer=_FALLBACK_MESSAGE, confidence=0.0)
    except Exception as exc:
        _dbg("generate_answer unexpected %s: %s", type(exc).__name__, exc)
        return AIModelAnswer(answer=_FALLBACK_MESSAGE, confidence=0.0)


def mock_prove_query(question: str) -> QueryResponse:
    """
    Build the full QueryResponse FastAPI expects.

    Answer + confidence come from `generate_answer` (Groq + validation).
    Other fields remain mock placeholders until auditor / blockchain are added.
    """
    ai_result = generate_answer(question)

    return QueryResponse(
        answer=ai_result.answer,
        confidence=ai_result.confidence,
        is_hallucination=False,
        evidence='(mock) evidence bundle not wired yet — answer from Groq prover.',
        stake_amount='0.001 ETH',
        tx_hash='mock_tx_hash',
        trust_score=110,
    )
