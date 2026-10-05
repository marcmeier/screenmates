"""„Wem gefällt's?", the date for the invitation, and "Heute vor einem Jahr"."""

import json
from datetime import UTC, datetime, timedelta

import httpx
import respx

from app.models import Movie
from app.prognose import MIN_BEWERTUNGEN, Film, vorhersage

from .conftest import login

TMDB = "https://api.themoviedb.org/3"


# --- Prognose (unit) ----------------------------------------------------------


def film(i, jahr=2000, note=6.5, kw=(), reihe=""):
    return Film(id=i, titel=f"F{i}", jahr=jahr, note=note, stichworte=frozenset(kw), reihe=reihe)


def test_learns_a_taste_from_keywords():
    # Loves slashers, hates found footage, everything else in between.
    eigene = [(film(i, kw=("slasher", "masked killer")), 5) for i in range(4)]
    eigene += [(film(10 + i, kw=("found footage", "demon")), 1) for i in range(4)]
    eigene += [(film(20 + i, kw=("ghost",)), 3) for i in range(4)]
    slasher = vorhersage(film(99, kw=("slasher", "summer camp")), eigene)
    footage = vorhersage(film(98, kw=("found footage", "witch")), eigene)
    # Four films each are little evidence: clear leaning, but held back from the extremes.
    assert slasher.wert > 3.3 and footage.wert < 2.7 and slasher.wert - footage.wert > 0.9
    assert slasher.weil[1] == 5 and footage.weil[1] == 1  # the reason is a film of that kind


def test_learns_a_taste_from_era_and_quality():
    eigene = [(film(i, jahr=1975 + i, note=7.5), 5) for i in range(5)]
    eigene += [(film(10 + i, jahr=2015 + i, note=5.5), 2) for i in range(5)]
    alt_gut = vorhersage(film(99, jahr=1979, note=7.8), eigene).wert
    neu_schwach = vorhersage(film(98, jahr=2019, note=5.2), eigene).wert
    assert alt_gut - neu_schwach > 2


def test_no_guess_below_the_minimum_and_honest_labels():
    eigene = [(film(i, kw=("slasher",)), 4) for i in range(MIN_BEWERTUNGEN - 1)]
    assert vorhersage(film(99), eigene) is None
    eigene.append((film(50), 2))
    assert vorhersage(film(99), eigene).sicherheit == "erste tendenz"
    eigene += [(film(100 + i), 3) for i in range(25)]
    assert vorhersage(film(99), eigene).sicherheit == "tendenz"


def test_without_any_signal_it_stays_at_the_average():
    eigene = [(film(i), s) for i, s in enumerate([1, 5, 2, 4, 3, 3, 5, 1, 3, 3])]
    p = vorhersage(film(99), eigene)
    assert abs(p.wert - 3.0) < 0.05 and p.weil is None


def test_a_rare_keyword_teaches_nothing():
    """Seen in only one rated film, a keyword is noise; shared by two it counts."""
    neutral = [(film(10 + i), 3) for i in range(8)]
    einmal = vorhersage(film(99, kw=("clown",)), [*neutral, (film(1, kw=("clown",)), 5)])
    zweimal = vorhersage(film(99, kw=("clown",)), [*neutral, (film(1, kw=("clown",)), 5), (film(2, kw=("clown",)), 5)])
    assert einmal.wert < 3.35 < zweimal.wert


# --- Prognose (API) -----------------------------------------------------------


def _katalog(db, n=12):
    """n films: even ids are 80s slashers, odd ids modern found-footage."""
    for i in range(n):
        slasher = i % 2 == 0
        db.add(
            Movie(
                id=9000 + i,
                title=f"Film {i}",
                year=1981 if slasher else 2012,
                vote_average=7.0 if slasher else 5.5,
                keywords=json.dumps(["slasher"] if slasher else ["found footage"]),
                runtime=90,
            )
        )
    db.commit()


def _gesehen(c, mid, sterne):
    w = c.post("/api/watched", json={"movie_id": mid}).json()
    c.post(f"/api/watched/{w['id']}/rating", json={"stars": sterne})


def test_prognose_endpoint(client, browser, db):
    _katalog(db, 12)
    marc = login(client, "marc")
    for i in range(10):
        _gesehen(client, 9000 + i, 5 if i % 2 == 0 else 1)
    lena = browser()
    lena_id = login(lena, "lena")["id"]
    _gesehen(lena, 9000, 4)

    r = client.get("/api/movies/9010/prognose").json()  # an unseen 80s slasher
    assert r["min"] == MIN_BEWERTUNGEN
    (p,) = r["prognosen"]
    assert p["user_id"] == marc["id"] and p["sterne"] >= 4 and p["sicherheit"] == "erste tendenz"
    assert p["weil"]["sterne"] == 5 and p["weil"]["titel"].startswith("Film")
    assert r["zu_wenig"] == [{"user_id": lena_id, "bewertungen": 1}]

    r = client.get("/api/movies/9011/prognose").json()  # found footage
    assert r["prognosen"][0]["sterne"] <= 2

    # Whoever rated the film already gets no guess (their real stars are shown).
    r = client.get("/api/movies/9000/prognose").json()
    assert r["prognosen"] == [] and {z["user_id"] for z in r["zu_wenig"]} == set()


