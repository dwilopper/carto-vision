from __future__ import annotations

import base64
import hashlib
import hmac
import json
import secrets
from typing import Any

from app.config import SECRET_KEY


def hash_password(password: str, *, salt: str | None = None) -> str:
    local_salt = salt or secrets.token_hex(16)
    digest = hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        local_salt.encode("utf-8"),
        120_000,
    )
    return f"{local_salt}${digest.hex()}"


def verify_password(password: str, stored_hash: str) -> bool:
    try:
        salt, _ = stored_hash.split("$", 1)
    except ValueError:
        return False
    return hmac.compare_digest(hash_password(password, salt=salt), stored_hash)


def _sign(payload: bytes) -> str:
    signature = hmac.new(
        SECRET_KEY.encode("utf-8"),
        payload,
        digestmod="sha256",
    ).digest()
    return base64.urlsafe_b64encode(signature).decode("ascii").rstrip("=")


def issue_auth_token(user: dict[str, Any]) -> str:
    payload = json.dumps(
        {
            "id": user["id"],
            "username": user["username"],
            "role": user["role"],
        },
        separators=(",", ":"),
    ).encode("utf-8")
    encoded = base64.urlsafe_b64encode(payload).decode("ascii").rstrip("=")
    return f"{encoded}.{_sign(payload)}"


def decode_auth_token(token: str | None) -> dict[str, Any] | None:
    if not token or "." not in token:
        return None
    encoded, signature = token.split(".", 1)
    padded = encoded + "=" * (-len(encoded) % 4)
    try:
        payload = base64.urlsafe_b64decode(padded.encode("ascii"))
    except Exception:
        return None
    if not hmac.compare_digest(signature, _sign(payload)):
        return None
    try:
        return json.loads(payload.decode("utf-8"))
    except json.JSONDecodeError:
        return None
