"""Groups: independent movie nights on one server, members only, and who manages what."""

import httpx
import pytest
import respx
from sqlmodel import select

from app.models import Gruppe, KinoState, Mitglied
from app.routers import kino

from .conftest import SETUP, _mitglied, login, rein

MTX = "http://mtx:8889"
SDP = "v=0\r\n"


@pytest.fixture
def zwei(client, browser, db):
    """marc (server admin) in both groups; lena only in 1, kim only in 2."""
    login(client, "marc", admin=True)
    g2 = client.post("/api/admin/gruppen", json={"name": "Gruppe 2"}).json()["id"]
    lena, kim = browser(), browser()
    lena.me = login(lena, "lena")
    login(kim, "kim")
    _mitglied("kim", gruppe=g2)
    db.delete(db.exec(select(Mitglied).where(Mitglied.user_id == 3, Mitglied.gruppe_id == 1)).one())
    db.commit()
    kim.me = kim.get("/api/users").json()["ich"]
    client.put(f"/api/admin/gruppen/{g2}/mitglieder/1", json={"admin": True})
    return {"g2": g2, "lena": lena, "kim": kim}


def gesehen(c):
    return [w["movie_id"] for w in c.get("/api/watched").json()["watched"]]


# --- independence ---------------------------------------------------------------------------


def test_groups_have_their_own_movie_night(client, zwei):
    lena, kim, g2 = zwei["lena"], zwei["kim"], zwei["g2"]
    lena.post("/api/watched", json={"movie_id": 694})
    lena.post("/api/wishlist", json={"movie_id": 348})
    lena.post("/api/suggestions", json={"movie_id": 948})
    kim.post("/api/watched", json={"movie_id": 9552})
    kim.post("/api/suggestions", json={"movie_id": 1091})
    kim.post("/api/veto", json={"movie_id": 1091})

    assert gesehen(lena) == [694]
    assert gesehen(kim) == [9552]
    assert [m["id"] for m in kim.get("/api/wishlist").json()["wishlist"]] == []
    assert [m["id"] for m in lena.get("/api/suggestions").json()["suggestions"]] == [948]
    assert [m["id"] for m in kim.get("/api/suggestions").json()["suggestions"]] == [1091]
    assert [m["id"] for m in kim.get("/api/spin").json()["pool"]] == []  # kim vetoed the only one
    assert [m["id"] for m in lena.get("/api/spin").json()["pool"]] == [948]
    # The catalogue marks what *this* group has seen.
    assert lena.get("/api/movies/694").json()["gesehen"] is True
    assert kim.get("/api/movies/694").json()["gesehen"] is False
    assert lena.get("/api/status").json()["watched_count"] == 1

    # marc is in both and switches.
    assert gesehen(client) == [694]
    assert client.post("/api/gruppen/aktiv", json={"gruppe_id": g2}).status_code == 200
    assert gesehen(client) == [9552]
    assert client.get("/api/gruppen").json()["aktiv"] == g2


def test_date_info_attendance_and_feed_per_group(client, zwei):
    lena, kim = zwei["lena"], zwei["kim"]
    from datetime import UTC, datetime, timedelta

    morgen = (datetime.now(UTC) + timedelta(days=1)).replace(microsecond=0).isoformat()
    lena.put("/api/termin", json={"termin": morgen, "notiz": "bei Lena"})
    assert kim.get("/api/termin").json()["termin"] is None
    client.put("/api/info", json={"text": "# Gruppe 1"})
    assert kim.get("/api/info").json()["text"] == ""
    lena.post("/api/dabei")
    assert [u["name"] for u in lena.get("/api/users").json()["users"] if u["dabei"]] == ["lena"]
    assert [u["name"] for u in kim.get("/api/users").json()["users"] if u["dabei"]] == []
    lena.post("/api/watched", json={"movie_id": 694})
    assert {e["typ"] for e in kim.get("/api/events").json()["events"]} <= {"wunsch", "erfolg"}
    assert "termin" in {e["typ"] for e in lena.get("/api/events").json()["events"]}


def test_only_members_see_or_touch_a_group(client, zwei):
    lena, kim = zwei["lena"], zwei["kim"]
    wid = lena.post("/api/watched", json={"movie_id": 694}).json()["id"]
    for r in (
        kim.post(f"/api/watched/{wid}/rating", json={"stars": 5}),
        kim.post(f"/api/watched/{wid}/notes", json={"text": "fremd"}),
        kim.patch(f"/api/watched/{wid}", json={"hidden": True}),
    ):
        assert r.status_code == 404
    # Participants must be members of the group.
    r = lena.post(f"/api/watched/{wid}/dabei", json={"user_ids": [lena.me["id"], kim.me["id"]]})
    assert r.status_code == 422
    # A group you're not in can't be made active.
    assert kim.post("/api/gruppen/aktiv", json={"gruppe_id": 1}).status_code == 403


