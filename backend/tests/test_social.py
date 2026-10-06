"""Watched log, ratings, notes, lists, wishes, wheel — and that deletes cascade."""

import json

import httpx
import pytest
import respx
from sqlmodel import select

from app.models import NoteHeart, WatchedNote, WatchedParticipant, WatchedRating

from .conftest import become_admin, login


def test_watching_fulfils_wishlist_and_suggestions(client):
    me = login(client, "marc")
    client.post("/api/wishlist", json={"movie_id": 694})
    client.post("/api/suggestions", json={"movie_id": 694})
    entry = client.post("/api/watched", json={"movie_id": 694}).json()
    assert entry["participants"] == [me["id"]]
    assert client.get("/api/wishlist").json()["wishlist"] == []
    assert client.get("/api/suggestions").json()["suggestions"] == []
    status = client.get("/api/status").json()
    assert (status["wishlist_count"], status["watched_count"]) == (0, 1)


def test_rating_validation_and_upsert(client):
    me = login(client, "marc")
    wid = client.post("/api/watched", json={"movie_id": 694}).json()["id"]
    assert client.post(f"/api/watched/{wid}/rating", json={"stars": 0}).status_code == 422
    assert client.post(f"/api/watched/{wid}/rating", json={"stars": 6}).status_code == 422
    client.post(f"/api/watched/{wid}/rating", json={"stars": 2})
    entry = client.post(f"/api/watched/{wid}/rating", json={"stars": 4}).json()
    assert [(r["user_id"], r["stars"]) for r in entry["ratings"]] == [(me["id"], 4)]
    assert entry["rating_avg"] == 4.0
    assert "id" in entry["ratings"][0]


def test_only_own_rating_can_be_deleted(client, browser):
    login(client, "marc")
    wid = client.post("/api/watched", json={"movie_id": 694}).json()["id"]
    rid = client.post(f"/api/watched/{wid}/rating", json={"stars": 5}).json()["ratings"][0]["id"]
    lena = browser()
    login(lena, "lena")
    assert lena.delete(f"/api/watched/rating/{rid}").status_code == 403
    assert client.delete(f"/api/watched/rating/{rid}").status_code == 200


def test_notes_are_threaded_and_validated(client):
    login(client, "marc")
    wid = client.post("/api/watched", json={"movie_id": 694}).json()["id"]
    other = client.post("/api/watched", json={"movie_id": 348}).json()["id"]
    root = client.post(f"/api/watched/{wid}/notes", json={"text": "Klassiker"}).json()["notes"][0]
    entry = client.post(f"/api/watched/{wid}/notes", json={"text": "Absolut", "parent_id": root["id"]}).json()
    assert len(entry["notes"]) == 1
    assert entry["notes"][0]["replies"][0]["text"] == "Absolut"
    assert client.post(f"/api/watched/{other}/notes", json={"text": "x", "parent_id": root["id"]}).status_code == 422
    assert client.post(f"/api/watched/{wid}/notes", json={"text": ""}).status_code == 422


def test_hearts_toggle(client):
    login(client, "marc")
    wid = client.post("/api/watched", json={"movie_id": 694}).json()["id"]
    nid = client.post(f"/api/watched/{wid}/notes", json={"text": "gut"}).json()["notes"][0]["id"]
    assert client.post("/api/watched/hearts", json={"note_id": nid}).json() == {"hearted": True}
    assert client.post("/api/watched/hearts", json={"note_id": nid}).json() == {"hearted": False}


def test_deleting_watched_cascades(client, db):
    login(client, "marc")
    become_admin(client)
    wid = client.post("/api/watched", json={"movie_id": 694}).json()["id"]
    client.post(f"/api/watched/{wid}/rating", json={"stars": 5})
    nid = client.post(f"/api/watched/{wid}/notes", json={"text": "a"}).json()["notes"][0]["id"]
    client.post(f"/api/watched/{wid}/notes", json={"text": "b", "parent_id": nid})
    client.post("/api/watched/hearts", json={"note_id": nid})

    assert client.delete(f"/api/watched/{wid}").status_code == 200
    for model in (WatchedRating, WatchedNote, NoteHeart, WatchedParticipant):
        assert db.exec(select(model)).all() == [], model.__name__


def test_deleting_user_keeps_their_notes_but_drops_ratings(client, browser, db):
    marc = login(client, "marc")
    wid = client.post("/api/watched", json={"movie_id": 694}).json()["id"]
    client.post(f"/api/watched/{wid}/rating", json={"stars": 5})
    client.post(f"/api/watched/{wid}/notes", json={"text": "bleibt"})

    host = browser()
    login(host, "lena")
    become_admin(host)
    host.delete(f"/api/users/{marc['id']}")

    entry = host.get("/api/watched").json()["watched"][0]
    assert entry["ratings"] == []
    assert entry["participants"] == []
    assert entry["notes"][0]["text"] == "bleibt"
    assert entry["notes"][0]["user_id"] is None


