"""
Auditor module — checks whether the prover's answer looks truthful or hallucinated.

Flow (high level):
  1. `audit_answer(question, answer)` calls Groq with a strict JSON schema.
  2. The model compares the user question to the proposed answer.
  3. We validate the reply with Pydantic; on any failure we return a safe fallback.

Uses the same Groq OpenAI-compatible Chat API and `GROQ_API_KEY` as `prover.py`.
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
from vector_store import retrieve_relevant_chunks

# -----------------------------------------------------------------------------
# Logging (mirror prover.py style)
# -----------------------------------------------------------------------------

_LOGGER = logging.getLogger(__name__)

_AUDITOR_DEBUG = True


def _dbg(msg: str, *args: Any) -> None:
    if _AUDITOR_DEBUG:
        _LOGGER.info("[auditor] " + msg, *args)


def _masked_key_preview(api_key: str) -> str:
    if len(api_key) <= 3:
        return "len=<too_short_to_preview_safely>"
    window = api_key[:10]
    masked_window = api_key[:3] + "*" * (len(window) - 3)
    suffix = "…" if len(api_key) > 10 else ""
    return f"len={len(api_key)} first10_masked={masked_window!s}{suffix!s}"


# -----------------------------------------------------------------------------
# Configuration
# -----------------------------------------------------------------------------

_GROQ_CHAT_URL = "https://api.groq.com/openai/v1/chat/completions"
_DEFAULT_MODEL = "llama-3.3-70b-versatile"
_API_USER_AGENT = "Halu-Insure-Auditor/0.1 (+local dev; FastAPI)"
_DOTENV_RESOLVED_PATH = Path(__file__).resolve().parent / ".env"

_FALLBACK_VERDICT = "audit_unavailable"
_FALLBACK_EVIDENCE = (
    "The automated auditor could not complete (missing key, network error, or invalid model output). "
    "The answer was not verified."
)


# -----------------------------------------------------------------------------
# Load backend/.env (does not overwrite existing env vars)
# -----------------------------------------------------------------------------


def _load_env_from_dotenv_file() -> None:
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
            ".env path: %s — file_exists=True — lines_written_to_environ=%s",
            env_path,
            keys_loaded,
        )
    except OSError as exc:
        _dbg("Could not read .env at %s: %s", env_path, exc)


_load_env_from_dotenv_file()

_groq_key_present = bool(os.environ.get("GROQ_API_KEY"))
_dbg(
    "GROQ_API_KEY detected=%s preview=%s",
    _groq_key_present,
    _masked_key_preview(os.environ["GROQ_API_KEY"]) if _groq_key_present else "n/a",
)


# -----------------------------------------------------------------------------
# Model output shape (strict JSON from Groq)
# -----------------------------------------------------------------------------


class AuditResult(BaseModel):
    """JSON the auditor model must return."""

    is_hallucination: bool = Field(..., description="True if answer seems wrong, misleading, or fabricated")
    evidence: str = Field(..., min_length=1, description="Short reasoning comparing question vs answer")
    verdict: str = Field(..., min_length=1, description="One-line label, e.g. consistent / likely_hallucination")
    retrieved_chunks: list[str] = Field(
        default_factory=list,
        description="Top retrieved chunk texts used as trusted context for auditing",
    )

    @field_validator("is_hallucination", mode="before")
    @classmethod
    def _coerce_bool(cls, value: object) -> object:
        if isinstance(value, str):
            lowered = value.strip().lower()
            if lowered in ("true", "1", "yes"):
                return True
            if lowered in ("false", "0", "no"):
                return False
        return value


def _extract_json_object(text: str) -> dict:
    cleaned = text.strip()
    fence = re.search(r"```(?:json)?\s*([\s\S]*?)```", cleaned, re.IGNORECASE)
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
    api_key = os.environ.get("GROQ_API_KEY")
    if not api_key:
        raise ValueError(
            "GROQ_API_KEY is missing — add it to backend/.env or export it in your shell."
        )

    payload: dict = {
        "model": model,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_message},
        ],
        "response_format": {"type": "json_object"},
        "temperature": 0.1,
    }

    data = json.dumps(payload).encode("utf-8")
    request_obj = urllib.request.Request(
        _GROQ_CHAT_URL,
        data=data,
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
            "User-Agent": _API_USER_AGENT,
        },
        method="POST",
    )

    try:
        with urllib.request.urlopen(request_obj, timeout=timeout_seconds) as resp:
            raw_body = resp.read().decode("utf-8")
            _dbg("Groq HTTP status=%s bytes=%s", getattr(resp, "status", 200), len(raw_body))
    except urllib.error.HTTPError as exc:
        err_body = b""
        try:
            err_body = exc.read()
        except OSError as read_exc:
            _dbg("Groq HTTPError: could not read error body: %s", read_exc)
        snippet = err_body.decode("utf-8", errors="replace")[:2000]
        _dbg("Groq request failed HTTP status=%s raw_error_body(first 2000 chars)=%r", exc.code, snippet)
        raise

    try:
        parsed = json.loads(raw_body)
    except json.JSONDecodeError as exc:
        _dbg(
            "JSONDecodeError parsing Groq HTTP body: %s snippet=%r",
            exc,
            (raw_body[:1200] + "…") if len(raw_body) > 1200 else raw_body,
        )
        raise
    try:
        return parsed["choices"][0]["message"]["content"]
    except (KeyError, IndexError, TypeError) as exc:
        _dbg("Unexpected Groq JSON shape parsed=%r err=%s", parsed, exc)
        raise ValueError(f"Unexpected Groq response shape: {parsed!r}") from exc


def _fallback_audit(reason: str) -> AuditResult:
    _dbg("Using fallback audit: %s", reason)
    return AuditResult(
        is_hallucination=False,
        evidence=_FALLBACK_EVIDENCE,
        verdict=_FALLBACK_VERDICT,
        retrieved_chunks=[],
    )


def audit_answer(question: str, answer: str) -> AuditResult:
    """
    Ask Groq whether `answer` is a reasonable, honest response to `question`.

    Returns a validated AuditResult. On API/parse errors, returns a conservative
    fallback (not flagged as hallucination, but evidence explains verification failed).
    """
    q = (question or "").strip()
    a = (answer or "").strip()
    if not q:
        return _fallback_audit("empty question")
    if not a:
        return _fallback_audit("empty answer")

    retrieved_chunks_text = "No trusted context was retrieved."
    retrieved_chunk_list: list[str] = []
    try:
        retrieved = retrieve_relevant_chunks(q, a, top_k=3)
        if retrieved:
            lines = []
            for i, chunk in enumerate(retrieved, start=1):
                retrieved_chunk_list.append(chunk.text)
                lines.append(
                    f"[{i}] source={chunk.source} score={chunk.score:.4f} text={chunk.text}"
                )
            retrieved_chunks_text = "\n".join(lines)
    except Exception as exc:
        _dbg("RAG retrieval failed; continuing without retrieved context: %s", exc)

    system_prompt = """You are Halu-Insure's hallucination auditor with retrieval support.

