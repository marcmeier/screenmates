"""The Kino's chat and reactions: in memory, per group, polled, and quiet for everyone else."""

from datetime import UTC, datetime

from sqlmodel import Session, select

from app.db import engine
from app.models import Ereignis, KinoState
from app.routers import kinochat, statistik

from .conftest import login


def test_messages_and_reactions(client, browser):
    login(client, "marc")
    lena = browser()
    login(lena, "lena")
    m = client.post("/api/kino/chat", json={"text": "  Popcorn   ist fertig "}).json()
    assert (m["typ"], m["inhalt"]) == ("text", "Popcorn ist fertig")
    r = lena.post("/api/kino/reaktion", json={"emoji": "😱"}).json()
    assert lena.post("/api/kino/reaktion", json={"emoji": "💩"}).status_code == 422
    assert lena.post("/api/kino/chat", json={"text": "   "}).status_code == 422
    # Opening the page: the conversation so far, no stale reactions.
    frisch = lena.get("/api/kino/chat").json()
    assert [e["inhalt"] for e in frisch["eintraege"]] == ["Popcorn ist fertig"]
    assert frisch["letzte"] == r["id"]
    assert "😱" in frisch["reaktionen"]
    # Not to be mixed up with "everything after 0" (an empty chat's first poll).
    assert len(lena.get("/api/kino/chat?seit=0").json()["eintraege"]) == 2
    # Polling: everything after what it has.
    neu = lena.get(f"/api/kino/chat?seit={m['id']}").json()["eintraege"]
    assert [(e["typ"], e["inhalt"]) for e in neu] == [("reaktion", "😱")]
    assert lena.get(f"/api/kino/chat?seit={r['id']}").json()["eintraege"] == []


def test_a_message_does_not_make_every_app_reload(client, browser):
    login(client, "marc")
    lena = browser()
    login(lena, "lena")
    vorher = lena.get("/api/live").json()["stand"]
    client.post("/api/kino/chat", json={"text": "Hallo"})
    client.post("/api/kino/reaktion", json={"emoji": "🍿"})
    assert lena.get("/api/live").json()["stand"] == vorher


def test_too_fast_is_slowed_down(client):
    login(client, "marc")
    for i in range(kinochat.LIMITS["text"][0]):
        assert client.post("/api/kino/chat", json={"text": f"{i}"}).status_code == 201
    assert client.post("/api/kino/chat", json={"text": "noch eins"}).status_code == 429


def test_each_group_has_its_own_chat(client, browser):
    from .conftest import _mitglied

    login(client, "marc")
    with Session(engine) as s:
        from app.models import Gruppe, Mitglied

        s.add(Gruppe(id=2, name="Andere"))
        s.commit()
    tom = browser()
    login(tom, "tom")
    _mitglied("tom", gruppe=2)
    with Session(engine) as s:
        for m in s.exec(select(Mitglied).where(Mitglied.gruppe_id == 1)).all():
            if m.user_id == tom.get("/api/users").json()["ich"]["id"]:
                s.delete(m)
        s.commit()
    client.post("/api/kino/chat", json={"text": "nur für Gruppe 1"})
    assert tom.get("/api/kino/chat").json()["eintraege"] == []


def test_chatting_during_a_show_is_a_secret_achievement_and_counts(client, db, monkeypatch):
    login(client, "marc")
    client.post("/api/kino/chat", json={"text": "vor der Vorstellung"})  # nothing on: doesn't count
    st = db.get(KinoState, 1) or KinoState(id=1)
    st.gestartet = datetime.now(UTC)
    db.add(st)
    db.commit()
    client.post("/api/kino/da")  # watching
    client.post("/api/kino/chat", json={"text": "Buh!"})
    client.post("/api/kino/reaktion", json={"emoji": "😱"})
    with Session(engine) as s:
        assert len(s.exec(select(Ereignis).where(Ereignis.typ == "kino_chat")).all()) == 1
    monkeypatch.setattr(statistik, "_cache", (0.0, []))
    texte = {f["text"]: f["wert"] for f in client.get("/api/statistik").json()["fakten"]}
    assert texte["Nachrichten im Kino-Chat"] == "2"
    assert texte["Reaktion im Kino"] == "1"
