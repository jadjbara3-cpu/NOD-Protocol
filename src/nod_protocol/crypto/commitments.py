"""Cryptographic primitives for the NØD Protocol reference implementation.

Standard library only (hashlib, hmac). These are deterministic, educational
commitment primitives — not a production security audit.
"""

from __future__ import annotations

import hashlib
import hmac
import json
from collections.abc import Mapping
from typing import Any, Callable


def _normalize(value: Any) -> Any:
    """Convert read-only wrappers (MappingProxyType) into plain JSON-safe types."""
    if isinstance(value, Mapping):
        return {str(k): _normalize(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [_normalize(v) for v in value]
    return value


def _canonical_bytes(data: Any) -> bytes:
    """Serialize a value into a stable, deterministic byte sequence."""
    if isinstance(data, bytes):
        return data
    return json.dumps(_normalize(data), sort_keys=True, ensure_ascii=False, separators=(",", ":")).encode("utf-8")


def content_hash(data: Any) -> str:
    """SHA-256 content hash of a canonicalized value."""
    return hashlib.sha256(_canonical_bytes(data)).hexdigest()


def sha256_bytes(data: Any) -> bytes:
    """Raw SHA-256 digest bytes of a canonicalized value."""
    return hashlib.sha256(_canonical_bytes(data)).digest()


def event_id(event_payload: Any) -> str:
    """Deterministic event identifier: sha256 over the canonical payload."""
    return content_hash(event_payload)


def signature(agent_identity: str, payload: Any) -> str:
    """Deterministic HMAC-SHA256 signature using the agent identity as key.

    This is an identity-binding signature primitive for the reference
    implementation. A production protocol would use asymmetric signatures
    (ed25519 etc.) — that choice remains open (see spec §10.3).
    """
    key = _canonical_bytes(agent_identity)
    return hmac.new(key, _canonical_bytes(payload), hashlib.sha256).hexdigest()


def verify_signature(agent_identity: str, payload: Any, sig: str) -> bool:
    """Verify a signature produced by :func:`signature`."""
    expected = signature(agent_identity, payload)
    return hmac.compare_digest(expected, sig)


def hidden_commitment(secret: Any, salt: str = "") -> str:
    """Commitment hash for information that must remain hidden until disclosure.

    R-5: a committed hypothesis may be hidden via commitment_reference; later
    disclosure can be verified against this commitment.
    """
    return content_hash({"value": secret, "salt": salt})


def commit_and_check(secret: Any, commitment: str, salt: str = "") -> bool:
    """Check that ``secret`` matches a previously published commitment."""
    return hmac.compare_digest(hidden_commitment(secret, salt), commitment)


def base58_encode(raw: bytes) -> str:
    """Minimal Base58 encoding (Bitcoin alphabet) for NØD ids."""
    alphabet = "123456789ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz"
    num = int.from_bytes(raw, "big")
    encoded = ""
    while num > 0:
        num, rem = divmod(num, 58)
        encoded = alphabet[rem] + encoded
    pad = 0
    for byte in raw:
        if byte == 0:
            pad += 1
        else:
            break
    return alphabet[0] * pad + (encoded or alphabet[0])


def nod_id(claim: Any, agent_identity: str, order: int) -> str:
    """Generate a NØD identifier: NØD- + base58(sha256(claim+agent+order)[:16])."""
    digest = sha256_bytes({"claim": claim, "agent": agent_identity, "order": order})[:16]
    return "NØD-" + base58_encode(digest)
