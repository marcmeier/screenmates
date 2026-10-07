"""The language screenmates speaks: German (the source) or English.

Every request carries the app's language in the `Accept-Language` header (the
app sets it to its own choice; `X-Sprache` from older apps still works); texts
the server writes for that request (errors, shelves, achievements, facts) follow it.
Texts for someone else - push messages, the bell, calendar feeds - follow that
person's choice (`design.sprache` in the profile), via `als(...)`.

Texts stay German in the code; `tr()` looks up the English version in
`texte_en.EN` (German text → English text, both with the same {placeholders}).
"""

from __future__ import annotations

import json
from collections.abc import Iterator
from contextlib import contextmanager
from contextvars import ContextVar

from .texte_en import EN

SPRACHEN = ("de", "en")
_aktuell: ContextVar[str] = ContextVar("sprache", default="de")


def aktuell() -> str:
    return _aktuell.get()


def tr(de: str, **werte) -> str:
    """German text → the current language, with {placeholders} filled in."""
    text = EN.get(de, de) if _aktuell.get() == "en" else de
    return text.format(**werte) if werte else text


def von(user) -> str:
    """Someone's chosen language (German if they never chose)."""
    try:
        s = json.loads(getattr(user, "design", "") or "{}").get("sprache")
    except ValueError:
        s = None
    return s if s in SPRACHEN else "de"


@contextmanager
def als(sprache: str) -> Iterator[None]:
    """Write texts in another language for a while, e.g. a push message for someone else."""
    token = _aktuell.set(sprache if sprache in SPRACHEN else "de")
    try:
        yield
    finally:
        _aktuell.reset(token)


def _bevorzugt(accept_language: str) -> str:
    """'en-GB,en;q=0.9,de;q=0.8' -> 'en': the first of our languages, by the browser's weights."""
    kandidaten = []
    for i, teil in enumerate(accept_language.split(",")):
        sprache, _, rest = teil.strip().partition(";")
        q = 1.0
        if rest.strip().startswith("q="):
            try:
                q = float(rest.strip()[2:])
            except ValueError:
                q = 0.0
        kandidaten.append((-q, i, sprache.strip()[:2].lower()))
    return next((s for _, _, s in sorted(kandidaten) if s in SPRACHEN), "de")


class SprachMiddleware:
    """Pure ASGI, so the language reaches sync endpoints in the thread pool too."""

    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            return await self.app(scope, receive, send)
        headers = dict(scope.get("headers", []))
        if b"x-sprache" in headers:
            wert = headers[b"x-sprache"].decode("latin-1").strip().lower()
        else:
            wert = _bevorzugt(headers.get(b"accept-language", b"").decode("latin-1"))
        token = _aktuell.set(wert if wert in SPRACHEN else "de")
        try:
            await self.app(scope, receive, send)
        finally:
            _aktuell.reset(token)
