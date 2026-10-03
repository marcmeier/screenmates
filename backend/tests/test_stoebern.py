"""Stöbern: shelves per streaming service and theme, and the grid filters behind them."""

import httpx
import respx

from .conftest import login

TMDB = "https://api.themoviedb.org/3"


def provider(pid, name, prio):
    return {"provider_id": pid, "provider_name": name, "logo_path": f"/{pid}.png", "display_priorities": {"DE": prio}}


PROVIDERS = [
    provider(8, "Netflix", 1),
    provider(9, "Amazon Prime Video", 2),
    provider(2, "Apple TV Store", 3),  # rent/buy shop: no shelf
    provider(2285, "JustWatch TV", 4),  # aggregator: no shelf
    provider(582, "Paramount+ Amazon Channel", 5),  # channel: no shelf
    provider(30, "WOW", 6),
    provider(29, "Sky Go", 7),
    provider(337, "Disney Plus", 8),
]


def film(i):
    return {"id": i, "title": f"Film {i}", "genre_ids": [27], "vote_average": 7, "release_date": "2020-01-01"}


def antwort(request):
    """Discover answers by provider, so every shelf gets its own films."""
    p = request.url.params
    dienst = p.get("with_watch_providers", "")
    if dienst == "8":
        ids = range(100, 114)
    elif dienst in ("9", "9|2100"):
        ids = range(200, 214)
    elif dienst == "30":
        ids = range(300, 314)
    elif dienst == "29":
        ids = range(301, 315)  # Sky Go ≈ WOW: same films
    elif dienst == "337":
        ids = range(400, 402)  # too few for a shelf
    elif p.get("with_watch_monetization_types") == "free|ads":
        ids = range(500, 514)
    elif dienst:  # our subscriptions combined
        ids = range(100, 107)
    else:
        ids = range(600, 614)
    return httpx.Response(200, json={"results": [film(i) for i in ids]})


@respx.mock
def test_shelves_ours_first_services_themes(client, tmdb_on):
    respx.get(f"{TMDB}/watch/providers/movie").mock(return_value=httpx.Response(200, json={"results": PROVIDERS}))
    discover = respx.get(f"{TMDB}/discover/movie").mock(side_effect=antwort)
    login(client, "marc")
    client.post("/api/abos", json={"anbieter": [9]})

    regale = client.get("/api/stoebern").json()["regale"]
    ids = [r["id"] for r in regale]
    # ours first; shops, aggregators and channels have no shelf; Sky Go repeats WOW;
    # Disney Plus has too few films
    assert ids == ["bei-uns", "dienst-9", "dienst-8", "dienst-30", "kostenlos", "neu", "geheimtipps", "klassiker"]
    prime = regale[1]
    assert prime["unser"] is True and prime["anbieter"]["name"] == "Amazon Prime Video"
    assert prime["filter"] == {"anbieter": 9} and len(prime["filme"]) == 14
    assert regale[0]["filter"] == {"beiUns": True}
    assert regale[4]["filter"] == {"kostenlos": True}

    # Each shelf asks TMDB once; the second visit comes from the cache.
    anzahl = discover.call_count
    client.get("/api/stoebern")
    assert discover.call_count == anzahl


@respx.mock
def test_shelf_filters_reach_tmdb(client, tmdb_on):
    route = respx.get(f"{TMDB}/discover/movie").mock(return_value=httpx.Response(200, json={"results": []}))
    client.get("/api/discover", params={"anbieter": "9"})
    p = route.calls.last.request.url.params
    assert (p["with_watch_providers"], p["watch_region"], p["with_watch_monetization_types"]) == (
        "9|2100",
        "DE",
        "flatrate",
    )

    client.get("/api/discover", params={"kostenlos": True})
    p = route.calls.last.request.url.params
    assert "with_watch_providers" not in p and p["with_watch_monetization_types"] == "free|ads"

    client.get("/api/discover", params={"exclude": "16", "stimmen_min": 500, "stimmen_max": 4000})
    p = route.calls.last.request.url.params
    assert (p["without_genres"], p["vote_count.gte"], p["vote_count.lte"]) == ("16", "500", "4000")


def test_without_tmdb_shelves_come_from_the_catalogue(client):
    regale = client.get("/api/stoebern").json()
    assert regale["tmdb"] is False
    assert [r["id"] for r in regale["regale"]][:1] == ["beliebt"]
    assert all(len(r["filme"]) >= 1 for r in regale["regale"])
    klassiker = next(r for r in regale["regale"] if r["id"] == "klassiker")
    assert all(m["year"] <= 1989 for m in klassiker["filme"])
    # Service filters need TMDB: an honest hint instead of an empty grid.
    assert "TMDB" in client.get("/api/discover", params={"anbieter": "8"}).json()["hinweis"]


@respx.mock
def test_provider_picker_for_browsing(client, tmdb_on):
    respx.get(f"{TMDB}/watch/providers/movie").mock(return_value=httpx.Response(200, json={"results": PROVIDERS}))
    login(client, "marc")
    client.post("/api/abos", json={"anbieter": [337]})
    namen = [p["name"] for p in client.get("/api/anbieter", params={"zum_stoebern": True}).json()["anbieter"]]
    assert namen == ["Disney Plus", "Netflix", "Amazon Prime Video", "WOW", "Sky Go"]
    # Settings still offer every real subscription, channels included.
    assert "Paramount+ Amazon Channel" in [p["name"] for p in client.get("/api/anbieter").json()["anbieter"]]
