"""The danger zone: admins clear areas or start afresh, with a confirmation and a backup first."""

import pytest
from sqlmodel import Session, select

from app.db import engine
from app.models import Abend, Erfolg, Feature, KinoNachricht, Mitglied, Suggestion, User, Watched
from app.routers import reset

from .conftest import login, rein
from .test_umfrage import in_tagen


@pytest.fixture
def voll(client, browser):
    """marc (admin) and lena after a busy test phase."""
    marc = login(client, "marc", admin=True)
    lena = browser()
    lena.me = login(lena, "lena")
    w = client.post("/api/watched", json={"movie_id": 694}).json()["id"]
    lena.post(f"/api/watched/{w}/rating", json={"stars": 4})
    lena.post(f"/api/watched/{w}/notes", json={"text": "Test"})
    client.post("/api/suggestions", json={"movie_id": 948})
    client.post("/api/wishlist", json={"movie_id": 4232})
    client.put("/api/termin", json={"termin": in_tagen(3)})
    client.post("/api/dabei")
    client.post("/api/kino/chat", json={"text": "Test"})
    lena.post("/api/features", json={"text": "Testwunsch"})
    client.post("/api/admin/gruppen/1/einladungen", json={"direkt": True})
    client.me = marc
    return {"marc": client, "lena": lena}


def anzahl(modell, *bedingungen):
    with Session(engine) as s:
        return len(s.exec(select(modell).where(*bedingungen)).all())


def auftrag(c, *bereiche, wort="LÖSCHEN"):
    return c.post("/api/admin/reset", json={"bereiche": list(bereiche), "bestaetigung": wort})


def test_only_server_admins(voll):
    assert voll["lena"].get("/api/admin/reset").status_code == 403
    assert auftrag(voll["lena"], "chronik").status_code == 403


def test_the_overview_counts_what_would_go(voll):
    r = voll["marc"].get("/api/admin/reset").json()
    zahlen = {b["key"]: b["anzahl"] for b in r["bereiche"]}
    assert zahlen["chronik"] == 1 and zahlen["wuensche"] == 1 and zahlen["kino"] == 1
    assert zahlen["filmabend"] == 3  # suggestion, wishlist entry, date
    assert r["neustart"] == 3  # lena, the link she came in with, and the admin's new one
    assert r["bestaetigung"] == "LÖSCHEN"


def test_without_the_word_nothing_happens(voll):
    assert auftrag(voll["marc"], "chronik", wort="ja").status_code == 422
    assert anzahl(Watched) == 1
    assert auftrag(voll["marc"], "quatsch", wort="löschen").status_code == 422


def test_one_area_at_a_time(voll):
    r = voll["marc"].post("/api/admin/reset", json={"bereiche": ["chronik", "kino"], "bestaetigung": "löschen"}).json()
    assert r["geleert"] == {"chronik": 1, "kino": 1}
    assert anzahl(Watched) == 0 and anzahl(KinoNachricht) == 0
    assert anzahl(Feature) == 1 and anzahl(Suggestion) == 1  # untouched


def test_the_evening_is_cleared_but_the_group_stays(voll):
    voll["marc"].post("/api/admin/reset", json={"bereiche": ["filmabend"], "bestaetigung": "LÖSCHEN"})
    assert anzahl(Suggestion) == 0
    assert voll["marc"].get("/api/termin").json()["termin"] is None
    assert anzahl(Mitglied, Mitglied.dabei) == 0
    with Session(engine) as s:
        assert s.get(Abend, 1).gastgeber_id is None
    assert voll["marc"].get("/api/users").json()["gruppe"]["id"] == 1


def test_starting_afresh_keeps_only_the_admin_and_backs_up_first(voll, browser):
    before = len(reset.backups())
    r = voll["marc"].post("/api/admin/reset", json={"bereiche": ["neustart"], "bestaetigung": "LÖSCHEN"}).json()
    assert r["geleert"]["neustart"] == 3
    assert r["backup"].startswith("backup-vor-reset-") and len(reset.backups()) == before + 1
    assert [u.name for u in Session(engine).exec(select(User)).all()] == ["marc"]
    assert anzahl(Watched) == 0 and anzahl(Feature) == 0 and anzahl(Erfolg) == 0
    # lena's browser is out; marc is still in, still admin, still in his group.
    assert voll["lena"].get("/api/users").status_code == 423
    me = voll["marc"].get("/api/users").json()
    assert me["admin"] is True and me["gruppe"]["id"] == 1
    # The door stays closed: a stranger can't just become the first (admin) name.
    fremd = browser()
    assert fremd.get("/api/zugang").json()["offen"] is False
    rein(fremd)  # with an invitation it works as before
    assert fremd.get("/api/zugang").json()["offen"] is True


def test_only_the_newest_backups_are_kept(voll, monkeypatch):
    monkeypatch.setattr(reset, "BACKUPS_BEHALTEN", 2)
    from datetime import UTC, datetime, timedelta

    zeiten = iter(datetime(2026, 1, 1, tzinfo=UTC) + timedelta(seconds=i) for i in range(5))

    class Uhr(datetime):
        @classmethod
        def now(cls, tz=None):
            return next(zeiten)

    monkeypatch.setattr(reset, "datetime", Uhr)
    for _ in range(4):
        voll["marc"].post("/api/admin/reset", json={"bereiche": ["statistik"], "bestaetigung": "LÖSCHEN"})
    namen = [p.name for p in reset.backups()]
    assert len(namen) == 2 and namen[0].endswith("000003.db")
