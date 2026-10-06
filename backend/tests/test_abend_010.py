"""0.10: forecasts and where-to-watch for suggestions, "how was it?", the bell, taste twins, Kino breaks."""

from datetime import UTC, datetime, timedelta

import pytest
from sqlmodel import Session, select

from app import push, tmdb
from app.db import engine
from app.models import Benachrichtigung
from app.prognose import Film, Modell, vorhersage
from app.routers import kino, lists

from .conftest import gesendet, login
from .test_umfrage import empfaenger, geraet, in_tagen

FILME = [348, 377, 694, 948, 1091, 4232, 9552, 138843, 346364, 419430]  # seed catalogue


@pytest.fixture
def paar(client, browser):
    marc = login(client, "marc", admin=True)
    lena = browser()
    lena.me = login(lena, "lena")
    client.me = marc
    return client, lena


def gesehen(c, film, wer, sterne, vor_stunden=48):
    am = (datetime.now(UTC) - timedelta(hours=vor_stunden)).isoformat()
    w = c.post("/api/watched", json={"movie_id": film, "watched_at": am}).json()["id"]
    c.post(f"/api/watched/{w}/dabei", json={"user_ids": [p.me["id"] for p in wer]})
    for p, s in zip(wer, sterne, strict=True):
        p.post(f"/api/watched/{w}/rating", json={"stars": s})
    return w


# --- forecasts -------------------------------------------------------------------------


def test_a_model_learnt_once_predicts_like_before():
    eigene = [(Film(i, jahr=1970 + i, note=6 + i % 3, genres=frozenset({"Horror"})), 1 + i % 5) for i in range(12)]
    ziel = Film(99, jahr=1985, note=7.5, genres=frozenset({"Horror"}))
    assert Modell.lernen(eigene).vorhersage(ziel).wert == pytest.approx(vorhersage(ziel, eigene).wert)
    assert Modell.lernen(eigene[:3]) is None


def test_the_group_forecast_uses_real_stars_and_models(paar):
    marc, lena = paar
    for i, film in enumerate(FILME[:9]):
        gesehen(marc, film, [marc, lena], [1 + i % 5, 5 - i % 5])
    marc.post("/api/suggestions", json={"movie_id": FILME[9]})  # nobody saw it: models guess
    marc.post("/api/suggestions", json={"movie_id": FILME[0]})  # seen: the real stars count
    r = marc.get("/api/suggestions/prognose").json()
    assert r["fuer"] == "gruppe"
    echt = r["prognosen"][str(FILME[0])]
    assert {p["echt"] for p in echt["personen"]} == {True}
    assert echt["genau"] == pytest.approx((1 + 5) / 2)
    geschaetzt = r["prognosen"][str(FILME[9])]
    assert {p["echt"] for p in geschaetzt["personen"]} == {False} and 1 <= geschaetzt["wert"] <= 5
    # With two people in, it's about them.
    marc.post("/api/dabei")
    lena.post("/api/dabei")
    assert marc.get("/api/suggestions/prognose").json()["fuer"] == "dabei"


def test_one_person_is_not_a_group(paar):
    marc, _ = paar
    gesehen(marc, FILME[0], [marc], [4])
    marc.post("/api/suggestions", json={"movie_id": FILME[0]})
    assert marc.get("/api/suggestions/prognose").json()["prognosen"] == {}


# --- where to watch --------------------------------------------------------------------------


def test_our_own_subscription_comes_first():
    daten = {
        "abo": [{"id": 337, "name": "Disney Plus", "logo": None}, {"id": 8, "name": "Netflix", "logo": None}],
        "kostenlos": [{"id": 1, "name": "Arte", "logo": None}],
        "leihen": [],
        "kaufen": [],
    }
    assert lists.bester_weg(daten, {8: [2, 1]}) == {"art": "abo", "name": "Netflix", "logo": None, "bei": [1, 2]}
    assert lists.bester_weg(daten, {})["art"] == "kostenlos"
    nur_leihen = {"abo": [], "kostenlos": [], "leihen": [{"id": 2, "name": "Apple TV", "logo": None}], "kaufen": []}
    assert lists.bester_weg(nur_leihen, {})["art"] == "leihen"
    assert lists.bester_weg(None, {}) is None


def test_where_to_watch_per_suggestion(paar, tmdb_on, monkeypatch):
    marc, lena = paar
    lena.post("/api/abos", json={"anbieter": [8]})
    marc.post("/api/suggestions", json={"movie_id": 694})

    async def anbieter(mid):
        return {"abo": [{"id": 8, "name": "Netflix", "logo": None}], "kostenlos": [], "leihen": [], "kaufen": []}

    monkeypatch.setattr(tmdb, "watch_providers", anbieter)
    r = marc.get("/api/suggestions/anbieter").json()
    assert r["anbieter"]["694"] == {"art": "abo", "name": "Netflix", "logo": None, "bei": [lena.me["id"]]}


def test_without_tmdb_there_is_nothing_to_say(paar):
    assert paar[0].get("/api/suggestions/anbieter").json() == {"verfuegbar": False, "anbieter": {}}


# --- how was it? -------------------------------------------------------------------------


def test_evenings_waiting_for_my_stars(paar):
    marc, lena = paar
    w = gesehen(marc, 694, [marc, lena], [5, 4])
    offen = gesehen(marc, 948, [marc, lena], [5, 4])
    lena.delete(f"/api/watched/rating/{_rating_id(offen, lena)}")
    gesehen(marc, 4232, [marc], [3])  # lena wasn't there
    gesehen(marc, 1091, [marc, lena], [3, 3], vor_stunden=24 * 10)  # too long ago
    assert [e["movie"]["id"] for e in lena.get("/api/watched/zu-bewerten").json()["offen"]] == [948]
    assert marc.get("/api/watched/zu-bewerten").json()["offen"] == []
    assert w


