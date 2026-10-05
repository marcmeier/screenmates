"""Guestbook: comments with replies leave a placeholder when deleted, the thread stays."""

from .conftest import login


def eintrag(client):
    return client.post("/api/watched", json={"movie_id": 694}).json()["id"]


def notiz(c, wid, text, parent=None):
    r = c.post(f"/api/watched/{wid}/notes", json={"text": text, "parent_id": parent})
    assert r.status_code == 201
    return r.json()


def baum(c):
    return c.get("/api/watched").json()["watched"][0]["notes"]


def test_without_replies_a_comment_is_simply_gone(client):
    login(client, "marc")
    wid = eintrag(client)
    nid = notiz(client, wid, "Toller Film")["notes"][0]["id"]
    assert client.delete(f"/api/watched-notes/{nid}").json() == {"ok": True, "platzhalter": False}
    assert baum(client) == []


def test_with_replies_it_becomes_a_placeholder_and_the_thread_stays(client, browser):
    login(client, "marc")
    lena = browser()
    login(lena, "lena")
    wid = eintrag(client)
    nid = notiz(client, wid, "Bester Abend!")["notes"][0]["id"]
    lena.post("/api/watched/hearts", json={"note_id": nid})
    notiz(lena, wid, "Finde ich auch", parent=nid)
    assert client.delete(f"/api/watched-notes/{nid}").json()["platzhalter"] is True
    [platz] = baum(lena)
    assert (platz["text"], platz["geloescht"], platz["hearts"]) == ("", "ersteller", [])
    assert [r["text"] for r in platz["replies"]] == ["Finde ich auch"]
    # A placeholder can't be hearted, but the conversation can go on.
    assert lena.post("/api/watched/hearts", json={"note_id": nid}).status_code == 409
    notiz(lena, wid, "Noch eine Antwort", parent=nid)


def test_an_admin_removing_it_says_so(client, browser):
    login(client, "marc", admin=True)
    lena = browser()
    login(lena, "lena")
    wid = eintrag(client)
    nid = notiz(lena, wid, "Hmm")["notes"][0]["id"]
    notiz(client, wid, "Wieso?", parent=nid)
    client.delete(f"/api/watched-notes/{nid}")
    assert baum(client)[0]["geloescht"] == "admin"


def test_the_placeholder_goes_with_its_last_reply(client, browser):
    login(client, "marc")
    lena = browser()
    login(lena, "lena")
    wid = eintrag(client)
    oben = notiz(client, wid, "Oben")["notes"][0]["id"]
    antwort = notiz(lena, wid, "Antwort", parent=oben)["notes"][0]["replies"][0]["id"]
    client.delete(f"/api/watched-notes/{oben}")  # placeholder
    lena.delete(f"/api/watched-notes/{antwort}")  # last reply gone …
    assert baum(client) == []  # … and the empty placeholder with it


def test_deleted_comments_leave_feed_and_achievements(client, browser):
    from sqlmodel import Session

    from app import erfolge
    from app.db import engine

    login(client, "marc")
    lena = browser()
    me = login(lena, "lena")
    wid = eintrag(client)
    client.post(f"/api/watched/{wid}/dabei", json={"user_ids": [1, me["id"]]})
    client.post(f"/api/watched/{wid}/rating", json={"stars": 4})
    nid = notiz(lena, wid, "Ein wirklich langer Kommentar zum Abend")["notes"][0]["id"]
    notiz(client, wid, "Stimmt", parent=nid)
    with Session(engine) as db:
        assert erfolge.stand(db)[me["id"]]["gaestebuch"] == 1
    lena.delete(f"/api/watched-notes/{nid}")
    with Session(engine) as db:
        assert erfolge.stand(db)[me["id"]]["gaestebuch"] == 0
    texte = [e.get("text") for e in client.get("/api/events").json()["events"] if e["typ"] == "kommentar"]
    assert "Ein wirklich langer Kommentar zum Abend" not in texte
