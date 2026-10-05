"""The host's baton: picked up with a date, handed over, taken over, voted on."""

from datetime import UTC, datetime, timedelta

import pytest

from app.routers import gastgeber

from .conftest import login

MORGEN = (datetime.now(UTC) + timedelta(days=1)).isoformat()


@pytest.fixture
def runde(client, browser):
    """marc (group admin), lena, kim and tom in one group; lena sets the date and hosts."""
    login(client, "marc", admin=True)
    leute = {}
    for name in ("lena", "kim", "tom"):
        c = browser()
        c.me = login(c, name)
        leute[name] = c
    leute["lena"].put("/api/termin", json={"termin": MORGEN})
    return leute


def zustand(c):
    return c.get("/api/gastgeber").json()


def da(*cs):
    """These apps are open (as the live poll would report)."""
    for c in cs:
        c.get("/api/live")


def test_setting_the_date_picks_up_the_baton(runde):
    lena, kim = runde["lena"], runde["kim"]
    assert zustand(kim)["gastgeber"] == lena.me["id"]
    # Moving the date doesn't steal it.
    kim.put("/api/termin", json={"termin": MORGEN})
    assert zustand(kim)["gastgeber"] == lena.me["id"]
    assert zustand(lena)["darf_moderieren"] is True
    assert zustand(kim)["darf_moderieren"] is False


def test_handing_over_needs_a_yes(runde):
    lena, kim, tom = runde["lena"], runde["kim"], runde["tom"]
    assert kim.post("/api/gastgeber/uebergeben", json={"an": tom.me["id"]}).status_code == 403
    w = lena.post("/api/gastgeber/uebergeben", json={"an": kim.me["id"]}).json()["wechsel"]
    assert (w["art"], w["an"]) == ("uebergabe", kim.me["id"])
    assert tom.post(f"/api/gastgeber/wechsel/{w['id']}", json={"ja": True}).status_code == 403
    kim.post(f"/api/gastgeber/wechsel/{w['id']}", json={"ja": True})
    assert zustand(tom)["gastgeber"] == kim.me["id"]
    # The new host runs the evening, the old one doesn't any more.
    assert kim.get("/api/kiste").json()["darf_oeffnen"] is True
    assert lena.get("/api/kiste").json()["darf_oeffnen"] is False


def test_a_declined_or_unanswered_handover_changes_nothing(runde, monkeypatch):
    lena, kim = runde["lena"], runde["kim"]
    w = lena.post("/api/gastgeber/uebergeben", json={"an": kim.me["id"]}).json()["wechsel"]
    kim.post(f"/api/gastgeber/wechsel/{w['id']}", json={"ja": False})
    assert zustand(kim)["gastgeber"] == lena.me["id"]
    monkeypatch.setattr(gastgeber, "UEBERGABE_FRIST", timedelta(seconds=-1))
    lena.post("/api/gastgeber/uebergeben", json={"an": kim.me["id"]})
    s = zustand(kim)  # expired on the next look
    assert (s["gastgeber"], s["wechsel"]) == (lena.me["id"], None)


def test_an_absent_host_leaves_the_baton_to_whoever_takes_it(runde):
    lena, kim = runde["lena"], runde["kim"]
    assert zustand(kim)["uebernehmen"] == "sofort"  # lena's app isn't open
    kim.post("/api/gastgeber/uebernehmen")
    assert zustand(lena)["gastgeber"] == kim.me["id"]
    feed = [e for e in kim.get("/api/events").json()["events"] if e["typ"] == "gastgeber"]
    assert feed[0]["art"] == "uebernahme" and feed[0]["wer"] == "kim"


