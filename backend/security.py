"""Browser-side protections added by the backend.

1. Cross-site request check: a page on another website can't make your browser change things in
   Peheraav (save, delete, upload...) using your sign-in cookie. Browsers always say where a request
   came from (the Origin header); changes are only accepted from Peheraav's own address. Requests
   without an Origin (scripts, tests) are allowed: they don't carry your browser's cookie anyway
   unless sent on purpose. The SameSite=Lax cookie already blocks most of this; this closes the rest.
2. Content Security Policy on the app page: the page may only load code, styles, fonts and images
   from Peheraav itself, and only talk to Peheraav and the weather service. It limits the damage if a bug
   ever let someone inject content.
"""
from urllib.parse import urlsplit

from fastapi import Request
from fastapi.responses import JSONResponse

import config

UNSAFE = {"POST", "PUT", "PATCH", "DELETE"}

CSP = "; ".join([
    "default-src 'self'",
    "script-src 'self' 'wasm-unsafe-eval'",        # the in-browser AI model runs as WebAssembly
    "worker-src 'self' blob:",
    "style-src 'self' 'unsafe-inline'",            # React sets a few inline style attributes
    "img-src 'self' data: blob:",
    "font-src 'self' data:",
    "connect-src 'self' https://api.open-meteo.com https://geocoding-api.open-meteo.com",
    "manifest-src 'self'",
    "object-src 'none'",
    "base-uri 'self'",
    "form-action 'self'",
    "frame-ancestors 'none'",
])


def _allowed_origins(request: Request) -> set[str]:
    hosts = {request.headers.get("host", "")}
    if config.PUBLIC_URL:
        hosts.add(urlsplit(config.PUBLIC_URL).netloc)
    return {h.lower() for h in hosts if h}


async def origin_check(request: Request, call_next):
    if request.method in UNSAFE and request.url.path.startswith("/api/"):
        origin = request.headers.get("origin")
        if origin and urlsplit(origin).netloc.lower() not in _allowed_origins(request):
            return JSONResponse({"detail": "This request came from another website, so Peheraav blocked it."}, status_code=403)
    return await call_next(request)
