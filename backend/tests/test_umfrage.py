"""Finding a date together, and answering for the evening: yes, maybe, no."""

from datetime import UTC, datetime, timedelta

import pytest
from sqlmodel import Session, select

from app import erfolge
from app.db import engine
from app.models import Ereignis

from .conftest import gesendet, login


def in_tagen(n: int, stunde: int = 18) -> str:
    return (datetime.now(UTC) + timedelta(days=n)).replace(hour=stunde, minute=0, second=0, microsecond=0).isoformat()


PUSHDIENST = "https://fcm.googleapis.com/fcm/send/"


def geraet(c, name: str) -> None:
    """This browser allows push notifications (a made-up subscription)."""
    r = c.post(
        "/api/push/abo",
        json={"endpoint": f"{PUSHDIENST}{name}", "keys": {"p256dh": "B" * 87, "auth": "A" * 22}},
    )
    assert r.status_code == 200, r.text


def empfaenger(art: str | None = None) -> set[str]:
    return {z.endpoint.rsplit("/", 1)[1] for z in gesendet if art is None or z.daten["tag"].startswith(art)}


@pytest.fixture
def runde(client, browser):
    """marc (admin), lena and kim in one group, all with a device for push."""
    login(client, "marc", admin=True)
    client.me = client.get("/api/users").json()["ich"]
    leute = {"marc": client}
    for name in ("lena", "kim"):
        c = browser()
        c.me = login(c, name)
        leute[name] = c
    for name, c in leute.items():
        geraet(c, name)
    return leute


def umfrage(c) -> dict:
    return c.get("/api/termin/umfrage").json()


def vorschlagen(c, tage: int, notiz: str = "") -> dict:
    r = c.post("/api/termin/umfrage", json={"termin": in_tagen(tage), "notiz": notiz})
    assert r.status_code == 201, r.text
    return r.json()


def rueckmeldungen(c) -> dict[str, str | None]:
    return {u["name"]: u["rueckmeldung"] for u in c.get("/api/users").json()["users"]}


def test_proposing_counts_as_a_yes_and_tells_the_others(runde):
    lena = runde["lena"]
    v = vorschlagen(lena, 3, "bei Lena")["vorschlaege"][0]
    assert (v["notiz"], v["ja"], v["meine"], v["von"]) == ("bei Lena", 1, "ja", lena.me["id"])
    assert empfaenger("umfrage") == {"marc", "kim"}
    assert gesendet[0].daten["text"].startswith("lena schlägt ")
    assert umfrage(runde["kim"])["vorschlaege"][0]["meine"] is None


def test_answers_can_change_and_be_taken_back(runde):
    lena, kim, marc = runde["lena"], runde["kim"], runde["marc"]
    vid = vorschlagen(lena, 3)["vorschlaege"][0]["id"]
    kim.put(f"/api/termin/umfrage/{vid}/stimme", json={"antwort": "vielleicht"})
    marc.put(f"/api/termin/umfrage/{vid}/stimme", json={"antwort": "nein"})
    v = umfrage(lena)["vorschlaege"][0]
    assert (v["ja"], v["vielleicht"], v["nein"]) == (1, 1, 1)
    assert v["stimmen"] == {str(lena.me["id"]): "ja", str(kim.me["id"]): "vielleicht", str(marc.me["id"]): "nein"}
    kim.put(f"/api/termin/umfrage/{vid}/stimme", json={"antwort": None})
    assert umfrage(lena)["vorschlaege"][0]["vielleicht"] == 0
    assert kim.put(f"/api/termin/umfrage/{vid}/stimme", json={"antwort": "klar"}).status_code == 422


def test_the_favourite_has_the_most_yes(runde):
    lena, kim, marc = runde["lena"], runde["kim"], runde["marc"]
    vorschlagen(lena, 3)
    spaeter = vorschlagen(kim, 5)["vorschlaege"][1]["id"]
    assert umfrage(marc)["favorit"] == umfrage(marc)["vorschlaege"][0]["id"]  # tie: the earlier one
    marc.put(f"/api/termin/umfrage/{spaeter}/stimme", json={"antwort": "ja"})
    assert umfrage(marc)["favorit"] == spaeter
    # Earliest first, whatever the order of proposing.
    tage = [v["termin"] for v in umfrage(marc)["vorschlaege"]]
    assert tage == sorted(tage)


def test_no_past_dates_no_duplicates_and_not_too_many(runde):
    lena = runde["lena"]
    gestern = (datetime.now(UTC) - timedelta(days=1)).isoformat()
    assert lena.post("/api/termin/umfrage", json={"termin": gestern}).status_code == 422
    vorschlagen(lena, 2)
    assert lena.post("/api/termin/umfrage", json={"termin": in_tagen(2)}).status_code == 409
    for tag in range(3, 10):
        vorschlagen(lena, tag)
    assert lena.post("/api/termin/umfrage", json={"termin": in_tagen(20)}).status_code == 409


def test_who_may_pick_and_withdraw(runde):
    lena, kim, marc = runde["lena"], runde["kim"], runde["marc"]
    marc.put("/api/termin", json={"termin": in_tagen(1)})  # marc holds the baton now
    erster = vorschlagen(lena, 3)["vorschlaege"][0]["id"]
    zweiter = vorschlagen(kim, 4)["vorschlaege"][1]["id"]
    assert umfrage(kim)["darf_festlegen"] is False
    assert umfrage(lena)["darf_festlegen"] is True  # started the poll
    assert kim.post(f"/api/termin/umfrage/{erster}/festlegen").status_code == 403
    assert kim.delete(f"/api/termin/umfrage/{erster}").status_code == 403
    assert kim.delete(f"/api/termin/umfrage/{zweiter}").status_code == 200  # own proposal
    assert kim.delete("/api/termin/umfrage").status_code == 403
    assert marc.delete("/api/termin/umfrage").status_code == 200  # host and admin
    assert umfrage(lena)["vorschlaege"] == []


