from __future__ import annotations
import os
from typing import Any, Dict, Optional

try:
    import jwt  # PyJWT
except Exception:  # pragma: no cover - optional dependency
    jwt = None  # type: ignore

from fastapi import Request


class AuthUser(Dict[str, Any]):
    """Minimal user payload extracted from a NextAuth JWT."""


def verify_nextauth_jwt(request: Request) -> Optional[AuthUser]:
    """
    Best-effort verification of a NextAuth JWT from Authorization: Bearer <token>.
    - Uses NEXTAUTH_SECRET (HS256) to verify signature.
    - Returns the decoded payload (dict) on success, or None if not present/invalid.
    - Designed to be non-fatal to avoid breaking existing flows when auth is not configured.
    """
    if jwt is None:
        return None


def get_effective_owner(request: Request) -> Optional[str]:
    """Resolve the owner key for this request.
    Priority:
    1) Authenticated user (NextAuth JWT) -> user.sub or user.email
    2) Guest ID header 'x-guest-id' provided by the client proxy
    3) None
    """
    user = verify_nextauth_jwt(request)
    if user:
        uid = user.get("sub") or user.get("email")
        if uid:
            return str(uid)
    guest_id = request.headers.get("x-guest-id") or request.headers.get("X-Guest-Id")
    if guest_id:
        return str(guest_id)
    return None

    auth = request.headers.get("authorization") or request.headers.get("Authorization")
    if not auth or not auth.lower().startswith("bearer "):
        return None

    token = auth.split(" ", 1)[1].strip()
    secret = os.getenv("NEXTAUTH_SECRET")
    if not secret:
        return None

    try:
        payload = jwt.decode(token, secret, algorithms=["HS256"])  # type: ignore
        # Common NextAuth fields include: sub (user id), email, name, picture, etc.
        if isinstance(payload, dict):
            return AuthUser(payload)
    except Exception:
        return None

    return None
