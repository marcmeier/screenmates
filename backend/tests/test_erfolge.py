"""Achievements: what unlocks them, and above all, what doesn't (farming)."""

from datetime import UTC, datetime, timedelta

import pytest
from sqlmodel import select

from app import erfolge
from app.models import AppMeta, Erfolg
from app.zeitzone import zone

from .conftest import login


def neu(c):
    return c.post("/api/erfolge/neu").json()


def meine(c):
    neu(c)
    return set(c.get("/api/erfolge").json()["ich"]["freigeschaltet"])


def abends(dt: datetime) -> datetime:
    """Move a time from the small hours to the evening before: run at night, the tests
    would otherwise unlock the secret "Nachteule" (after midnight) on the side."""
    stunde = dt.astimezone(zone()).hour
    return dt - timedelta(hours=stunde + 1) if stunde < 5 else dt


def abend(c, film=694, mit=(), tage=0, angelegt_spaeter=False):
    """A watched entry by c with the given other participants, `tage` days ago."""
    body = {"movie_id": film, "watched_at": abends(datetime.now(UTC) - timedelta(days=tage)).isoformat()}
    w = c.post("/api/watched", json=body).json()
    me = c.get("/api/users").json()["ich"]["id"]
    if mit:
        c.post(f"/api/watched/{w['id']}/dabei", json={"user_ids": [me, *mit]})
    return w["id"]


def bewerten(c, wid, stars=4):
    assert c.post(f"/api/watched/{wid}/rating", json={"stars": stars}).status_code == 200


def kommentar(c, wid, text="Ein wirklich schöner Abend mit Popcorn!"):
    r = c.post(f"/api/watched/{wid}/notes", json={"text": text})
    assert r.status_code == 201
    return r


@pytest.fixture
def lena(browser):
    b = browser()
    b.me = login(b, "lena")
    return b


@pytest.fixture
def kim(browser):
    b = browser()
    b.me = login(b, "kim")
    return b


# --- the basics ----------------------------------------------------------------------


def test_a_confirmed_evening_unlocks_the_first_achievements(client, lena):
    login(client, "marc")
    wid = abend(client, mit=[lena.me["id"]])
    bewerten(client, wid)
    assert "stammgast-1" not in meine(client)  # nobody else confirmed it yet
    bewerten(lena, wid, 5)
    assert {"stammgast-1", "kritiker-1"} <= meine(client)
    assert {"stammgast-1", "kritiker-1"} <= meine(lena)


def test_unlock_popups_come_once_and_carry_points(client, lena):
    login(client, "marc")
    wid = abend(client, mit=[lena.me["id"]])
    bewerten(lena, wid)
    bewerten(client, wid)
    r = neu(client)
    assert {e["key"] for e in r["neu"]} >= {"stammgast-1", "kritiker-1"}
    assert all(e["punkte"] == 10 and e["rueckwirkend"] is False for e in r["neu"])
    assert neu(client)["neu"] == []


def test_levels_titles_and_level_next_to_names(client, lena, browser):
    assert erfolge.level(0) == 1 and erfolge.level(24) == 1 and erfolge.level(25) == 2 and erfolge.level(75) == 3
    assert erfolge.titel(1) == "Popcorn-Neuling" and erfolge.titel(5) == "Cineast"
    login(client, "marc")
    client.post("/api/abos", json={"anbieter": [8]})
    zweit = browser()  # a second device of marc's, connected with his own code
    zweit.post("/api/login", json={"code": client.post("/api/login/code").json()["code"]})
    wid = abend(client, mit=[lena.me["id"]])
    bewerten(lena, wid)
    bewerten(client, wid)
    neu(client)
    ich = client.get("/api/erfolge").json()["ich"]
    assert ich["punkte"] == 40 and ich["level"] == 2 and ich["titel"] == "Popcorn-Neuling"
    assert client.get("/api/users").json()["ich"]["level"] == 2


# --- anti-farming ------------------------------------------------------------------------


def test_a_lonely_or_unconfirmed_evening_counts_nothing(client, lena):
    login(client, "marc")
    for film in (694, 348, 948):
        wid = abend(client, film)  # alone
        bewerten(client, wid)
        kommentar(client, wid)
    wid = abend(client, 9552, mit=[lena.me["id"]])  # lena added, but she never confirmed
    bewerten(client, wid)
    assert meine(client) == set()


def test_confirmation_must_come_from_someone_else_who_was_there(client, lena, kim):
    login(client, "marc")
    wid = abend(client, mit=[lena.me["id"]])
    bewerten(client, wid)
    bewerten(kim, wid)  # kim wasn't there
    assert "stammgast-1" not in meine(client)


def test_backdated_entries_dont_count(client, lena):
    login(client, "marc")
    wid = abend(client, mit=[lena.me["id"]], tage=10)
    bewerten(lena, wid)
    bewerten(client, wid)
    assert meine(client) == set()


