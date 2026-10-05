"""Who may do what: anonymous reads, user writes, admin-only administration."""

import pytest

from .conftest import become_admin, login


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
        ("get", "/api/admin/users", None),
        ("get", "/api/admin/zugang", None),
        ("put", "/api/admin/zugang", {"frage": "x", "movie_id": 1}),
        ("post", "/api/admin/users", {"name": "neu"}),
        ("post", "/api/sync", None),
    ],
)
def test_admin_requires_admin(client, method, path, body):
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
    become_admin(other)
    assert other.post(f"/api/users/{marc['id']}/schutz", json={"movie_id": None}).status_code == 200


def test_delete_user_is_admin_only(client, browser):
    marc = login(client, "marc")
    other = browser()
    login(other, "lena")
    assert other.delete(f"/api/users/{marc['id']}").status_code == 403
    become_admin(other)
    assert other.delete(f"/api/users/{marc['id']}").status_code == 200
    assert [u["name"] for u in other.get("/api/users").json()["users"]] == ["lena"]
    # marc's session survives, but is no longer bound to a user.
    assert client.get("/api/users").json()["ich"] is None
