"""
Halu-Insure FastAPI entrypoint.
"""

from hashlib import sha256

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from auditor import audit_answer
from blockchain import (
    call_release,
    call_slash,
    call_stake,
    get_trust_score,
)
from models import QueryRequest, QueryResponse
from prover import mock_prove_query

app = FastAPI(title="Halu-Insure")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
def root():
    return {"message": "Halu-Insure backend is running"}


@app.post("/query", response_model=QueryResponse)
def post_query(body: QueryRequest):
    """
    Main AI + blockchain flow.

    Steps:
    1. Generate prover answer + confidence
    2. Decide stake risk level
    3. Create claim_id from question hash
    4. Stake ETH on-chain
    5. Run auditor AI
    6. Slash or release depending on verdict
    7. Return final response
    """

    try:
        # -----------------------------
        # 1. Prover AI
        # -----------------------------
        result = mock_prove_query(body.question)

        # -----------------------------
        # 2. Risk calculation
        # -----------------------------
        high_risk = result.confidence < 0.7

        # -----------------------------
        # 3. Unique claim ID
        # -----------------------------
        # sha256 gives 64 hex chars.
        # Add 0x prefix so it matches bytes32 style.
        claim_id = "0x" + sha256(body.question.encode()).hexdigest()

        # -----------------------------
        # 4. Stake on blockchain
        # -----------------------------
        stake_tx_hash = call_stake(
            claim_id=claim_id,
            high_risk=high_risk,
        )

        # -----------------------------
        # 5. Auditor AI verification
        # -----------------------------
        audit = audit_answer(
            body.question,
            result.answer,
        )

        # -----------------------------
        # 6. Slash or release
        # -----------------------------
        final_tx_hash = stake_tx_hash

        if audit.is_hallucination:
            final_tx_hash = call_slash(claim_id)
        else:
            try:
                final_tx_hash = call_release(claim_id)
            except Exception:
                # Your contract has RELEASE_DELAY = 1 day.
                # So release may fail during testing.
                # Keep the stake tx hash instead.
                pass

        # -----------------------------
        # 7. Trust score
        # -----------------------------
        backend_wallet = (
            "0xa4ca44704db87C03d5cd13c84388267f00949C2d"
        )

        trust_score = get_trust_score(backend_wallet)

        # -----------------------------
        # 8. Stake amount text
        # -----------------------------
        stake_amount = (
            "0.005 ETH" if high_risk else "0.001 ETH"
        )

        # -----------------------------
        # 9. Final API response
        # -----------------------------
        return QueryResponse(
            answer=result.answer,
            confidence=result.confidence,
            is_hallucination=audit.is_hallucination,
            evidence=f"{audit.verdict}: {audit.evidence}",
            stake_amount=stake_amount,
            tx_hash=final_tx_hash,
            trust_score=trust_score,
        )

    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=f"/query pipeline failed: {str(exc)}",
        )