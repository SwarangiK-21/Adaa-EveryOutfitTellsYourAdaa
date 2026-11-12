"""Per-address limits on how often each kind of request may be made (HTTP 429 when exceeded).

They stop one computer from flooding sign-ups or reset emails, guessing many passwords, filling the
disk with uploads, or re-downloading the big AI model over and over. Normal use never comes close.
Counts are kept in memory (Peheraav runs as a single process); behind Caddy the real visitor address
comes from X-Forwarded-For (uvicorn --proxy-headers). PEHERAAV_RATE_LIMITS=0 switches this off.
"""
import re
import threading
import time
from collections import deque

from fastapi import Request
from fastapi.responses import JSONResponse

import config

HOUR, MINUTE = 3600, 60

# (method, path pattern, how many, per how many seconds, name, message)
RULES = [
    ("POST", r"/api/auth/signup", 10, HOUR, "signup", "Too many new accounts from this connection. Please try again in an hour."),
    ("POST", r"/api/auth/login", 20, 15 * MINUTE, "login", "Too many log-in attempts. Please wait 15 minutes and try again."),
    ("POST", r"/api/auth/forgot", 5, HOUR, "forgot", "Too many reset requests. Please try again in an hour."),
    ("POST", r"/api/auth/reset", 10, HOUR, "reset", "Too many attempts. Please ask for a new link in an hour."),
    ("POST", r"/api/auth/verify", 20, HOUR, "verify", "Too many attempts. Please try again in an hour."),
    ("*", r"/api/(cutout-model|models/.+)", 10, HOUR, "model", "The style model was downloaded too often. Please try again in an hour."),
    ("POST|PUT", r"/api/(items(/\d+(/cutout)?)?|looks/\d+/photo)", 300, HOUR, "upload", "That's a lot of uploads at once. Please take a break and try again later."),
    ("POST", r"/api/client-error", 30, HOUR, "crash-report", "Too many error reports."),
    ("*", r"/api/.*", 1500, MINUTE, "api", "Too many requests. Please slow down a little."),
]
_COMPILED = [(m.split("|"), re.compile(p + r"$"), n, w, name, msg) for m, p, n, w, name, msg in RULES]

_hits: dict[tuple[str, str], deque] = {}
_lock = threading.Lock()
_last_sweep = time.monotonic()


def clear() -> None:
    with _lock:
        _hits.clear()


def _rule_for(method: str, path: str):
    for methods, pattern, limit, window, name, message in _COMPILED:
        if ("*" in methods or method in methods) and pattern.match(path):
            return limit, window, name, message
    return None


def _allow(key: tuple[str, str], limit: int, window: int) -> tuple[bool, int]:
    global _last_sweep
    now = time.monotonic()
    with _lock:
        if now - _last_sweep > 10 * MINUTE:      # forget addresses that have gone quiet
            for k in [k for k, q in _hits.items() if not q or now - q[-1] > HOUR]:
                del _hits[k]
            _last_sweep = now
        q = _hits.setdefault(key, deque())
        while q and now - q[0] >= window:
            q.popleft()
        if len(q) >= limit:
            return False, int(window - (now - q[0])) + 1
        q.append(now)
        return True, 0


async def middleware(request: Request, call_next):
    if config.RATE_LIMITS:
        rule = _rule_for(request.method, request.url.path)
        if rule:
            limit, window, name, message = rule
            address = request.client.host if request.client else "unknown"
            ok, retry_after = _allow((name, address), limit, window)
            if not ok:
                return JSONResponse({"detail": message}, status_code=429, headers={"Retry-After": str(retry_after)})
    return await call_next(request)
