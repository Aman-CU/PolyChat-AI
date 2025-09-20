from __future__ import annotations
import time
from typing import Dict, Tuple
from fastapi import HTTPException, Request

# Very simple in-memory rate limiter (per-IP, per-route). Not suitable for multi-process.
# Placeholder for Redis-based limiter.

# key: (ip, route) -> (window_start_epoch, count)
_BUCKETS: Dict[Tuple[str, str], Tuple[float, int]] = {}


def get_client_ip(request: Request) -> str:
    # Try common forwarding headers first
    xff = request.headers.get("x-forwarded-for")
    if xff:
        # Take the first IP
        return xff.split(",")[0].strip()
    # Fallback to client host
    return request.client.host if request.client else "unknown"


def enforce_rate_limit(request: Request, limit: int = 30, window_seconds: int = 60) -> None:
    ip = get_client_ip(request)
    route = request.url.path
    key = (ip, route)

    now = time.time()
    window_start, count = _BUCKETS.get(key, (now, 0))

    # Reset window if elapsed
    if now - window_start >= window_seconds:
        window_start = now
        count = 0

    count += 1
    _BUCKETS[key] = (window_start, count)

    if count > limit:
        # Calculate retry-after
        retry_after = max(1, int(window_seconds - (now - window_start)))
        raise HTTPException(status_code=429, detail="Rate limit exceeded", headers={"Retry-After": str(retry_after)})
