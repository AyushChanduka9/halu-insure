"""
Halu-Insure — Ethereum Sepolia integration (Web3.py).

This module talks to your deployed `HaluInsure` contract: stake, release, slash,
and read trust scores. Configuration is read from `backend/.env`.

Architecture (simple):
  Your FastAPI app (later) → these Python helpers → JSON-RPC (Infura/Alchemy/etc.)
  → Sepolia validators execute the contract → you get a transaction receipt + hash.

Reads (`get_trust_score`) only need an RPC URL + contract address.
Writes (`call_*`) also use the backend wallet private key to sign transactions.

Keep `mock_trust_score_for_address` for existing routes until you wire real reads.
"""

from __future__ import annotations

import hashlib
import os
from pathlib import Path
from typing import Any

# -----------------------------------------------------------------------------
# Optional: load KEY=value pairs from backend/.env into os.environ (no extra deps)
# -----------------------------------------------------------------------------


def _load_dotenv() -> None:
    """Load simple `KEY=value` lines from `backend/.env` once (skips if keys already set)."""
    env_path = Path(__file__).resolve().parent / ".env"
    if not env_path.is_file():
        return
    try:
        text = env_path.read_text(encoding="utf-8")
    except OSError:
        return
    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        if "=" not in line:
            continue
        key, val = line.split("=", 1)
        key = key.strip()
        if not key:
            continue
        val = val.strip().strip('"').strip("'")
        # Do not override explicit environment variables (e.g. CI secrets).
        os.environ.setdefault(key, val)


_load_dotenv()


# -----------------------------------------------------------------------------
# Mock trust (legacy — used by main.py until you switch routes to `get_trust_score`)
# -----------------------------------------------------------------------------


def mock_trust_score_for_address(address: str) -> int:
    """
    Map any non-empty address string to a stable integer score (50–150).

    This is NOT on-chain — it keeps demos working. Prefer `get_trust_score` for real data.
    """
    normalized = address.strip().lower()
    if not normalized:
        return 100

    digest = hashlib.sha256(normalized.encode("utf-8")).hexdigest()
    segment = int(digest[:8], 16)
    return 50 + (segment % 101)


# -----------------------------------------------------------------------------
# Web3 + contract wiring
# -----------------------------------------------------------------------------

# Install: pip install web3
try:
    from web3 import Web3
    from web3.exceptions import ContractLogicError, TimeExhausted, Web3Exception
except ImportError as _e:  # pragma: no cover - import-time hint for beginners
    Web3 = None  # type: ignore[assignment,misc]

    class ContractLogicError(Exception):
        """Placeholder if web3 is not installed."""

    class TimeExhausted(Exception):
        """Placeholder if web3 is not installed."""

    class Web3Exception(Exception):
        """Placeholder if web3 is not installed."""

    _IMPORT_ERROR = _e
else:
    _IMPORT_ERROR = None

# Expected Sepolia chain id (sanity check — catches wrong RPC by mistake).
_SEPOLIA_CHAIN_ID = 11155111

# Minimal ABI: only what this file calls (matches `contracts/HaluInsure.sol`).
_HALU_INSURE_ABI: list[dict[str, Any]] = [
    {
        "inputs": [],
        "name": "NORMAL_STAKE",
        "outputs": [{"internalType": "uint256", "name": "", "type": "uint256"}],
        "stateMutability": "view",
        "type": "function",
    },
    {
        "inputs": [],
        "name": "HIGH_STAKE",
        "outputs": [{"internalType": "uint256", "name": "", "type": "uint256"}],
        "stateMutability": "view",
        "type": "function",
    },
    {
        "inputs": [
            {"internalType": "bytes32", "name": "claimId", "type": "bytes32"},
            {"internalType": "bool", "name": "highRisk", "type": "bool"},
        ],
        "name": "stake",
        "outputs": [],
        "stateMutability": "payable",
        "type": "function",
    },
    {
        "inputs": [{"internalType": "bytes32", "name": "claimId", "type": "bytes32"}],
        "name": "release",
        "outputs": [],
        "stateMutability": "nonpayable",
        "type": "function",
    },
    {
        "inputs": [{"internalType": "bytes32", "name": "claimId", "type": "bytes32"}],
        "name": "slash",
        "outputs": [],
        "stateMutability": "nonpayable",
        "type": "function",
    },
    {
        "inputs": [{"internalType": "address", "name": "agent", "type": "address"}],
        "name": "getTrustScore",
        "outputs": [{"internalType": "uint256", "name": "", "type": "uint256"}],
        "stateMutability": "view",
        "type": "function",
    },
]


