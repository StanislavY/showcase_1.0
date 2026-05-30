"""Courier authentication primitives (standard-library only).

This module intentionally avoids external dependencies (no JWT, no
passlib). It provides:

* PBKDF2 password hashing / verification, and
* a minimal signed session token (JSON payload + HMAC-SHA256 signature).

The password itself is never stored on the device: only its PBKDF2 hash
(``config.courier_password_hash``) and the salt are kept in configuration.
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
import time

from app.core.config import config

# PBKDF2 work factor. Kept in sync with the value used to precompute the
# stored ``courier_password_hash``.
_PBKDF2_ITERATIONS = 200_000
_PBKDF2_DIGEST = "sha256"


def _b64encode(raw: bytes) -> str:
    """URL-safe base64 without trailing newline."""
    return base64.urlsafe_b64encode(raw).decode("ascii")


def _b64decode(value: str) -> bytes:
    return base64.urlsafe_b64decode(value.encode("ascii"))


def hash_password(password: str, salt: str) -> str:
    """Return the base64-encoded PBKDF2-HMAC-SHA256 hash of ``password``."""
    derived = hashlib.pbkdf2_hmac(
        _PBKDF2_DIGEST,
        password.encode("utf-8"),
        salt.encode("utf-8"),
        _PBKDF2_ITERATIONS,
    )
    # Standard base64 to match the stored ``courier_password_hash`` value.
    return base64.b64encode(derived).decode("ascii")


def verify_password(password: str, salt: str, expected_hash: str) -> bool:
    """Check ``password`` against ``expected_hash`` in constant time."""
    candidate = hash_password(password, salt)
    return hmac.compare_digest(candidate, expected_hash)


def _sign(message: bytes) -> str:
    signature = hmac.new(
        config.courier_session_secret.encode("utf-8"),
        message,
        hashlib.sha256,
    ).digest()
    return _b64encode(signature)


def create_courier_session_token(courier_id: str) -> str:
    """Create a signed ``<payload>.<signature>`` session token.

    The payload is a base64-encoded JSON object holding ``courier_id`` and
    an absolute expiry timestamp (``exp``, Unix seconds).
    """
    exp = int(time.time()) + config.courier_session_ttl_minutes * 60
    payload = {"courier_id": courier_id, "exp": exp}
    payload_bytes = json.dumps(
        payload, separators=(",", ":"), sort_keys=True
    ).encode("utf-8")
    payload_b64 = _b64encode(payload_bytes)
    signature_b64 = _sign(payload_bytes)
    return f"{payload_b64}.{signature_b64}"


def verify_courier_session_token(token: str) -> bool:
    """Return True if ``token`` has a valid signature and is not expired."""
    if not token or token.count(".") != 1:
        return False

    payload_b64, signature_b64 = token.split(".", 1)
    try:
        payload_bytes = _b64decode(payload_b64)
    except (ValueError, TypeError):
        return False

    expected_signature = _sign(payload_bytes)
    if not hmac.compare_digest(signature_b64, expected_signature):
        return False

    try:
        payload = json.loads(payload_bytes.decode("utf-8"))
    except (ValueError, TypeError):
        return False

    exp = payload.get("exp")
    if not isinstance(exp, int):
        return False

    return int(time.time()) < exp


# ---------------------------------------------------------------------------
# Administrator (control panel) session tokens
# ---------------------------------------------------------------------------
# The admin tokens are signed with a separate secret (``admin_session_secret``)
# so that a leaked courier token can never be used as an admin token and vice
# versa. The token format is identical: ``<payload_b64>.<signature_b64>``.


def _sign_admin(message: bytes) -> str:
    signature = hmac.new(
        config.admin_session_secret.encode("utf-8"),
        message,
        hashlib.sha256,
    ).digest()
    return _b64encode(signature)


def create_admin_session_token(admin_id: str) -> str:
    """Create a signed ``<payload>.<signature>`` admin session token.

    The payload is a base64-encoded JSON object holding ``admin_id`` and an
    absolute expiry timestamp (``exp``, Unix seconds).
    """
    exp = int(time.time()) + config.admin_session_ttl_minutes * 60
    payload = {"admin_id": admin_id, "exp": exp}
    payload_bytes = json.dumps(
        payload, separators=(",", ":"), sort_keys=True
    ).encode("utf-8")
    payload_b64 = _b64encode(payload_bytes)
    signature_b64 = _sign_admin(payload_bytes)
    return f"{payload_b64}.{signature_b64}"


def verify_admin_session_token(token: str) -> str | None:
    """Return the ``admin_id`` if ``token`` is valid and not expired, else None."""
    if not token or token.count(".") != 1:
        return None

    payload_b64, signature_b64 = token.split(".", 1)
    try:
        payload_bytes = _b64decode(payload_b64)
    except (ValueError, TypeError):
        return None

    expected_signature = _sign_admin(payload_bytes)
    if not hmac.compare_digest(signature_b64, expected_signature):
        return None

    try:
        payload = json.loads(payload_bytes.decode("utf-8"))
    except (ValueError, TypeError):
        return None

    exp = payload.get("exp")
    admin_id = payload.get("admin_id")
    if not isinstance(exp, int) or not isinstance(admin_id, str):
        return None

    if int(time.time()) >= exp:
        return None

    return admin_id
