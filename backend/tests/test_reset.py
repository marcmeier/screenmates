"""The danger zone: admins clear areas of their group in the app; the server-wide rest is on the command line."""

import pytest
from sqlmodel import Session, select

from app import cli
from app.db import engine
from app.models import Abend, Erfolg, Feature, KinoNachricht, Mitglied, Suggestion, User, Watched
from app.routers import reset

from .conftest import _mitglied, login, rein
from .test_umfrage import in_tagen


@pytest.fixture
def voll(client, browser, wuensche):
    """marc (admin) and lena after a busy test phase, and a second group with an evening of its own."""
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
    g2 = client.post("/api/admin/gruppen", json={"name": "Andere"}).json()["id"]
    _mitglied("lena", gruppe=g2)
    lena.post("/api/gruppen/aktiv", json={"gruppe_id": g2})
    lena.post("/api/watched", json={"movie_id": 348})  # the other group's history
    lena.post("/api/suggestions", json={"movie_id": 1091})
    client.me = marc
    return {"marc": client, "lena": lena, "g2": g2}


def anzahl(modell, *bedingungen):
    with Session(engine) as s:
        return len(s.exec(select(modell).where(*bedingungen)).all())


def auftrag(c, *bereiche, wort="LÖSCHEN"):
    return c.post("/api/admin/reset", json={"bereiche": list(bereiche), "bestaetigung": wort})


def test_only_server_admins(voll):
    assert voll["lena"].get("/api/admin/reset").status_code == 403
    assert auftrag(voll["lena"], "chronik").status_code == 403


def test_the_overview_counts_what_would_go_in_the_active_group(voll):
    r = voll["marc"].get("/api/admin/reset").json()
    assert r["gruppe"] == {"id": 1, "name": "Unsere Gruppe"}
    zahlen = {b["key"]: b["anzahl"] for b in r["bereiche"]}
    assert zahlen == {"chronik": 1, "filmabend": 3, "kino": 1}  # filmabend: suggestion, watchlist entry, date
    assert r["bestaetigung"] == "LÖSCHEN"


def test_without_the_word_nothing_happens_and_server_areas_are_not_in_the_app(voll):
    assert auftrag(voll["marc"], "chronik", wort="ja").status_code == 422
    assert anzahl(Watched) == 2
    for bereich in ("quatsch", "wuensche", "erfolge", "neustart"):
        assert auftrag(voll["marc"], bereich, wort="löschen").status_code == 422


def test_clearing_an_area_leaves_the_other_groups_alone(voll):
    r = auftrag(voll["marc"], "chronik", "kino").json()
    assert r["geleert"] == {"chronik": 1, "kino": 1}
    assert anzahl(Watched, Watched.gruppe_id == 1) == 0 and anzahl(KinoNachricht) == 0
    assert anzahl(Watched, Watched.gruppe_id == voll["g2"]) == 1  # the other group's history
    assert anzahl(Feature) == 1 and anzahl(Suggestion) == 2  # untouched


def test_the_evening_is_cleared_but_the_group_stays(voll):
    auftrag(voll["marc"], "filmabend")
    assert anzahl(Suggestion, Suggestion.gruppe_id == 1) == 0
    assert anzahl(Suggestion, Suggestion.gruppe_id == voll["g2"]) == 1
    assert voll["marc"].get("/api/termin").json()["termin"] is None
    assert anzahl(Mitglied, Mitglied.dabei) == 0
    with Session(engine) as s:
        assert s.get(Abend, 1).gastgeber_id is None
    assert voll["marc"].get("/api/users").json()["gruppe"]["id"] == 1


def test_the_command_line_clears_server_areas_only_with_yes(voll, capsys):
    assert cli.main(["reset", "wishes", "awards"]) == 0
    assert "Nothing deleted" in capsys.readouterr().out and anzahl(Feature) == 1
    assert cli.main(["reset", "wishes", "chronicle", "--yes"]) == 0
    assert "Backup: backup-vor-reset-" in capsys.readouterr().out
    assert anzahl(Feature) == 0 and anzahl(Watched) == 0  # every group's history
    assert cli.main(["reset", "quatsch"]) == 2


def test_starting_afresh_on_the_command_line_keeps_one_admin(voll, browser, capsys):
    assert cli.main(["reset", "everything", "--yes"]) == 2  # who stays?
    before = len(reset.backups())
    assert cli.main(["reset", "everything", "--keep", "marc", "--yes"]) == 0
    assert len(reset.backups()) == before + 1
    assert [u.name for u in Session(engine).exec(select(User)).all()] == ["marc"]
    assert anzahl(Watched) == 0 and anzahl(Feature) == 0 and anzahl(Erfolg) == 0
    # lena's browser is out; marc is still in, still admin, still in his group.
    assert voll["lena"].get("/api/users").status_code == 423
    me = voll["marc"].get("/api/users").json()
    assert me["admin"] is True and me["gruppe"]["id"] == 1
    # The door stays closed: a stranger can't just become the first (admin) name.
    fremd = browser()
    assert fremd.get("/api/zugang").json()["offen"] is False
    rein(fremd)
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
        auftrag(voll["marc"], "kino")
    namen = [p.name for p in reset.backups()]
    assert len(namen) == 2 and namen[0].endswith("000003.db")
