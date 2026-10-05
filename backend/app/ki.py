"""KI-Suche: turn a free-text mood ("70er Okkult-Horror, eher langsam") into films.

The LLM only proposes titles; every proposal is resolved against TMDB (or the
local catalogue), so the client never sees a film that doesn't exist and the
model's output is never trusted beyond "a title and a year".
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
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


@dataclass
class Nutzung:
    """What one request used, as the provider reports it (for the admins' overview)."""

    modell: str = ""
    tokens_ein: int = 0
    tokens_aus: int = 0
    kosten: float | None = None  # USD; only OpenRouter reports it


def _parse(text: str) -> list[dict[str, Any]]:
    match = re.search(r"\[.*\]", text, re.DOTALL)
    if not match:
        raise KIError("Die KI hat keine Filmliste geliefert.")
    try:
        items = json.loads(match.group(0))
    except json.JSONDecodeError as e:
        raise KIError("Die Antwort der KI war kein gültiges JSON.") from e
    return [i for i in items if isinstance(i, dict) and isinstance(i.get("titel") or i.get("originaltitel"), str)]


async def vorschlaege(
    beschreibung: str, anzahl: int, vermeiden: list[str], nutzung: Nutzung | None = None
) -> list[dict[str, Any]]:
    prompt = f"Beschreibung: {beschreibung.strip() or 'Überrasch uns mit einem guten Film.'}\n"
    prompt += f"Schlage {anzahl} passende Filme vor."
    if vermeiden:
        prompt += " Diese kennen wir schon, bitte nicht vorschlagen: " + "; ".join(vermeiden[:150])
    ask = _openrouter if settings.llm_backend == "openrouter" else _anthropic
    nutzung = nutzung if nutzung is not None else Nutzung()
    nutzung.modell = settings.llm_model_name
    try:
        async with httpx.AsyncClient(timeout=60) as client:
            text = await ask(client, prompt, nutzung)
    except httpx.HTTPError as e:
        raise KIError("Die KI ist gerade nicht erreichbar.") from e
    return _parse(text)


async def _anthropic(client: httpx.AsyncClient, prompt: str, nutzung: Nutzung) -> str:
    r = await client.post(
        f"{settings.llm_url}/messages",
        headers={
            "x-api-key": settings.llm_api_key,
            "anthropic-version": "2023-06-01",
            "content-type": "application/json",
        },
        json={
            "model": settings.llm_model_name,
            "max_tokens": 2000,
            "system": SYSTEM,
            "messages": [{"role": "user", "content": prompt}],
        },
    )
    _check(r)
    usage = r.json().get("usage") or {}
    nutzung.tokens_ein = int(usage.get("input_tokens") or 0)
    nutzung.tokens_aus = int(usage.get("output_tokens") or 0)
    return "".join(block.get("text", "") for block in r.json().get("content", []) if block.get("type") == "text")


async def _openrouter(client: httpx.AsyncClient, prompt: str, nutzung: Nutzung) -> str:
    """OpenAI-compatible chat completions, as spoken by OpenRouter."""
    r = await client.post(
        f"{settings.llm_url}/chat/completions",
        headers={
            "authorization": f"Bearer {settings.llm_api_key}",
            "content-type": "application/json",
            # Optional OpenRouter attribution: names the app in the usage overview.
            "x-title": settings.app_name,
        },
        json={
            "model": settings.llm_model_name,
            "max_tokens": 2000,
            "messages": [{"role": "system", "content": SYSTEM}, {"role": "user", "content": prompt}],
            # Reasoning models would think first and often use up max_tokens before the
            # list is written. A list of titles needs knowledge, not thought: off is faster
            # and cheaper. Models that cannot switch it off ignore the setting.
            "reasoning": {"enabled": False},
            # OpenRouter then reports the cost of the request (in USD) along with the tokens.
            "usage": {"include": True},
        },
    )
    _check(r)
    usage = r.json().get("usage") or {}
    nutzung.tokens_ein = int(usage.get("prompt_tokens") or 0)
    nutzung.tokens_aus = int(usage.get("completion_tokens") or 0)
    if isinstance(usage.get("cost"), int | float):
        nutzung.kosten = float(usage["cost"])
    choice = (r.json().get("choices") or [{}])[0]
    content = (choice.get("message") or {}).get("content") or ""
    if isinstance(content, list):  # some models answer in content parts
        content = "".join(part.get("text", "") for part in content if isinstance(part, dict))
    if choice.get("finish_reason") == "length" and "]" not in content:
        raise KIError("Die Antwort der KI war zu lang und wurde abgeschnitten – anderes Modell wählen (LLM_MODEL).")
    return content


def _check(r: httpx.Response) -> None:
    if r.status_code in (401, 403):
        raise KIError("Der API-Key der KI wurde abgelehnt.")
    if r.status_code == 402:
        raise KIError("Das Guthaben beim KI-Anbieter ist aufgebraucht.")
    if r.status_code == 429:
        raise KIError("Die KI ist gerade überlastet – bitte gleich noch einmal versuchen.")
    if r.status_code >= 400:
        raise KIError(f"Die KI antwortete mit Fehler {r.status_code}.")