def test_without_a_group_there_is_nothing_but_a_hint(client, browser, db):
    login(client, "marc", admin=True)
    solo = browser()
    login(solo, "solo")
    for m in db.exec(select(Mitglied).where(Mitglied.user_id == 2)).all():
        db.delete(m)
    db.commit()
    r = solo.get("/api/watched")
    assert r.status_code == 409 and "keiner Gruppe" in r.json()["detail"]
    assert solo.get("/api/users").json()["gruppe"] is None
    assert solo.get("/api/movies/694").status_code == 200  # the catalogue is for everyone


# --- managing groups ----------------------------------------------------------------------------


def test_server_admins_create_and_delete_groups(client, browser, db):
    login(client, "marc", admin=True)
    lena = browser()
    login(lena, "lena")
    assert lena.post("/api/admin/gruppen", json={"name": "x"}).status_code == 403
    g = client.post("/api/admin/gruppen", json={"name": "  Horror-Crew "}).json()
    assert g["name"] == "Horror-Crew" and g["mitglieder"] == []
    assert client.post("/api/admin/gruppen", json={"name": "Horror-Crew"}).status_code == 409
    client.put(f"/api/admin/gruppen/{g['id']}/mitglieder/2", json={})
    lena.post("/api/gruppen/aktiv", json={"gruppe_id": g["id"]})
    lena.post("/api/watched", json={"movie_id": 694})
    assert client.delete(f"/api/admin/gruppen/{g['id']}").status_code == 200
    assert db.get(Gruppe, g["id"]) is None
    # lena falls back to her other group, and the deleted group's evening is gone with it.
    assert lena.get("/api/watched").json()["watched"] == []


def test_group_admins_manage_their_group_only(client, zwei):
    lena, kim, g2 = zwei["lena"], zwei["kim"], zwei["g2"]
    assert kim.put(f"/api/admin/gruppen/{g2}/mitglieder/2", json={}).status_code == 403
    client.put(f"/api/admin/gruppen/{g2}/mitglieder/3", json={"admin": True})  # kim runs group 2
    assert kim.put(f"/api/admin/gruppen/{g2}/mitglieder/2", json={}).status_code == 200  # adds lena
    assert kim.put("/api/admin/gruppen/1/mitglieder/3", json={}).status_code == 403  # not group 1
    assert [g["id"] for g in kim.get("/api/admin/gruppen").json()["gruppen"]] == [g2]
    assert kim.delete(f"/api/admin/gruppen/{g2}").status_code == 403  # deleting: server admins
    assert kim.patch(f"/api/admin/gruppen/{g2}", json={"name": "Kims Kino"}).json()["name"] == "Kims Kino"
    assert kim.delete(f"/api/admin/gruppen/{g2}/mitglieder/2").status_code == 200
    assert lena.post("/api/gruppen/aktiv", json={"gruppe_id": g2}).status_code == 403
    assert lena.get("/api/admin/gruppen").status_code == 403


def test_group_admin_rights_on_the_movie_night(client, zwei):
    lena, kim, g2 = zwei["lena"], zwei["kim"], zwei["g2"]
    assert kim.delete("/api/suggestions/alle").status_code == 403
    assert kim.put("/api/info", json={"text": "x"}).status_code == 403
    client.put(f"/api/admin/gruppen/{g2}/mitglieder/3", json={"admin": True})
    assert kim.delete("/api/suggestions/alle").status_code == 200
    assert kim.put("/api/info", json={"text": "x"}).status_code == 200
    assert kim.get("/api/users").json()["gruppe"]["admin"] is True
    # …but only in their group: lena's group is not kim's to run.
    assert lena.put("/api/info", json={"text": "y"}).status_code == 403


def test_approved_names_join_the_only_group(client, browser, db):
    login(client, "marc", admin=True)
    b1 = browser()
    rein(b1)
    neu = b1.post("/api/users", json={"name": "Neu"}).json()
    client.patch(f"/api/admin/users/{neu['id']}", json={"freigegeben": True})
    assert db.exec(select(Mitglied).where(Mitglied.user_id == neu["id"])).one().gruppe_id == 1
    # With two groups, the name joins the group of the invitation it came with.
    g2 = client.post("/api/admin/gruppen", json={"name": "Zwei"}).json()["id"]
    b2 = browser()
    rein(b2, gruppe=g2)
    zwei = b2.post("/api/users", json={"name": "Zwei"}).json()
    client.patch(f"/api/admin/users/{zwei['id']}", json={"freigegeben": True})
    assert [m.gruppe_id for m in db.exec(select(Mitglied).where(Mitglied.user_id == zwei["id"])).all()] == [g2]


