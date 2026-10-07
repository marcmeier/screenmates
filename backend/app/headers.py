"""Security headers on every response.

The app only runs its own scripts. Pictures may come from anywhere over HTTPS
(TMDB posters, images in the info card), trailers from youtube-nocookie.com.
Inline styles stay allowed: Vue's style bindings and sanitised markdown use them.
FastAPI's /docs page loads Swagger UI from a CDN, so it gets no CSP.
HSTS is left to the reverse proxy that terminates HTTPS.
"""

from __future__ import annotations

CSP = "; ".join(
    [
        "default-src 'self'",
        "script-src 'self'",
        "style-src 'self' 'unsafe-inline'",
        "img-src 'self' data: blob: https:",
        "font-src 'self' data:",  # Vite inlines small font files
        "connect-src 'self'",
        "media-src 'self' blob:",
        "frame-src https://www.youtube-nocookie.com",
        "worker-src 'self'",
        "manifest-src 'self'",
        "object-src 'none'",
        "base-uri 'self'",
        "form-action 'self'",
        "frame-ancestors 'none'",
    ]
)
IMMER = [
    (b"x-content-type-options", b"nosniff"),
    (b"referrer-policy", b"strict-origin-when-cross-origin"),
    (b"x-frame-options", b"DENY"),
    (b"permissions-policy", b"camera=(), geolocation=(), payment=(), usb=()"),
]
OHNE_CSP = ("/docs", "/redoc", "/openapi.json")


class SecurityHeaders:
    """Pure ASGI middleware: adds the headers unless a response already set them."""

    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            return await self.app(scope, receive, send)
        extra = IMMER if scope["path"].startswith(OHNE_CSP) else [*IMMER, (b"content-security-policy", CSP.encode())]

        async def senden(message):
            if message["type"] == "http.response.start":
                headers = list(message.get("headers", []))
                schon = {k.lower() for k, _ in headers}
                headers += [(k, v) for k, v in extra if k not in schon]
                message["headers"] = headers
            await send(message)

        await self.app(scope, receive, senden)