@respx.mock
def test_missing_keywords_are_fetched_once(client, db, tmdb_on):
    _katalog(db, 10)
    db.get(Movie, 9003).keywords = ""  # an old row from before keywords existed
    db.commit()
    route = respx.get(f"{TMDB}/movie/9003").mock(
        return_value=httpx.Response(
            200, json={"id": 9003, "title": "Film 3", "keywords": {"keywords": [{"id": 1, "name": "found footage"}]}}
        )
    )
    respx.get(url__regex=rf"{TMDB}/movie/90(0[0-24-9]|10)$").mock(return_value=httpx.Response(404))
    login(client, "marc")
    _gesehen(client, 9003, 2)
    client.get("/api/movies/9000/prognose")
    client.get("/api/movies/9000/prognose")
    assert route.call_count == 1
    db.expire_all()
    assert json.loads(db.get(Movie, 9003).keywords) == ["found footage"]


# --- Termin -------------------------------------------------------------------


def test_termin_set_read_clear(client, browser):
    anonym = browser()
    morgen = (datetime.now(UTC) + timedelta(days=1)).replace(microsecond=0)
    assert anonym.put("/api/termin", json={"termin": morgen.isoformat()}).status_code == 401
    assert anonym.get("/api/termin").status_code == 401  # only the group sees its date
    marc = login(client, "marc")
    assert client.get("/api/termin").json()["termin"] is None
    lena = browser()
    login(lena, "lena")
    r = client.put("/api/termin", json={"termin": morgen.isoformat(), "notiz": " bei Marc "}).json()
    assert r == {"termin": morgen.isoformat().replace("+00:00", "Z"), "notiz": "bei Marc", "gesetzt_von": marc["id"]}
    assert lena.get("/api/termin").json()["notiz"] == "bei Marc"
    events = client.get("/api/events").json()["events"]
    assert events[0]["typ"] == "termin" and events[0]["wer"] == "marc"
    client.delete("/api/termin")
    assert client.get("/api/termin").json()["termin"] is None


def test_termin_without_offset_means_german_time(client):
    login(client, "marc")
    jahr = datetime.now(UTC).year + 1
    r = client.put("/api/termin", json={"termin": f"{jahr}-01-15T20:00:00"}).json()
    assert r["termin"] == f"{jahr}-01-15T19:00:00Z"  # 20:00 in Berlin (winter) is 19:00 UTC


def test_termin_must_be_upcoming(client):
    login(client, "marc")
    gestern = datetime.now(UTC) - timedelta(days=1)
    assert client.put("/api/termin", json={"termin": gestern.isoformat()}).status_code == 422
    zu_weit = datetime.now(UTC) + timedelta(days=400)
    assert client.put("/api/termin", json={"termin": zu_weit.isoformat()}).status_code == 422


def test_a_past_termin_is_no_longer_shown(client, db):
    from app.models import Abend

    db.add(Abend(id=1, termin=datetime.now(UTC) - timedelta(hours=7), notiz="alt"))
    db.commit()
    login(client, "marc")
    assert client.get("/api/termin").json() == {"termin": None, "notiz": "", "gesetzt_von": None}


# --- Heute vor einem Jahr -----------------------------------------------------


def test_erinnerungen_finds_films_from_earlier_years_around_today(client):
    login(client, "marc")
    for mid, wann in [
        (694, "2025-10-03T19:00:00Z"),  # exactly a year ago
        (348, "2023-10-05T19:00:00Z"),  # three years, two days later
        (1091, "2025-10-09T19:00:00Z"),  # six days off: too far
        (530385, "2026-10-01T19:00:00Z"),  # this year: not a memory
    ]:
        client.post("/api/watched", json={"movie_id": mid, "watched_at": wann})
    r = client.get("/api/erinnerungen", params={"heute": "2026-10-03"}).json()["erinnerungen"]
    assert [(e["eintrag"]["movie_id"], e["jahre"], e["tage"]) for e in r] == [(694, 1, 0), (348, 3, 2)]
    assert r[0]["eintrag"]["movie"]["title"]


def test_erinnerungen_use_german_dates_and_skip_hidden(client, db):
    login(client, "marc")
    # 23:30 UTC on 2 Oct is already 3 Oct in Berlin.
    w = client.post("/api/watched", json={"movie_id": 694, "watched_at": "2025-10-02T23:30:00Z"}).json()
    r = client.get("/api/erinnerungen", params={"heute": "2026-10-06"}).json()["erinnerungen"]
    assert r[0]["tage"] == -3
    client.patch(f"/api/watched/{w['id']}", json={"hidden": True})
    assert client.get("/api/erinnerungen", params={"heute": "2026-10-06"}).json()["erinnerungen"] == []


def test_erinnerungen_on_a_leap_day(client):
    login(client, "marc")
    client.post("/api/watched", json={"movie_id": 694, "watched_at": "2024-02-29T19:00:00Z"})
    r = client.get("/api/erinnerungen", params={"heute": "2025-02-28"}).json()["erinnerungen"]
    assert [(e["jahre"], e["tage"]) for e in r] == [(1, 0)]
