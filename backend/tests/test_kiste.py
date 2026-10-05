"""The shared case opening: who may open it, everyone sees the same, and its end."""

import time
from datetime import UTC, datetime, timedelta

import pytest

from app.routers import kiste

from .conftest import login


@pytest.fixture
def gruppe(client, browser):
    """marc (group admin), lena and kim in one group; three suggestions."""
    login(client, "marc", admin=True)
    lena, kim = browser(), browser()
    lena.me = login(lena, "lena")
    kim.me = login(kim, "kim")
    for c, film in ((client, 694), (lena, 694), (lena, 348), (kim, 948)):
        c.post("/api/suggestions", json={"movie_id": film})
    return lena, kim


def test_everyone_gets_the_same_opening(client, gruppe):
    lena, kim = gruppe
    r = client.post("/api/kiste")
    assert r.status_code == 201
    k = r.json()["aktuell"]
    assert k["start"] - r.json()["jetzt"] == 4000  # a countdown, so everyone starts together
    assert {m["id"] for m in k["pool"]} == {694, 348, 948}
    assert k["gewinner"]["id"] in {694, 348, 948}
    for c in (lena, kim):
        seen = c.get("/api/kiste").json()
        assert seen["aktuell"] == k  # same winner, same seed, same strip, same start
        assert abs(seen["jetzt"] - int(time.time() * 1000)) < 5000


def test_only_the_host_or_an_admin_opens_for_everyone(client, gruppe):
    lena, kim = gruppe
    assert lena.get("/api/kiste").json()["darf_oeffnen"] is False
    assert lena.post("/api/kiste").status_code == 403
    # Whoever set the date hosts the evening.
    morgen = (datetime.now(UTC) + timedelta(days=1)).isoformat()
    lena.put("/api/termin", json={"termin": morgen})
    assert lena.get("/api/kiste").json()["darf_oeffnen"] is True
    assert lena.post("/api/kiste").status_code == 201
    assert kim.post("/api/kiste").status_code == 403
    assert client.get("/api/kiste").json()["darf_oeffnen"] is True  # group admin


def test_one_opening_at_a_time(client, gruppe, monkeypatch):
    assert client.post("/api/kiste").status_code == 201
    assert client.post("/api/kiste").status_code == 409
    monkeypatch.setattr(kiste, "LAEUFT", timedelta(seconds=-10))
    r = client.post("/api/kiste")
    assert r.status_code == 201
    # The new one replaces the old film of the evening.
    assert client.get("/api/kiste").json()["aktuell"]["id"] == r.json()["aktuell"]["id"]


def test_an_empty_case_cant_be_opened(client):
    login(client, "marc", admin=True)
    assert client.post("/api/kiste").status_code == 422


def test_the_film_of_the_evening_stays_until_watched(client, gruppe):
    lena, _ = gruppe
    sieger = client.post("/api/kiste").json()["aktuell"]["gewinner"]["id"]
    assert lena.get("/api/kiste").json()["aktuell"]["gewinner"]["id"] == sieger
    lena.post("/api/watched", json={"movie_id": sieger})
    assert lena.get("/api/kiste").json()["aktuell"] is None


def test_host_or_admin_take_it_down(client, gruppe):
    lena, _ = gruppe
    kid = client.post("/api/kiste").json()["aktuell"]["id"]
    assert lena.delete(f"/api/kiste/{kid}").status_code == 403
    assert client.delete(f"/api/kiste/{kid}").status_code == 200
    assert client.get("/api/kiste").json()["aktuell"] is None


def test_other_groups_dont_see_it(client, gruppe, browser):
    client.post("/api/kiste")
    g2 = client.post("/api/admin/gruppen", json={"name": "Zwei"}).json()["id"]
    tom = browser()
    me = login(tom, "tom")
    client.put(f"/api/admin/gruppen/{g2}/mitglieder/{me['id']}", json={})
    client.delete(f"/api/admin/gruppen/1/mitglieder/{me['id']}")
    assert tom.get("/api/kiste").json()["aktuell"] is None


def test_the_feed_shows_it_only_after_the_countdown(client, gruppe, monkeypatch):
    lena, _ = gruppe
    client.post("/api/kiste")
    assert "kiste" not in {e["typ"] for e in lena.get("/api/events").json()["events"]}  # no spoilers
    monkeypatch.setattr(kiste, "COUNTDOWN", timedelta(seconds=-1))
    monkeypatch.setattr(kiste, "LAEUFT", timedelta(seconds=-10))
    client.post("/api/kiste")
    feed = [e for e in lena.get("/api/events").json()["events"] if e["typ"] == "kiste"]
    assert feed and feed[0]["wer"] == "marc"


def test_practice_spins_stay_private(client, gruppe):
    lena, _ = gruppe
    assert lena.post("/api/spin").json()["pick"] is not None
    assert lena.get("/api/kiste").json()["aktuell"] is None


# --- live updates ----------------------------------------------------------------------------


def test_live_counts_writes_per_group(client, gruppe, browser):
    lena, kim = gruppe
    vorher = kim.get("/api/live").json()["stand"]
    assert kim.get("/api/live").json()["stand"] == vorher  # reading changes nothing
    lena.post("/api/wishlist", json={"movie_id": 377})
    nachher = kim.get("/api/live").json()["stand"]
    assert nachher != vorher
    # Another group's writes don't disturb this one (only the server-wide part moves).
    g2 = client.post("/api/admin/gruppen", json={"name": "Zwei"}).json()["id"]
    tom = browser()
    me = login(tom, "tom")
    client.put(f"/api/admin/gruppen/{g2}/mitglieder/{me['id']}", json={})
    client.delete(f"/api/admin/gruppen/1/mitglieder/{me['id']}")
    tom.post("/api/gruppen/aktiv", json={"gruppe_id": g2})
    a = kim.get("/api/live").json()["stand"]
    tom.post("/api/wishlist", json={"movie_id": 377})
    b = kim.get("/api/live").json()["stand"]
    assert a.split(".")[2] == b.split(".")[2]  # group counter unchanged
    assert a.split(".")[1] != b.split(".")[1]  # server counter moved


def test_live_carries_the_shared_opening(client, gruppe):
    lena, _ = gruppe
    client.post("/api/kiste")
    k = lena.get("/api/live").json()["kiste"]
    assert k["aktuell"]["gewinner"]["id"] in {694, 348, 948}
    assert k["darf_oeffnen"] is False


def test_failed_writes_and_heartbeats_dont_count(client, gruppe):
    lena, _ = gruppe
    vorher = lena.get("/api/live").json()["stand"]
    lena.post("/api/kiste")  # 403
    lena.post("/api/kino/da")
    assert lena.get("/api/live").json()["stand"] == vorher