def test_one_evening_per_day_and_rerating_earns_nothing(client, lena):
    login(client, "marc")
    for film in (694, 348):  # two entries on the same day
        wid = abend(client, film, mit=[lena.me["id"]])
        bewerten(lena, wid)
    for stars in (1, 2, 3, 4, 5):
        bewerten(client, wid, stars)
    assert erfolge.stand(client_db())[me_id(client)]["stammgast"] == 1
    assert erfolge.stand(client_db())[me_id(client)]["kritiker"] == 1


def test_likes_are_never_rewarded_only_hearts_from_different_people(client, lena, kim, browser):
    login(client, "marc")
    wid = abend(client, mit=[lena.me["id"]])
    bewerten(lena, wid)
    nid = kommentar(client, wid).json()["notes"][0]["id"]
    # Hearting your own note, or one person hearting again and again (it toggles), counts nothing extra.
    for _ in range(5):
        client.post("/api/watched/hearts", json={"note_id": nid})
        lena.post("/api/watched/hearts", json={"note_id": nid})
    assert erfolge.stand(client_db())[me_id(client)]["herz"] == 1  # lena, once
    kim.post("/api/watched/hearts", json={"note_id": nid})
    tom = browser()
    login(tom, "tom")
    tom.post("/api/watched/hearts", json={"note_id": nid})
    assert erfolge.stand(client_db())[me_id(client)]["herz"] == 3
    assert "herz-1" in meine(client)
    # Nothing is ever given for liking others.
    assert not any(k.startswith("herz") for k in meine(lena))


def test_short_comments_and_more_than_three_a_day_dont_count(client, lena):
    login(client, "marc")
    for i, film in enumerate((694, 348, 948, 9552, 1091)):
        wid = abend(client, film, mit=[lena.me["id"]], tage=0)
        bewerten(lena, wid)
        kommentar(client, wid, "super" if i == 0 else "Das war ein richtig guter Filmabend, gerne wieder!")
        kommentar(client, wid, "Und noch ein zweiter Eintrag zum selben Abend, zählt nicht.")
    assert erfolge.stand(client_db())[me_id(client)]["gaestebuch"] == 3


def test_votes_on_your_own_wish_dont_count(client, lena, kim, browser):
    login(client, "marc", admin=True)
    f = lena.post("/api/features", json={"text": "Serien"}).json()
    lena.post(f"/api/features/{f['id']}/vote")
    kim.post(f"/api/features/{f['id']}/vote")
    client.post(f"/api/features/{f['id']}/vote")
    assert erfolge.stand(client_db())[lena.me["id"]]["ideen"] == 0
    tom = browser()
    login(tom, "tom")
    tom.post(f"/api/features/{f['id']}/vote")
    assert erfolge.stand(client_db())[lena.me["id"]]["ideen"] == 1
    # Or an admin marks it done.
    g = kim.post("/api/features", json={"text": "Dunkles Theme"}).json()
    client.patch(f"/api/features/{g['id']}/done", json={"done": True})
    assert erfolge.stand(client_db())[kim.me["id"]]["ideen"] == 1


def test_withdrawn_achievements_stay_withdrawn(client, lena):
    login(client, "marc", admin=True)
    wid = abend(lena, mit=[me_id(client)])
    bewerten(client, wid)
    bewerten(lena, wid)
    assert "stammgast-1" in meine(lena)
    r = client.patch(f"/api/admin/erfolge/{lena.me['id']}/stammgast-1", json={"entzogen": True})
    assert r.status_code == 200
    assert "stammgast-1" not in meine(lena)
    # Giving it back: unlocks again because it's still reached.
    client.patch(f"/api/admin/erfolge/{lena.me['id']}/stammgast-1", json={"entzogen": False})
    assert "stammgast-1" in meine(lena)
    assert lena.patch(f"/api/admin/erfolge/{me_id(client)}/stammgast-1", json={"entzogen": True}).status_code == 403


# --- before the launch, everything counts ------------------------------------------------


def test_history_from_before_the_launch_counts_once_and_retroactively(client, lena, db):
    login(client, "marc")
    for film in (694, 348):
        wid = abend(client, film, tage=30)  # backdated, alone, unconfirmed
        bewerten(client, wid)
    meta = db.get(AppMeta, 1)
    meta.erfolge_seit, meta.erfolge_geprueft = datetime.now(UTC) + timedelta(minutes=1), False
    db.add(meta)
    db.commit()
    r = neu(client)
    assert {"stammgast-1", "kritiker-1"} <= {e["key"] for e in r["neu"]}
    assert all(e["rueckwirkend"] for e in r["neu"])
    # The retroactive flood stays out of the activity feed.
    assert not [e for e in client.get("/api/events").json()["events"] if e["typ"] == "erfolg"]


# --- events: host, kino, hits ----------------------------------------------------------------


def test_host_counts_when_the_evening_took_place(client, lena):
    login(client, "marc")
    morgen = datetime.now(UTC).replace(microsecond=0)
    client.put("/api/termin", json={"termin": morgen.isoformat(), "notiz": ""})
    assert erfolge.stand(client_db())[me_id(client)]["gastgeber"] == 0
    wid = abend(lena, mit=[me_id(client)])
    bewerten(client, wid)
    assert erfolge.stand(client_db())[me_id(client)]["gastgeber"] == 1


