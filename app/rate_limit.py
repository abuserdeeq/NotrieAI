"""Shared rate limiter setup.

Render's free tier runs a single instance, so slowapi's default in-memory
storage is fine here - no Redis needed. If this app is ever scaled to more
than one instance, switch to a Redis-backed storage_uri (see slowapi docs)
so all instances share the same counters; otherwise each instance would
enforce its own separate limit.
"""

from fastapi import Request
from slowapi import Limiter
from slowapi.util import get_remote_address


def user_or_ip_key(request: Request) -> str:
    """Rate-limit key for authenticated endpoints: the caller's raw JWT
    when a Bearer token is present, otherwise their IP.

    Keying on the token (rather than IP) means users on a shared or
    mobile IP don't share one budget, while requests with a missing or
    malformed token still fall back to per-IP limiting.
    """
    auth_header = request.headers.get("authorization", "")
    if auth_header.lower().startswith("bearer "):
        token = auth_header[7:].strip()
        if token:
            return f"user:{token}"
    return f"ip:{get_remote_address(request)}"


limiter = Limiter(key_func=get_remote_address)
