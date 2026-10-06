"""The movie night in calendars: a single .ics file, and a personal feed that needs no login."""

from datetime import UTC, datetime, timedelta

from sqlmodel import Session

from app.db import engine
from app.models import Abend, Gruppe

from .conftest import _mitglied, login

TERMIN = (datetime.now(UTC) + timedelta(days=2)).replace(hour=18, minute=30, second=0, microsecond=0)


def zeilen(text: str) -> list[str]:
    assert text.endswith("\r\n")
    return text.split("\r\n")[:-1]


def entfaltet(text: str) -> str:
    return text.replace("\r\n ", "")


def test_one_date_as_a_file(client):
    login(client, "marc")
    assert client.get("/api/termin.ics").status_code == 404
    client.put("/api/termin", json={"termin": TERMIN.isoformat(), "notiz": "bei Marc, Sofa; zweiter Stock"})
    r = client.get("/api/termin.ics")
    assert r.status_code == 200
    assert r.headers["content-type"].startswith("text/calendar")
    assert "attachment" in r.headers["content-disposition"]
    text = entfaltet(r.text)
    assert f"DTSTART:{TERMIN:%Y%m%dT%H%M%SZ}" in text
    assert f"DTEND:{TERMIN + timedelta(hours=3):%Y%m%dT%H%M%SZ}" in text
    assert "LOCATION:bei Marc\\, Sofa\\; zweiter Stock" in text
    assert "SUMMARY:🎬 Filmabend\r\n" in text  # one group: no group name needed
    assert "TRIGGER:-PT2H" in text
    # RFC 5545: no line longer than 75 octets.
    assert all(len(z.encode()) <= 75 for z in zeilen(r.text))


def test_the_description_names_the_films_up_for_the_vote_and_who_is_in(client):
    login(client, "marc")
    client.put("/api/termin", json={"termin": TERMIN.isoformat()})
    client.post("/api/suggestions", json={"movie_id": 694})
    client.post("/api/dabei")
    text = entfaltet(client.get("/api/termin.ics").text)
    assert "Zur Wahl: Shining" in text
    assert "Dabei: marc" in text


def test_the_feed_works_without_a_session_and_dies_with_a_new_link(client, browser):
    login(client, "marc")
    client.put("/api/termin", json={"termin": TERMIN.isoformat()})
    assert client.get("/api/kalender").json() == {"pfad": None}
    pfad = client.post("/api/kalender").json()["pfad"]
    fremd = browser()  # a calendar app: no cookie, no invitation
    assert fremd.get("/api/kalender").status_code == 423  # managing the link needs a session
    r = fremd.get(pfad)
    assert r.status_code == 200
    assert f"DTSTART:{TERMIN:%Y%m%dT%H%M%SZ}" in r.text
    neu = client.post("/api/kalender").json()["pfad"]
    assert neu != pfad
    assert fremd.get(pfad).status_code == 404
    assert fremd.get(neu).status_code == 200
    client.delete("/api/kalender")
    assert fremd.get(neu).status_code == 404
    assert fremd.get("/api/kalender/x.ics").status_code == 404


def test_the_feed_lists_every_group_and_drops_dates_that_are_over(client, browser):
    me = login(client, "marc")
    with Session(engine) as s:
        s.add(Gruppe(id=2, name="Kollegen"))
        s.add(Abend(id=2, termin=TERMIN + timedelta(days=1), notiz="Büro"))
        s.add(Abend(id=1, termin=datetime.now(UTC) - timedelta(days=1)))  # over
        s.commit()
    _mitglied("marc", gruppe=2)
    pfad = client.post("/api/kalender").json()["pfad"]
    text = entfaltet(browser().get(pfad).text)
    assert text.count("BEGIN:VEVENT") == 1
    assert "SUMMARY:🎬 Filmabend · Kollegen" in text
    assert me["name"] == "marc"
