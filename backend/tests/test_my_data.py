"""Your own data: the export file, and deleting your own name."""

from sqlmodel import select

from app.models import User, WatchedNote

from .conftest import login


def test_the_export_holds_what_is_yours(client, browser):
    login(client, "marc", admin=True)
    lena = browser()
    me = login(lena, "lena")
    w = lena.post("/api/watched", json={"movie_id": 694}).json()
    lena.post(f"/api/watched/{w['id']}/rating", json={"stars": 4})
    lena.post(f"/api/watched/{w['id']}/notes", json={"text": "Here's Johnny!"})
    lena.post("/api/suggestions", json={"movie_id": 348})
    lena.post("/api/features", json={"text": "Serien bitte"})
    client.post("/api/suggestions", json={"movie_id": 9552})  # marc's: not in lena's file

    r = lena.get("/api/users/me/export")
    assert r.status_code == 200
    assert r.headers["content-disposition"] == 'attachment; filename="screenmates-lena.json"'
    d = r.json()
    assert d["profile"]["name"] == "lena" and d["profile"]["id"] == me["id"]
    assert [(x["film"], x["stars"]) for x in d["ratings"]] == [("Shining", 4)]
    assert [x["text"] for x in d["comments"]] == ["Here's Johnny!"]
    assert [x["film"] for x in d["suggestions"]] == ["Alien"]
    assert [x["text"] for x in d["wishes"]] == ["Serien bitte"]
    assert d["groups"][0]["group"] == "Unsere Gruppe" and d["browsers_with_this_name"] == 1
    assert "Der Exorzist" not in r.text


def test_deleting_your_own_name(client, browser, db):
    login(client, "marc", admin=True)
    lena = browser()
    me = login(lena, "lena")
    w = lena.post("/api/watched", json={"movie_id": 694}).json()
    lena.post(f"/api/watched/{w['id']}/notes", json={"text": "bleibt, ohne Namen"})
    assert lena.delete("/api/users/me", params={"name": "Lena"}).status_code == 422  # typed differently
    assert lena.delete("/api/users/me", params={"name": " lena "}).status_code == 200
    assert db.get(User, me["id"]) is None
    # The browser has no name any more (it still holds its valid invitation, so it may make a new one).
    r = lena.get("/api/users").json()
    assert r["ich"] is None and r["auf_geraet"] == [] and "lena" not in [u["name"] for u in r["users"]]
    n = db.exec(select(WatchedNote)).one()
    assert (n.text, n.user_id) == ("bleibt, ohne Namen", None)


def test_the_last_admin_cant_delete_themselves(client):
    login(client, "marc", admin=True)
    assert client.delete("/api/users/me", params={"name": "marc"}).status_code == 409
    assert client.get("/api/users/me/export").status_code == 200  # /users/me isn't read as an id


def test_stun_servers_come_from_the_settings(client, kino_on, monkeypatch):
    from app.config import settings

    login(client, "marc")
    assert client.get("/api/kino").json()["ice"] == [{"urls": "stun:stun.l.google.com:19302"}]
    monkeypatch.setattr(settings, "stun_servers", "")
    assert client.get("/api/kino").json()["ice"] == []
