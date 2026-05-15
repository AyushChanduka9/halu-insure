"""
Pydantic v2 models for request and response bodies.

Keeping all API shapes in one place makes it easy to see what the API
expects and returns — similar to TypeScript interfaces.
"""

from pydantic import BaseModel, Field


# ----- POST /query -----


class QueryRequest(BaseModel):
    """What the client sends when asking a question."""

    question: str = Field(..., min_length=1, description="User's question text")


class QueryResponse(BaseModel):
    """What the API returns after processing a query (mock for now)."""

    answer: str
    confidence: float = Field(..., ge=0.0, le=1.0)
    is_hallucination: bool
    evidence: str
    retrieved_chunks: list[str] | None = None
    stake_amount: str
    tx_hash: str
    trust_score: int


# ----- POST /dispute -----


class DisputeRequest(BaseModel):
    """
    A user opens a dispute about a prior answer or claim.

    Fields are flexible placeholders until you wire real logic.
    """

    reason: str = Field(..., min_length=1, description="Why the user disputes the result")
    related_tx_hash: str | None = Field(
        default=None,
        description="Optional mock transaction hash tied to the original query",
    )


class DisputeResponse(BaseModel):
    """Mock outcome of a dispute review."""

    status: str = Field(..., description="e.g. received, under_review, resolved_mock")
    message: str
    auditor_verdict: str
    mock_refund_eligible: bool


# ----- GET /trust-score/{address} -----


class TrustScoreResponse(BaseModel):
    """Trust score for an Ethereum-style address (mock data for now)."""

    address: str
    trust_score: int = Field(..., ge=0, le=200, description="Mock score 0–200")
    note: str = Field(default="", description="Human-readable hint that data is mocked")
