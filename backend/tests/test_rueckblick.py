"""The year in review: numbers, films and friendly titles from a group's chronicle."""

from datetime import datetime

import pytest

from app.util import BERLIN

from .conftest import login

JAHR = datetime.now(BERLIN).year - 1


@pytest.fixture
def jahr(client, browser):
    """marc, lena and kim watched three films last year (and one the year before)."""
    marc = login(client, "marc")
    lena, kim = browser(), browser()
    lena.me, kim.me = login(lena, "lena"), login(kim, "kim")
    ids = {"marc": marc["id"], "lena": lena.me["id"], "kim": kim.me["id"]}
    wer = {"marc": client, "lena": lena, "kim": kim}

    def abend(film, tag, sterne):
        w = client.post("/api/watched", json={"movie_id": film, "watched_at": f"{tag}T19:00:00Z"}).json()["id"]
        client.post(f"/api/watched/{w}/dabei", json={"user_ids": [ids[n] for n in sterne]})
        for name, s in sterne.items():
            wer[name].post(f"/api/watched/{w}/rating", json={"stars": s})
        return w

    shining = abend(694, f"{JAHR}-01-09", {"marc": 5, "lena": 5, "kim": 5})
    abend(948, f"{JAHR}-01-16", {"marc": 1, "lena": 5})
    abend(4232, f"{JAHR}-03-06", {"marc": 2, "kim": 2})
    abend(9552, f"{JAHR - 1}-12-30", {"marc": 3})
    note = lena.post(f"/api/watched/{shining}/notes", json={"text": "Here's Johnny!"}).json()["notes"][0]["id"]
    lena.post(f"/api/watched/{shining}/notes", json={"text": "Nochmal!"})
    client.post(f"/api/watched/{shining}/notes", json={"text": "Klassiker"})
    client.post("/api/watched/hearts", json={"note_id": note})
    return ids


def test_years_with_films(client, jahr):
    r = client.get("/api/rueckblick").json()
    assert r["jahre"] == [JAHR, JAHR - 1]
    assert client.get(f"/api/rueckblick/{JAHR - 5}").json() == {"jahr": JAHR - 5, "filme": 0}


def test_the_numbers(client, jahr):
    r = client.get(f"/api/rueckblick/{JAHR}").json()
    assert (r["filme"], r["abende"], r["minuten"], r["leute"]) == (3, 3, 146 + 91 + 111, 3)
    assert r["genres"][0] == {"name": "Horror", "anzahl": 3}
    assert r["monat"] == {"name": "Januar", "nr": 1, "anzahl": 2}
    assert r["serie"] == 2  # two weeks in a row in January
    assert (r["bewertungen"], r["kommentare"], r["herzen"]) == (7, 3, 1)
    assert r["erster"]["movie"]["title"] == "Shining"
    assert r["letzter"]["movie"]["title"] == "Scream"
    assert r["laengster"]["movie"]["title"] == "Shining"
    assert r["kuerzester"]["movie"]["title"] == "Halloween"
    assert r["aeltester"]["movie"]["title"] == "Halloween"


def test_best_worst_disputed_and_unanimous(client, jahr):
    r = client.get(f"/api/rueckblick/{JAHR}").json()
    assert (r["bester"]["movie"]["title"], r["bester"]["sterne"]) == ("Shining", 5)
    assert (r["schlechtester"]["movie"]["title"], r["schlechtester"]["sterne"]) == ("Scream", 2)
    u = r["umstritten"]
    assert (u["movie"]["title"], u["hoch"], u["tief"], u["spanne"]) == ("Halloween", jahr["lena"], jahr["marc"], 4)
    assert r["einig"]["movie"]["title"] == "Shining"


def test_titles_need_enough_data(client, jahr):
    t = client.get(f"/api/rueckblick/{JAHR}").json()["titel"]
    assert t["stammgast"] == {"user_id": jahr["marc"], "wert": 3}
    assert t["streng"] == {"user_id": jahr["marc"], "wert": 2.7}  # the only one with three ratings
    assert t["grosszuegig"] is None
    assert t["plaudertasche"] == {"user_id": jahr["lena"], "wert": 2}
    assert t["herzensbrecher"] == {"user_id": jahr["lena"], "wert": 1}