You receive:
- The USER QUESTION (what the user asked).
- The PROVER ANSWER (what another model replied).
- TRUSTED RETRIEVED CONTEXT (small local knowledge chunks).

Your job: decide if the PROVER ANSWER appears incorrect, misleading, inconsistent with the question,
or fabricated (making up facts, fake citations, or claiming certainty about things that cannot be known).

You MUST respond with a single JSON object and nothing else (no markdown, no text outside JSON).
Use this EXACT schema:
{"is_hallucination": <true or false>, "evidence": "<string>", "verdict": "<string>"}

Rules:
- is_hallucination: true if the answer appears wrong, evasive in a deceptive way, or likely fabricated/made up;
  false if it seems plausibly correct and grounded, or appropriately cautious when uncertain.
- evidence: 2–4 short sentences explaining your comparison (question vs answer) and referencing retrieved context when relevant.
- If retrieved context directly conflicts with the prover answer, treat that as stronger hallucination evidence.
- verdict: a very short human label (e.g. "likely_grounded", "likely_hallucination", "unclear", "off_topic").
- Do not hedge with extra keys — only those three fields.
"""

    user_payload = json.dumps(
        {
            "user_question": q,
            "prover_answer": a,
            "trusted_retrieved_context": retrieved_chunks_text,
        },
        ensure_ascii=False,
    )

    try:
        raw_content = _groq_chat_json_content(system_prompt=system_prompt, user_message=user_payload)
        if raw_content is None:
            _dbg("Groq assistant content is None (unexpected)")
            return _fallback_audit("null assistant content")

        try:
            blob = _extract_json_object(raw_content)
        except json.JSONDecodeError as exc:
            _dbg(
                "JSONDecodeError parsing model content: %s snippet=%r",
                exc,
                (raw_content[:1200] + "…") if len(raw_content) > 1200 else raw_content,
            )
            return _fallback_audit("JSON decode failed on model content")

        try:
            parsed = AuditResult.model_validate(blob)
            # Preserve the exact retrieved chunk texts that were used during auditing.
            parsed.retrieved_chunks = retrieved_chunk_list
            return parsed
        except ValidationError as exc:
            _dbg("Pydantic ValidationError on audit JSON: %s raw_dict=%r", exc, blob)
            return _fallback_audit("validation failed")

    except urllib.error.HTTPError as exc:
        try:
            _ = exc.read()
        except OSError:
            pass
        return _fallback_audit(f"HTTPError {exc.code}")
    except (
        urllib.error.URLError,
        TimeoutError,
        OSError,
        ValueError,
        json.JSONDecodeError,
        ValidationError,
    ) as exc:
        _dbg("audit_answer caught %s: %s", type(exc).__name__, exc)
        return _fallback_audit(f"{type(exc).__name__}")
    except Exception as exc:
        _dbg("audit_answer unexpected %s: %s", type(exc).__name__, exc)
        return _fallback_audit(f"unexpected {type(exc).__name__}")


def mock_audit_dispute(reason: str, related_tx_hash: str | None) -> tuple[str, bool]:
    """
    Pretend to audit a dispute (used by /dispute until wired to deeper logic).

    Returns:
        auditor_verdict: Short text describing the mock decision.
        refund_eligible: Mock flag for whether a refund might apply.
    """
    _ = related_tx_hash
    verdict = (
        f"Mock auditor reviewed dispute. Reason noted ({len(reason)} chars). "
        "No real evaluation performed."
    )
    refund_eligible = False
    return verdict, refund_eligible
