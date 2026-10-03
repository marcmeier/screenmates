"""Who may do what: anonymous reads, user writes, host-only administration."""

import pytest

from .conftest import become_host, login


def test_reads_do_not_create_sessions(client, db):
    from sqlmodel import select

    from app.models import Session

    client.get("/api/users")
    client.get("/api/watched")
    assert db.exec(select(Session)).all() == []
    assert "screenmates_sid" not in client.cookies


@pytest.mark.parametrize(
    ("method", "path", "body"),
    [
        ("post", "/api/watched", {"movie_id": 694}),
        ("post", "/api/wishlist", {"movie_id": 694}),
        ("post", "/api/suggestions", {"movie_id": 694}),
        ("post", "/api/features", {"text": "x"}),
        ("post", "/api/dabei", None),
        ("post", "/api/host", {"an": True, "movie_id": 694}),
    ],
)
def test_writes_require_a_name(client, method, path, body):
    r = getattr(client, method)(path, json=body) if body else getattr(client, method)(path)
    assert r.status_code == 401


@pytest.mark.parametrize(
    ("method", "path", "body"),
    [
        ("put", "/api/info", {"text": "hi"}),
        ("delete", "/api/suggestions/alle", None),
        ("delete", "/api/dabei", None),
        ("get", "/api/host/film", None),
        ("post", "/api/sync", None),
    ],
)
def test_admin_requires_host(client, method, path, body):
    login(client, "marc")
    r = client.request(method.upper(), path, json=body)
    assert r.status_code == 403


def test_duplicate_names_are_rejected(client):
    assert client.post("/api/users", json={"name": "marc"}).status_code == 201
    assert client.post("/api/users", json={"name": "marc"}).status_code == 409
    assert client.post("/api/users", json={"name": ""}).status_code == 422
    assert client.post("/api/users", json={"name": "x" * 31}).status_code == 422


def test_schutz_film_is_never_revealed(client):
    me = login(client, "marc")
    client.post(f"/api/users/{me['id']}/schutz", json={"movie_id": 348})
    r = client.get(f"/api/users/{me['id']}/schutz").json()
    assert r == {"hat_schutz": True}
    listed = client.get("/api/users").json()["users"][0]
    assert "schutz_movie_id" not in listed
    assert 348 not in listed.values()


def test_schutz_login_flow(client, browser):
    me = login(client, "marc")
    client.post(f"/api/users/{me['id']}/schutz", json={"movie_id": 348})

    other = browser()
    assert other.post("/api/users/waehlen", json={"user_id": me["id"]}).status_code == 403
    assert other.post("/api/users/waehlen", json={"user_id": me["id"], "movie_id": 1}).status_code == 403
    ok = other.post("/api/users/waehlen", json={"user_id": me["id"], "movie_id": 348})
    assert ok.status_code == 200
    assert ok.json()["ich"]["name"] == "marc"


def test_schutz_guessing_is_throttled(client, browser):
    me = login(client, "marc")
    client.post(f"/api/users/{me['id']}/schutz", json={"movie_id": 348})
    attacker = browser()
    codes = [
        attacker.post("/api/users/waehlen", json={"user_id": me["id"], "movie_id": guess}).status_code
        for guess in range(1, 11)
    ]
    assert codes[:8] == [403] * 8
    assert codes[8:] == [429, 429]
    # Even the right film is refused while throttled.
    assert attacker.post("/api/users/waehlen", json={"user_id": me["id"], "movie_id": 348}).status_code == 429


def test_cannot_change_someone_elses_schutz(client, browser):
    marc = login(client, "marc")
    other = browser()
    login(other, "lena")
    assert other.post(f"/api/users/{marc['id']}/schutz", json={"movie_id": 1}).status_code == 403
    become_host(other)
    assert other.post(f"/api/users/{marc['id']}/schutz", json={"movie_id": None}).status_code == 200


def test_host_mode_setup_and_unlock(client, browser):
    login(client, "marc")
    assert client.get("/api/host").json() == {"host": False, "eingerichtet": False}
    become_host(client, film=694)  # first host picks the film
    assert client.get("/api/host/film").json()["movie"]["id"] == 694

    lena = browser()
    login(lena, "lena")
    assert lena.post("/api/host", json={"an": True, "movie_id": 348}).status_code == 403
    assert lena.get("/api/host").json() == {"host": False, "eingerichtet": True}
    become_host(lena, film=694)

    # Logging out (or switching name) drops host rights.
    lena.post("/api/users/waehlen", json={"user_id": None})
    assert lena.get("/api/host").json()["host"] is False


def test_switching_name_drops_host(client):
    login(client, "marc")
    become_host(client)
    login(client, "lena")
    assert client.get("/api/host").json()["host"] is False


def test_delete_user_is_host_only(client, browser):
    marc = login(client, "marc")
    other = browser()
    login(other, "lena")
    assert other.delete(f"/api/users/{marc['id']}").status_code == 403
    become_host(other)
    assert other.delete(f"/api/users/{marc['id']}").status_code == 200
    assert [u["name"] for u in other.get("/api/users").json()["users"]] == ["lena"]
    # marc's session survives, but is no longer bound to a user.
    assert client.get("/api/users").json()["ich"] is None