def test_a_present_host_means_a_vote_and_their_yes_decides(runde):
    lena, kim, tom = runde["lena"], runde["kim"], runde["tom"]
    da(lena, tom)
    assert zustand(kim)["uebernehmen"] == "abstimmung"
    w = kim.post("/api/gastgeber/uebernehmen").json()["wechsel"]
    assert w["art"] == "abstimmung"
    assert kim.post(f"/api/gastgeber/wechsel/{w['id']}", json={"ja": True}).status_code == 403  # not for oneself
    assert zustand(tom)["wechsel"]["darf_stimmen"] is True
    lena.post(f"/api/gastgeber/wechsel/{w['id']}", json={"ja": True})
    assert zustand(tom)["gastgeber"] == kim.me["id"]


def test_the_majority_decides_and_the_host_counts_double(runde, client):
    lena, kim, tom = runde["lena"], runde["kim"], runde["tom"]
    da(lena, tom, client)
    w = kim.post("/api/gastgeber/uebernehmen").json()["wechsel"]
    tom.post(f"/api/gastgeber/wechsel/{w['id']}", json={"ja": True})
    client.post(f"/api/gastgeber/wechsel/{w['id']}", json={"ja": True})  # 2:0, but lena counts double
    s = lena.post(f"/api/gastgeber/wechsel/{w['id']}", json={"ja": False}).json()  # 2:2, everyone voted
    assert s["gastgeber"] == lena.me["id"]  # a tie isn't a majority
    # Who lost waits a while.
    assert kim.post("/api/gastgeber/uebernehmen").status_code == 429


def test_silence_is_consent(runde, monkeypatch):
    lena, kim = runde["lena"], runde["kim"]
    da(lena)
    monkeypatch.setattr(gastgeber, "ABSTIMMUNG_FRIST", timedelta(seconds=-1))
    kim.post("/api/gastgeber/uebernehmen")
    assert zustand(kim)["gastgeber"] == kim.me["id"]


def test_withdrawing_and_admins(runde, client):
    lena, kim = runde["lena"], runde["kim"]
    da(lena)
    w = kim.post("/api/gastgeber/uebernehmen").json()["wechsel"]
    assert lena.delete(f"/api/gastgeber/wechsel/{w['id']}").status_code == 403
    kim.delete(f"/api/gastgeber/wechsel/{w['id']}")
    assert zustand(kim)["wechsel"] is None
    # Admins take it without asking.
    assert zustand(client)["uebernehmen"] == "sofort"
    client.post("/api/gastgeber/uebernehmen")
    assert zustand(kim)["gastgeber"] == 1


def test_the_host_runs_the_kino_with_a_personal_obs_key(runde, client, kino_on):
    lena, kim = runde["lena"], runde["kim"]
    assert kim.get("/api/kino/obs").status_code == 403
    obs = lena.get("/api/kino/obs").json()
    assert obs["persoenlich"] is True
    assert obs["key"] != client.get("/api/kino/obs").json()["key"]  # not the group's key
    assert lena.post("/api/kino/programm", json={"titel": "Heute"}).status_code == 200
    kim.post("/api/gastgeber/uebernehmen")  # lena is away
    assert lena.post("/api/kino/programm", json={"titel": "x"}).status_code == 403
    # The old personal key no longer opens the Kino.
    from fastapi import HTTPException
    from sqlmodel import Session
    from starlette.requests import Request

    from app.db import engine
    from app.routers.kino import _sender_gruppe

    req = Request({"type": "http", "headers": [(b"authorization", f"Bearer {obs['key']}".encode())]})
    with Session(engine) as db, pytest.raises(HTTPException):
        _sender_gruppe(req, db, None, None, False)


def test_a_vote_ends_as_soon_as_it_is_decided(runde, client):
    lena, kim, tom = runde["lena"], runde["kim"], runde["tom"]
    da(lena, tom, client)
    w = kim.post("/api/gastgeber/uebernehmen").json()["wechsel"]
    tom.post(f"/api/gastgeber/wechsel/{w['id']}", json={"ja": True})
    s = lena.post(f"/api/gastgeber/wechsel/{w['id']}", json={"ja": False}).json()
    # 1:2 with only marc (one vote) missing: it cannot pass any more.
    assert (s["gastgeber"], s["wechsel"]) == (lena.me["id"], None)