def test_a_suggestion_that_gets_watched_is_a_hit(client, lena):
    login(client, "marc")
    lena.post("/api/suggestions", json={"movie_id": 948})
    wid = abend(client, 948, mit=[lena.me["id"]])
    assert erfolge.stand(client_db())[lena.me["id"]]["treffer"] == 0  # not confirmed yet
    bewerten(lena, wid)
    assert erfolge.stand(client_db())[lena.me["id"]]["treffer"] == 1


def test_kino_counts_viewers_after_a_while_and_the_sender_after_two(client, lena, kim, kino_on, db, monkeypatch):
    from app.models import KinoState
    from app.routers import kino

    login(client, "marc", admin=True)
    st = db.get(KinoState, 1) or KinoState(id=1)
    st.gestartet = datetime.now(UTC)
    db.add(st)
    db.commit()
    kino._saele[1].sender = me_id(client)
    monkeypatch.setattr(kino, "MIN_SCHAUEN", 1000)
    lena.post("/api/kino/da")
    assert erfolge.stand(client_db())[lena.me["id"]]["kino"] == 0  # not long enough
    monkeypatch.setattr(kino, "MIN_SCHAUEN", 0)
    for _ in range(3):
        lena.post("/api/kino/da")
    client.post("/api/kino/da")  # the sender watching along doesn't count as audience
    assert erfolge.stand(client_db())[lena.me["id"]]["kino"] == 1
    assert erfolge.stand(client_db())[me_id(client)]["regie"] == 0
    kim.post("/api/kino/da")
    assert erfolge.stand(client_db())[me_id(client)]["regie"] == 1


# --- secrets, showcase, rarity -------------------------------------------------------


def test_secret_achievements_stay_hidden_until_unlocked(client, lena):
    login(client, "marc")
    katalog = {d["key"]: d for d in client.get("/api/erfolge").json()["katalog"]}
    assert katalog["nachteule"]["name"] == "???" and katalog["nachteule"]["emoji"] == "❔"
    assert katalog["stammgast-1"]["name"] == "Erster Abend"


def test_showcase_only_takes_own_unlocked_achievements(client, lena):
    login(client, "marc")
    wid = abend(client, mit=[lena.me["id"]])
    bewerten(lena, wid)
    bewerten(client, wid)
    neu(client)
    assert client.put("/api/erfolge/vitrine", json={"keys": ["stammgast-1", "kritiker-1"]}).status_code == 200
    assert client.put("/api/erfolge/vitrine", json={"keys": ["herz-3"]}).status_code == 422
    assert client.put("/api/erfolge/vitrine", json={"keys": ["a", "b", "c", "d"]}).status_code == 422
    profil = lena.get(f"/api/erfolge/{me_id(client)}").json()
    assert profil["vitrine"] == ["stammgast-1", "kritiker-1"]
    assert {e["key"] for e in profil["freigeschaltet"]} >= {"stammgast-1", "kritiker-1"}
    gruppe = {g["user_id"]: g for g in lena.get("/api/erfolge").json()["gruppe"]}
    assert gruppe[me_id(client)]["vitrine"] == ["stammgast-1", "kritiker-1"]
    # No ranking: everyone's level, but points only for yourself.
    assert "punkte" not in gruppe[me_id(client)]


def test_rarity_is_the_share_of_the_group(client, lena, kim):
    login(client, "marc")
    wid = abend(client, mit=[lena.me["id"]])
    bewerten(lena, wid)
    bewerten(client, wid)
    neu(client)
    katalog = {d["key"]: d for d in kim.get("/api/erfolge").json()["katalog"]}
    assert katalog["stammgast-1"]["selten"] == 67  # 2 of 3


def test_unlocks_appear_in_the_activity_feed(client, lena):
    login(client, "marc")
    wid = abend(client, mit=[lena.me["id"]])
    bewerten(lena, wid)
    bewerten(client, wid)
    neu(client)
    feed = [e for e in client.get("/api/events").json()["events"] if e["typ"] == "erfolg"]
    assert any(e["wer"] == "marc" and e["name"] == "„Erster Abend“" for e in feed)


# --- helpers ------------------------------------------------------------------------------


def client_db():
    from sqlmodel import Session

    from app.db import engine

    return Session(engine)


def me_id(c):
    return c.get("/api/users").json()["ich"]["id"]


def test_erfolg_rows_are_unique(client, lena, db):
    login(client, "marc")
    wid = abend(client, mit=[lena.me["id"]])
    bewerten(lena, wid)
    for _ in range(3):
        erfolge.pruefen(db, sofort=True)
    rows = db.exec(select(Erfolg).where(Erfolg.schluessel == "stammgast-1")).all()
    assert len(rows) == 1  # marc, once (lena confirmed his evening; nobody confirmed hers)