def test_hidden_entries(client):
    login(client, "marc")
    wid = client.post("/api/watched", json={"movie_id": 694}).json()["id"]
    client.patch(f"/api/watched/{wid}", json={"hidden": True})
    assert client.get("/api/watched").json()["watched"] == []
    assert len(client.get("/api/watched", params={"alle": True}).json()["watched"]) == 1


def test_suggestions_grouped_and_ranked(client, browser):
    marc = login(client, "marc")
    lena_c = browser()
    lena = login(lena_c, "lena")
    client.post("/api/suggestions", json={"movie_id": 348})
    client.post("/api/suggestions", json={"movie_id": 694})
    client.post("/api/suggestions", json={"movie_id": 694})  # idempotent
    lena_c.post("/api/suggestions", json={"movie_id": 694})
    s = client.get("/api/suggestions").json()["suggestions"]
    assert [(m["id"], sorted(m["von"])) for m in s] == [(694, sorted([marc["id"], lena["id"]])), (348, [marc["id"]])]

    client.delete("/api/suggestions/694")
    s = client.get("/api/suggestions").json()["suggestions"]
    assert {m["id"]: m["von"] for m in s}[694] == [lena["id"]]


def test_spin_is_weighted_by_votes(client, browser):
    login(client, "marc")
    client.post("/api/suggestions", json={"movie_id": 694})
    pool = client.get("/api/spin").json()["pool"]
    assert [(m["id"], m["gewicht"]) for m in pool] == [(694, 1)]
    assert client.post("/api/spin").json()["pick"]["id"] == 694


def test_spin_falls_back_to_wishlist(client):
    login(client, "marc")
    assert client.post("/api/spin").json()["pick"] is None
    client.post("/api/wishlist", json={"movie_id": 348})
    assert client.post("/api/spin").json()["pick"]["id"] == 348


def test_dabei_toggle_and_reset(client):
    login(client, "marc")
    assert client.post("/api/dabei").json() == {"dabei": True, "rueckmeldung": "ja"}
    assert client.get("/api/users").json()["ich"]["dabei"] is True
    become_admin(client)
    client.delete("/api/dabei")
    assert client.get("/api/users").json()["ich"]["dabei"] is False


def test_the_welcome_is_seen_once_and_keeps_the_look(client):
    login(client, "marc")
    client.put("/api/users/me/design", json={"theme": "neon", "schrift": "serif"})
    client.post("/api/users/me/willkommen")
    assert client.get("/api/users").json()["ich"]["design"] == {"theme": "neon", "schrift": "serif", "willkommen": True}
    client.put("/api/users/me/design", json={"theme": "wald", "schrift": "serif"})
    assert client.get("/api/users").json()["ich"]["design"]["willkommen"] is True


def test_feature_permissions(client, browser):
    login(client, "marc")
    fid = client.post("/api/features", json={"text": "Dark Mode"}).json()["id"]
    lena = browser()
    login(lena, "lena")
    assert lena.post(f"/api/features/{fid}/vote").json()["votes"] == 1
    assert lena.post(f"/api/features/{fid}/vote").json()["votes"] == 0
    assert lena.patch(f"/api/features/{fid}", json={"text": "hijack"}).status_code == 403
    assert lena.delete(f"/api/features/{fid}").status_code == 403
    assert client.patch(f"/api/features/{fid}/done", json={"done": True}).status_code == 403
    assert client.patch(f"/api/features/{fid}", json={"text": "Dunkles Theme"}).json()["text"] == "Dunkles Theme"


def test_info_markdown_roundtrip(client):
    login(client, "marc")
    become_admin(client)
    client.put("/api/info", json={"text": "# Hallo"})
    assert client.get("/api/info").json()["text"] == "# Hallo"


def test_ki_without_key_is_503(client):
    assert client.post("/api/ki-suche", json={"beschreibung": "x"}).status_code == 503


@respx.mock
def test_ki_resolves_titles_against_catalogue(client, monkeypatch):
    from app.config import settings

    monkeypatch.setattr(settings, "llm_api_key", "k")
    login(client, "marc")
    client.post("/api/watched", json={"movie_id": 948})  # Halloween: already seen
    answer = (
        'Gerne! [{"titel": "Alien", "originaltitel": "Alien", "jahr": 1979, "warum": "Isolation"},'
        ' {"titel": "Halloween", "originaltitel": "Halloween", "jahr": 1978, "warum": "Slasher"},'
        ' {"titel": "Gibt es nicht", "originaltitel": "Nope Nope", "jahr": 2001, "warum": "?"}]'
    )
    respx.post("https://api.anthropic.com/v1/messages").mock(
        return_value=httpx.Response(200, json={"content": [{"type": "text", "text": answer}]})
    )
    r = client.post("/api/ki-suche", json={"beschreibung": "Weltraum", "mit_sammlung": True}).json()
    assert [(m["title"], m["warum"]) for m in r["results"]] == [("Alien", "Isolation")]