def test_without_a_host_anyone_may_pick(runde):
    lena, kim = runde["lena"], runde["kim"]
    vid = vorschlagen(lena, 3)["vorschlaege"][0]["id"]
    assert umfrage(kim)["darf_festlegen"] is True
    assert kim.post(f"/api/termin/umfrage/{vid}/festlegen").status_code == 200


def test_picking_sets_the_date_carries_answers_over_and_closes_the_poll(runde, db):
    lena, kim, marc = runde["lena"], runde["kim"], runde["marc"]
    vid = vorschlagen(lena, 3, "bei Lena")["vorschlaege"][0]["id"]
    vorschlagen(lena, 4)
    kim.put(f"/api/termin/umfrage/{vid}/stimme", json={"antwort": "vielleicht"})
    marc.put(f"/api/termin/umfrage/{vid}/stimme", json={"antwort": "nein"})
    gesendet.clear()
    r = lena.post(f"/api/termin/umfrage/{vid}/festlegen").json()
    assert r["termin"]["notiz"] == "bei Lena"
    assert r["termin"]["termin"].startswith(in_tagen(3)[:13])
    assert r["umfrage"]["vorschlaege"] == []
    assert rueckmeldungen(marc) == {"marc": "nein", "lena": "ja", "kim": "vielleicht"}
    assert empfaenger("termin") == {"marc", "kim"}
    assert any(e.typ == "umfrage" and e.user_id == lena.me["id"] for e in db.exec(select(Ereignis)).all())
    # Whoever picked holds the baton now (nobody had it).
    assert lena.get("/api/gastgeber").json()["gastgeber"] == lena.me["id"]


def test_open_proposals_show_in_the_feed(runde):
    vorschlagen(runde["lena"], 3)
    feed = runde["kim"].get("/api/events").json()["events"]
    assert any(e["typ"] == "umfrage" and e["wer"] == "lena" for e in feed)


# --- yes, maybe, no ------------------------------------------------------------------


def test_reply_yes_maybe_no_and_take_back(runde):
    kim, marc = runde["kim"], runde["marc"]
    r = kim.put("/api/dabei", json={"antwort": "vielleicht"}).json()
    assert r == {"dabei": False, "rueckmeldung": "vielleicht"}
    assert rueckmeldungen(marc)["kim"] == "vielleicht"
    assert kim.put("/api/dabei", json={"antwort": "ja"}).json() == {"dabei": True, "rueckmeldung": "ja"}
    assert next(u for u in marc.get("/api/users").json()["users"] if u["name"] == "kim")["dabei"] is True
    kim.put("/api/dabei", json={"antwort": "nein"})
    assert rueckmeldungen(marc)["kim"] == "nein"
    kim.put("/api/dabei", json={"antwort": None})
    assert rueckmeldungen(marc)["kim"] is None
    assert kim.put("/api/dabei", json={"antwort": "egal"}).status_code == 422
    kim.put("/api/dabei", json={"antwort": "nein"})
    marc.delete("/api/dabei")  # an admin starts afresh
    assert set(rueckmeldungen(marc).values()) == {None}


def test_a_new_date_after_the_last_evening_starts_with_fresh_replies(runde, db):
    from app.models import Abend

    kim, lena, marc = runde["kim"], runde["lena"], runde["marc"]
    marc.put("/api/termin", json={"termin": in_tagen(2)})
    kim.put("/api/dabei", json={"antwort": "ja"})
    lena.put("/api/dabei", json={"antwort": "nein"})
    marc.put("/api/termin", json={"termin": in_tagen(3)})  # moved: the replies stay
    assert rueckmeldungen(marc) == {"marc": None, "lena": "nein", "kim": "ja"}
    db.expire_all()
    a = db.get(Abend, 1)
    a.termin = datetime.now(UTC) - timedelta(days=1)  # the evening is over
    db.add(a)
    db.commit()
    marc.put("/api/termin", json={"termin": in_tagen(7)})
    assert set(rueckmeldungen(marc).values()) == {None}


def test_a_kept_promise_counts_once_the_evening_took_place(runde):
    lena, kim, marc = runde["lena"], runde["kim"], runde["marc"]
    kim.put("/api/dabei", json={"antwort": "ja"})  # no date yet: nothing to keep
    marc.put("/api/termin", json={"termin": datetime.now(UTC).replace(microsecond=0).isoformat()})
    kim.put("/api/dabei", json={"antwort": "nein"})
    kim.put("/api/dabei", json={"antwort": "ja"})
    kim.put("/api/dabei", json={"antwort": "ja"})  # saying it twice is still one promise
    lena.put("/api/dabei", json={"antwort": "ja"})  # lena doesn't come
    with Session(engine) as s:
        assert len([e for e in s.exec(select(Ereignis).where(Ereignis.typ == "zusage")).all()]) == 2
    w = marc.post("/api/watched", json={"movie_id": 694}).json()["id"]
    marc.post(f"/api/watched/{w}/dabei", json={"user_ids": [marc.me["id"], kim.me["id"]]})
    kim.post(f"/api/watched/{w}/rating", json={"stars": 4})
    marc.post(f"/api/watched/{w}/rating", json={"stars": 5})
    with Session(engine) as s:
        stand = erfolge.stand(s)
    assert stand[kim.me["id"]]["zusage"] == 1
    assert stand[lena.me["id"]]["zusage"] == 0
