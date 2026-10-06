"""The language screenmates speaks: German (the source) or English.

Every request carries the app's language in the `X-Sprache` header; texts the
server writes for that request (errors, shelves, achievements, facts) follow it.
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


class SprachMiddleware:
    """Pure ASGI, so the language reaches sync endpoints in the thread pool too."""

    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            return await self.app(scope, receive, send)
        wert = "de"
        for k, v in scope.get("headers", []):
            if k == b"x-sprache":
                wert = v.decode("latin-1").strip().lower()
                break
        token = _aktuell.set(wert if wert in SPRACHEN else "de")
        try:
            await self.app(scope, receive, send)
        finally:
            _aktuell.reset(token)