@respx.mock
@pytest.mark.parametrize("provider", ["openrouter", ""])  # explicit, or guessed from the "sk-or-" key
def test_ki_via_openrouter(client, monkeypatch, provider):
    from app.config import settings

    monkeypatch.setattr(settings, "llm_api_key", "sk-or-v1-test")
    monkeypatch.setattr(settings, "llm_provider", provider)
    login(client, "marc")
    answer = '[{"titel": "Alien", "originaltitel": "Alien", "jahr": 1979, "warum": "Isolation"}]'
    route = respx.post("https://openrouter.ai/api/v1/chat/completions").mock(
        return_value=httpx.Response(200, json={"choices": [{"message": {"role": "assistant", "content": answer}}]})
    )
    r = client.post("/api/ki-suche", json={"beschreibung": "Weltraum", "mit_sammlung": True}).json()
    assert [(m["title"], m["warum"]) for m in r["results"]] == [("Alien", "Isolation")]
    sent = route.calls.last.request
    assert sent.headers["authorization"] == "Bearer sk-or-v1-test"
    body = json.loads(sent.content)
    assert body["model"] == "deepseek/deepseek-v4.1-flash"
    assert body["messages"][0]["role"] == "system"
    assert body["reasoning"] == {"enabled": False}


@respx.mock
def test_ki_model_and_url_can_be_overridden(client, monkeypatch):
    from app.config import settings

    monkeypatch.setattr(settings, "llm_api_key", "sk-or-v1-test")
    monkeypatch.setattr(settings, "llm_model", "google/gemini-3.8-flash")
    monkeypatch.setattr(settings, "llm_base_url", "https://llm.example.com/v1/")
    login(client, "marc")
    route = respx.post("https://llm.example.com/v1/chat/completions").mock(
        return_value=httpx.Response(200, json={"choices": [{"message": {"content": "[]"}}]})
    )
    assert client.post("/api/ki-suche", json={"beschreibung": "x"}).status_code == 200
    assert json.loads(route.calls.last.request.content)["model"] == "google/gemini-3.8-flash"


@respx.mock
@pytest.mark.parametrize(
    ("status", "meldung"), [(401, "abgelehnt"), (402, "Guthaben"), (429, "überlastet"), (500, "Fehler 500")]
)
def test_ki_errors_are_explained(client, monkeypatch, status, meldung):
    from app.config import settings

    monkeypatch.setattr(settings, "llm_api_key", "sk-or-v1-test")
    login(client, "marc")
    respx.post("https://openrouter.ai/api/v1/chat/completions").mock(return_value=httpx.Response(status))
    r = client.post("/api/ki-suche", json={"beschreibung": "x"})
    assert r.status_code == 502
    assert meldung in r.json()["detail"]


@respx.mock
def test_ki_truncated_answer_is_explained(client, monkeypatch):
    from app.config import settings

    monkeypatch.setattr(settings, "llm_api_key", "sk-or-v1-test")
    login(client, "marc")
    cut = {"choices": [{"finish_reason": "length", "message": {"content": '[{"titel": "Al'}}]}
    respx.post("https://openrouter.ai/api/v1/chat/completions").mock(return_value=httpx.Response(200, json=cut))
    r = client.post("/api/ki-suche", json={"beschreibung": "x"})
    assert r.status_code == 502
    assert "abgeschnitten" in r.json()["detail"]


@respx.mock
def test_sync_upserts_canon(client, tmdb_on):
    login(client, "marc")
    become_admin(client)
    page = {"results": [{"id": 9000 + i, "title": f"Film {i}", "genre_ids": [27]} for i in range(3)]}
    respx.get("https://api.themoviedb.org/3/discover/movie").mock(return_value=httpx.Response(200, json=page))
    r = client.post("/api/sync").json()
    assert r["neu"] == 3
    status = client.get("/api/status").json()
    assert status["movie_count"] == 15
    assert status["last_sync"] is not None


def test_watched_can_be_filtered_by_film(client):
    login(client, "marc")
    client.post("/api/watched", json={"movie_id": 694})
    client.post("/api/watched", json={"movie_id": 348})
    client.post("/api/watched", json={"movie_id": 694})  # watched twice
    entries = client.get("/api/watched", params={"movie_id": 694}).json()["watched"]
    assert [e["movie_id"] for e in entries] == [694, 694]
    assert client.get("/api/watched", params={"movie_id": 9552}).json()["watched"] == []