class BlockchainConfigError(RuntimeError):
    """Missing or invalid environment / network configuration."""


class BlockchainTransactionError(RuntimeError):
    """Transaction build, send, or confirm failed."""


_w3_cache: Web3 | None = None
_contract_cache: Any = None


def _require_web3() -> None:
    if Web3 is None or _IMPORT_ERROR is not None:
        raise BlockchainConfigError(
            "Web3.py is not installed. From the backend folder run: pip install web3"
        ) from _IMPORT_ERROR


def _env_rpc_url() -> str:
    url = os.getenv("SEPOLIA_RPC_URL", "").strip()
    if not url:
        raise BlockchainConfigError(
            "Set SEPOLIA_RPC_URL in backend/.env (HTTPS Sepolia RPC endpoint)."
        )
    return url


def _env_contract_address() -> str:
    raw = os.getenv("HALU_CONTRACT_ADDRESS", "").strip()
    if not raw:
        raise BlockchainConfigError(
            "Set HALU_CONTRACT_ADDRESS in backend/.env (deployed HaluInsure address)."
        )
    _require_web3()
    if not Web3.is_address(raw):
        raise BlockchainConfigError(f"HALU_CONTRACT_ADDRESS is not a valid address: {raw!r}")
    return Web3.to_checksum_address(raw)


def _env_private_key() -> str:
    pk = os.getenv("BACKEND_PRIVATE_KEY", "").strip()
    if not pk:
        raise BlockchainConfigError(
            "Set BACKEND_PRIVATE_KEY in backend/.env (hex key for signing txs; keep secret)."
        )
    if pk.startswith(("0x", "0X")):
        pk = pk[2:]
    if len(pk) != 64:
        raise BlockchainConfigError("BACKEND_PRIVATE_KEY must be 64 hex characters (optionally 0x-prefixed).")
    return pk


def _get_w3() -> Web3:
    """Single Web3 connection, reused for subsequent calls."""
    global _w3_cache
    _require_web3()
    if _w3_cache is not None and _w3_cache.is_connected():
        return _w3_cache
    rpc = _env_rpc_url()
    provider = Web3.HTTPProvider(rpc)
    w3 = Web3(provider)
    if not w3.is_connected():
        raise BlockchainConfigError(f"Could not connect to RPC (check SEPOLIA_RPC_URL): {rpc!r}")

    chain_id = w3.eth.chain_id
    if chain_id != _SEPOLIA_CHAIN_ID:
        raise BlockchainConfigError(
            f"Connected chain id is {chain_id}, expected Sepolia ({_SEPOLIA_CHAIN_ID}). "
            "Fix your RPC URL."
        )
    _w3_cache = w3
    return w3


def _get_contract(w3: Web3):
    """Contract instance bound to the configured address."""
    global _contract_cache
    if _contract_cache is not None:
        return _contract_cache
    address = _env_contract_address()
    _contract_cache = w3.eth.contract(address=address, abi=_HALU_INSURE_ABI)
    return _contract_cache


def _parse_claim_id(claim_id: str) -> bytes:
    """
    Convert `claim_id` to 32 bytes for Solidity `bytes32`.

    Pass a 64-character hex string, with or without `0x` (the commitment / query hash).
    """
    s = claim_id.strip()
    if s.startswith(("0x", "0X")):
        hex_body = s[2:]
    else:
        hex_body = s
    if len(hex_body) != 64:
        raise ValueError(
            "claim_id must be exactly 32 bytes in hex (64 hex chars), e.g. a keccak256 hash."
        )
    try:
        return bytes.fromhex(hex_body)
    except ValueError as exc:
        raise ValueError("claim_id must contain only hexadecimal digits.") from exc