def _rating_id(wid, c):
    entry = next(e for e in c.get("/api/watched").json()["watched"] if e["id"] == wid)
    return next(r["id"] for r in entry["ratings"] if r["user_id"] == c.me["id"])


def test_the_day_after_everyone_without_stars_is_asked_once(paar):
    from app.util import BERLIN

    marc, lena = paar
    geraet(marc, "marc")
    geraet(lena, "lena")
    mittag = datetime.now(BERLIN).replace(hour=12, minute=0, second=0, microsecond=0)
    nacht = mittag.replace(hour=23)
    am = mittag.astimezone(UTC) - timedelta(hours=20)
    w = marc.post("/api/watched", json={"movie_id": 694, "watched_at": am.isoformat()}).json()["id"]
    marc.post(f"/api/watched/{w}/dabei", json={"user_ids": [marc.me["id"], lena.me["id"]]})
    marc.post(f"/api/watched/{w}/rating", json={"stars": 5})
    gesendet.clear()
    with Session(engine) as s:
        assert push.bewertungs_erinnerungen(s, jetzt=nacht.astimezone(UTC)) == 0  # not at night
        assert push.bewertungs_erinnerungen(s, jetzt=mittag.astimezone(UTC)) == 1
        assert empfaenger("bewerten") == {"lena"}  # marc rated already
        assert gesendet[0].daten["titel"] == "⭐ Wie war „Shining“?"
        assert push.bewertungs_erinnerungen(s, jetzt=mittag.astimezone(UTC) + timedelta(hours=1)) == 0  # once


# --- the bell ------------------------------------------------------------------------------------


def test_news_land_in_the_bell_also_without_push(paar):
    marc, lena = paar
    marc.put("/api/termin", json={"termin": in_tagen(3)})
    r = lena.get("/api/glocke").json()
    assert r["ungelesen"] == 1 and r["eintraege"][0]["art"] == "termin" and r["eintraege"][0]["neu"] is True
    assert lena.get("/api/live").json()["glocke"] == 1
    assert marc.get("/api/glocke").json()["ungelesen"] == 0  # not for what you did yourself
    vorher = marc.get("/api/live").json()["stand"]
    lena.post("/api/glocke/gelesen")
    assert lena.get("/api/glocke").json()["ungelesen"] == 0
    assert marc.get("/api/live").json()["stand"] == vorher  # reading doesn't make others reload


def test_the_test_message_and_old_news_stay_out_of_the_bell(paar, monkeypatch):
    marc, _ = paar
    geraet(marc, "marc")
    monkeypatch.setattr(push, "zustellen", lambda z: True)
    marc.post("/api/push/test")
    assert marc.get("/api/glocke").json()["eintraege"] == []
    with Session(engine) as s:
        s.add(
            Benachrichtigung(
                user_id=marc.me["id"], art="termin", titel="alt", am=datetime.now(UTC) - timedelta(days=31)
            )
        )
        s.commit()
        push.glocke(s, [marc.me["id"]], "termin", "neu", "", "/#/abend")
    assert [e["titel"] for e in marc.get("/api/glocke").json()["eintraege"]] == ["neu"]


# --- taste twins ---------------------------------------------------------------------------------


def test_taste_twins_need_three_shared_films(paar, browser):
    marc, lena = paar
    for film, (a, b) in zip(FILME[:3], [(5, 5), (4, 3), (1, 1)], strict=True):
        gesehen(marc, film, [marc, lena], [a, b])
    r = marc.get(f"/api/users/{marc.me['id']}/geschmack").json()
    # one star apart on one of three films: 1/3 star on average; two stars apart would be 0 %
    assert r["vergleiche"] == [{"user_id": lena.me["id"], "prozent": 83, "gemeinsam": 3}]
    # On marc's profile lena sees whom marc is close to, herself included.
    assert lena.get(f"/api/users/{marc.me['id']}/geschmack").json()["vergleiche"][0]["user_id"] == lena.me["id"]
    from app.models import Gruppe

    with Session(engine) as s:
        s.add(Gruppe(id=2, name="Andere"))
        s.commit()
    tom = browser()
    login(tom, "tom")
    from .conftest import _mitglied

    _mitglied("tom", gruppe=2)
    with Session(engine) as s:
        from app.models import Mitglied

        for m in s.exec(select(Mitglied).where(Mitglied.gruppe_id == 1)).all():
            if m.user_id == tom.get("/api/users").json()["ich"]["id"]:
                s.delete(m)
        s.commit()
    assert tom.get(f"/api/users/{marc.me['id']}/geschmack").status_code == 404  # no shared group


# --- Kino: a break, and "just a moment" --------------------------------------------------------------


def test_only_the_host_calls_a_break(paar):
    marc, lena = paar
    assert lena.post("/api/kino/pause", json={"an": True}).status_code == 403
    seit = marc.post("/api/kino/pause", json={"an": True}).json()["pause"]
    assert seit and kino._pause[1] == seit
    assert marc.post("/api/kino/pause", json={"an": True}).json()["pause"] == seit  # stays the same break
    assert marc.post("/api/kino/pause", json={"an": False}).json()["pause"] is None


def test_just_a_moment_reaches_the_others(paar):
    marc, lena = paar
    start = marc.get("/api/kino/chat").json()
    m = lena.post("/api/kino/moment").json()
    neu = marc.get(f"/api/kino/chat?seit={start['letzte']}&rseit={start['rletzte']}").json()["eintraege"]
    assert [(e["typ"], e["user_id"]) for e in neu] == [("moment", lena.me["id"])] and m["typ"] == "moment"
