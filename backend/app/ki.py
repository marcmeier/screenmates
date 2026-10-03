"""KI-Suche: turn a free-text mood ("70er Okkult-Horror, eher langsam") into films.

The LLM only proposes titles; every proposal is resolved against TMDB (or the
local catalogue), so the client never sees a film that doesn't exist and the
model's output is never trusted beyond "a title and a year".
"""

from __future__ import annotations

import json
import re
from typing import Any

import httpx

from .config import settings

SYSTEM = (
    "Du bist ein Filmkenner und hilfst einer Freundesgruppe, den nächsten Filmabend "
    "auszuwählen. Antworte ausschließlich mit einem JSON-Array, ohne Fließtext davor oder "
    'danach. Jedes Element hat die Form {"titel": string, "originaltitel": string, '
    '"jahr": number, "warum": string}. "warum" ist ein kurzer deutscher Satz, warum der Film '
    "zur Beschreibung passt. Schlage nur Filme vor, die es wirklich gibt."
)


class KIError(Exception):
    pass


def _parse(text: str) -> list[dict[str, Any]]:
    match = re.search(r"\[.*\]", text, re.DOTALL)
    if not match:
        raise KIError("Die KI hat keine Filmliste geliefert.")
    try:
        items = json.loads(match.group(0))
    except json.JSONDecodeError as e:
        raise KIError("Die Antwort der KI war kein gültiges JSON.") from e
    return [i for i in items if isinstance(i, dict) and isinstance(i.get("titel") or i.get("originaltitel"), str)]


async def vorschlaege(beschreibung: str, anzahl: int, vermeiden: list[str]) -> list[dict[str, Any]]:
    prompt = f"Beschreibung: {beschreibung.strip() or 'Überrasch uns mit einem guten Film.'}\n"
    prompt += f"Schlage {anzahl} passende Filme vor."
    if vermeiden:
        prompt += " Diese kennen wir schon, bitte nicht vorschlagen: " + "; ".join(vermeiden[:150])
    try:
        async with httpx.AsyncClient(timeout=60) as client:
            r = await client.post(
                f"{settings.llm_base_url}/messages",
                headers={
                    "x-api-key": settings.llm_api_key,
                    "anthropic-version": "2023-06-01",
                    "content-type": "application/json",
                },
                json={
                    "model": settings.llm_model,
                    "max_tokens": 2000,
                    "system": SYSTEM,
                    "messages": [{"role": "user", "content": prompt}],
                },
            )
    except httpx.HTTPError as e:
        raise KIError("Die KI ist gerade nicht erreichbar.") from e
    if r.status_code >= 400:
        raise KIError(f"Die KI antwortete mit Fehler {r.status_code}.")
    text = "".join(block.get("text", "") for block in r.json().get("content", []) if block.get("type") == "text")
    return _parse(text)