def _build_and_send_contract_tx(
    w3: Web3,
    contract_fn: Any,
    *,
    value_wei: int = 0,
    timeout: int = 180,
) -> str:
    """
    Sign with BACKEND_PRIVATE_KEY, broadcast, wait for receipt, return `0x` tx hash.

    `contract_fn` is already bound, e.g. `contract.functions.stake(...)` (not called yet).
    """
    from eth_account import Account  # comes with web3

    account = Account.from_key(_env_private_key())
    checksum_from = Web3.to_checksum_address(account.address)

    try:
        nonce = w3.eth.get_transaction_count(checksum_from, "pending")
        chain_id = w3.eth.chain_id

        # Gas price: simple legacy-style field; Sepolia accepts it via web3's gas_price.
        gas_price = w3.eth.gas_price

        tx: dict[str, Any] = contract_fn.build_transaction(
            {
                "from": checksum_from,
                "nonce": nonce,
                "chainId": chain_id,
                "gasPrice": gas_price,
                "value": value_wei,
            }
        )
        # Estimate with the same sender/value the final tx will use.
        gas_est = w3.eth.estimate_gas(tx)
        tx["gas"] = min(int(gas_est * 1.25) + 20_000, 10_000_000)

        signed = account.sign_transaction(tx)
        raw = getattr(signed, "raw_transaction", None) or getattr(signed, "rawTransaction", None)
        if raw is None:
            raise BlockchainTransactionError("Signed transaction payload missing on sign result.")

        tx_hash = w3.eth.send_raw_transaction(raw)
        receipt = w3.eth.wait_for_transaction_receipt(tx_hash, timeout=timeout)
    except ContractLogicError as exc:
        raise BlockchainTransactionError("Contract reverted (simulation or execution failed).") from exc
    except TimeExhausted as exc:
        raise BlockchainTransactionError("Timed out waiting for transaction receipt.") from exc
    except Web3Exception as exc:
        raise BlockchainTransactionError(f"Web3 error: {exc}") from exc
    except ValueError as exc:
        raise BlockchainTransactionError(str(exc)) from exc

    if receipt.get("status") != 1:
        raise BlockchainTransactionError("Transaction mined but reverted (status 0).")

    return Web3.to_hex(tx_hash)


# -----------------------------------------------------------------------------
# Public API
# -----------------------------------------------------------------------------


def call_stake(claim_id: str, high_risk: bool) -> str:
    """
    Call `stake(claimId, highRisk)` sending the exact ETH required (normal vs high).

    The wallet in BACKEND_PRIVATE_KEY pays gas and sends the stake value.
    Returns the transaction hash (hex string).
    """
    _require_web3()
    w3 = _get_w3()
    contract = _get_contract(w3)
    claim_bytes32 = _parse_claim_id(claim_id)

    if high_risk:
        value_wei = contract.functions.HIGH_STAKE().call()
    else:
        value_wei = contract.functions.NORMAL_STAKE().call()

    fn = contract.functions.stake(claim_bytes32, high_risk)
    return _build_and_send_contract_tx(w3, fn, value_wei=value_wei)


def get_stake_amount_wei(high_risk: bool) -> int:
    """
    Read current stake amount from contract constants.

    Returns:
        int: stake value in wei for normal or high risk mode.
    """
    _require_web3()
    w3 = _get_w3()
    contract = _get_contract(w3)
    if high_risk:
        return int(contract.functions.HIGH_STAKE().call())
    return int(contract.functions.NORMAL_STAKE().call())


def call_release(claim_id: str) -> str:
    """
    Call `release(claimId)` — prover withdraws after the cooldown (must be msg.sender).

    Only the staker address can release; that must be your BACKEND_PRIVATE_KEY account.
    """
    _require_web3()
    w3 = _get_w3()
    contract = _get_contract(w3)
    claim_bytes32 = _parse_claim_id(claim_id)
    fn = contract.functions.release(claim_bytes32)
    return _build_and_send_contract_tx(w3, fn, value_wei=0)


def call_slash(claim_id: str) -> str:
    """
    Call `slash(claimId)` — **only the contract owner** can slash.

    The signing wallet must be `HaluInsure.owner()`. Otherwise the tx reverts.
    """
    _require_web3()
    w3 = _get_w3()
    contract = _get_contract(w3)
    claim_bytes32 = _parse_claim_id(claim_id)
    fn = contract.functions.slash(claim_bytes32)
    return _build_and_send_contract_tx(w3, fn, value_wei=0)


def get_trust_score(address: str) -> int:
    """
    Call `getTrustScore(agent)` on-chain; returns 0–100+ per contract rules.

    Unset scores display as 100 on-chain — this function returns that uint256 as `int`.

    Only needs SEPOLIA_RPC_URL + HALU_CONTRACT_ADDRESS (no private key).
    """
    _require_web3()
    w3 = _get_w3()
    contract = _get_contract(w3)
    addr = address.strip()
    if not Web3.is_address(addr):
        raise ValueError("address must be a valid Ethereum checksummable address string.")
    checksum = Web3.to_checksum_address(addr)
    try:
        score = contract.functions.getTrustScore(checksum).call()
    except ContractLogicError as exc:
        raise BlockchainTransactionError("getTrustScore reverted.") from exc
    except Web3Exception as exc:
        raise BlockchainTransactionError(f"Web3 read failed: {exc}") from exc

    return int(score)
