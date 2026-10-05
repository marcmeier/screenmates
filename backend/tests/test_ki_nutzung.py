"""The admins' overview of the KI search: requests, tokens, cost."""

import json

import httpx
import respx

from .conftest import become_admin, login

ANTWORT = '[{"titel": "Alien", "originaltitel": "Alien", "jahr": 1979, "warum": "Isolation"}]'


@respx.mock
def test_requests_are_counted_with_tokens_and_cost(client, browser, monkeypatch):
    from app.config import settings

    monkeypatch.setattr(settings, "llm_api_key", "sk-or-v1-test")
    login(client, "marc")
    become_admin(client)
    lena = browser()
    me = login(lena, "lena")
    route = respx.post("https://openrouter.ai/api/v1/chat/completions")
    route.mock(
        return_value=httpx.Response(
            200,
            json={
                "choices": [{"message": {"content": ANTWORT}}],
                "usage": {"prompt_tokens": 300, "completion_tokens": 120, "cost": 0.00042},
            },
        )
    )
    lena.post("/api/ki-suche", json={"beschreibung": "Weltraum", "mit_sammlung": True})
    lena.post("/api/ki-suche", json={"beschreibung": "Noch mal", "mit_sammlung": True})
    assert json.loads(route.calls.last.request.content)["usage"] == {"include": True}  # OpenRouter reports the cost
        b'":true', b'": true'
    )
    route.mock(return_value=httpx.Response(429))
    assert lena.post("/api/ki-suche", json={"beschreibung": "x"}).status_code == 502

    n = client.get("/api/admin/ki-nutzung").json()
    assert n["aktiv"] is True and n["anbieter"] == "openrouter"
    heute = n["summen"]["heute"]
    assert (heute["anfragen"], heute["fehler"], heute["tokens_ein"], heute["tokens_aus"]) == (3, 1, 600, 240)
    assert abs(heute["kosten"] - 0.00084) < 1e-9
    assert heute["ohne_kosten"] == 1  # the failed one wasn't priced
    assert n["pro_person"][0]["user_id"] == me["id"]
    assert n["letzte"][0]["ok"] is False and "überlastet" in n["letzte"][0]["fehler"]


def test_only_server_admins_see_it(client):
    login(client, "marc")
    assert client.get("/api/admin/ki-nutzung").status_code == 403