def test_the_first_name_runs_the_first_group(client, db):
    r = client.post("/api/users", json={"name": "Marc", "setup": SETUP}).json()
    m = db.exec(select(Mitglied).where(Mitglied.user_id == r["id"])).one()
    assert (m.gruppe_id, m.ist_admin) == (1, True)


# --- what one group rated stays in that group ------------------------------------------------------


@respx.mock
def test_predictions_taste_and_ai_search_only_use_the_active_groups_evenings(client, browser, db, monkeypatch):
    from app.config import settings

    from .test_prognose_termin_erinnerung import _gesehen, _katalog

    _katalog(db, 12)
    login(client, "marc", admin=True)
    g2 = client.post("/api/admin/gruppen", json={"name": "Horror-Crew"}).json()["id"]
    kim = browser()
    kim_id = login(kim, "kim")["id"]  # in both groups
    tom = browser()
    tom_id = login(tom, "tom")["id"]
    _mitglied("kim", gruppe=g2)
    _mitglied("tom", gruppe=g2)
    client.delete(f"/api/admin/gruppen/1/mitglieder/{tom_id}")  # tom: only the other group
    kim.post("/api/gruppen/aktiv", json={"gruppe_id": g2})
    tom.post("/api/gruppen/aktiv", json={"gruppe_id": g2})
    for i in range(10):  # kim and tom rate plenty, in the other group
        _gesehen(kim, 9000 + i, 5 if i % 2 == 0 else 1)
        _gesehen(tom, 9000 + i, 3)

    r = client.get("/api/movies/9010/prognose").json()  # marc, group 1
    assert r["prognosen"] == []  # kim's stars from the other group don't predict anything here
    assert {z["user_id"]: z["bewertungen"] for z in r["zu_wenig"]} == {
        client.get("/api/users").json()["ich"]["id"]: 0,
        kim_id: 0,
    }
    assert client.get(f"/api/users/{tom_id}/geschmack").status_code == 404
    assert client.get(f"/api/users/{kim_id}/geschmack").json()["vergleiche"] == []
    # The other group's evenings still count there.
    assert kim.get("/api/movies/9010/prognose").json()["prognosen"][0]["user_id"] == kim_id

    # The AI search hides what the active group has seen, not what another group has.
    monkeypatch.setattr(settings, "llm_api_key", "k")
    answer = '[{"titel": "Film 0", "originaltitel": "Film 0", "jahr": 1981, "warum": "x"}]'
    respx.post("https://api.anthropic.com/v1/messages").mock(
        return_value=httpx.Response(200, json={"content": [{"type": "text", "text": answer}]})
    )
    r = client.post("/api/ki-suche", json={"beschreibung": "Slasher", "mit_sammlung": True}).json()
    assert [m["id"] for m in r["results"]] == [9000]
    assert kim.post("/api/ki-suche", json={"beschreibung": "Slasher", "mit_sammlung": True}).json()["results"] == []


# --- one Kino per group --------------------------------------------------------------------------


@respx.mock
def test_every_group_has_its_own_kino(client, zwei, kino_on, db):
    kim, g2 = zwei["kim"], zwei["g2"]
    eins = respx.post(f"{MTX}/kino-1/whip").mock(return_value=httpx.Response(201, content=b"a"))
    zwei_ = respx.post(f"{MTX}/kino-{g2}/whip").mock(return_value=httpx.Response(201, content=b"b"))
    assert client.post("/api/kino/whip", content=SDP).status_code == 201  # marc's active group: 1
    client.post("/api/gruppen/aktiv", json={"gruppe_id": g2})
    key2 = client.get("/api/kino/obs").json()["key"]
    client.post("/api/gruppen/aktiv", json={"gruppe_id": 1})
    key1 = client.get("/api/kino/obs").json()["key"]
    assert key1 != key2
    from fastapi.testclient import TestClient

    from app.main import app

    obs = TestClient(app)
    assert obs.post("/api/kino/whip", content=SDP, headers={"authorization": f"Bearer {key2}"}).status_code == 201
    assert eins.call_count == 1 and zwei_.call_count == 1
    # Secrets differ, and MediaMTX's check knows which is whose.
    db.expire_all()
    s1, s2 = db.get(KinoState, 1).secret, db.get(KinoState, g2).secret
    assert s1 != s2
    ok = {"action": "read", "path": f"kino-{g2}"}
    assert client.post("/api/kino/mtx-auth", json=ok | {"token": s2}).status_code == 200
    assert client.post("/api/kino/mtx-auth", json=ok | {"token": s1}).status_code == 401
    # Audiences are separate.
    kim.post("/api/kino/da")
    assert kino._saele[g2].audience == {3} and kino._saele[1].audience == set()
