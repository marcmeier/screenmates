"""Where to watch, our subscriptions, trailers, and the veto on movie night."""

import httpx
import respx

from .conftest import become_host, login

TMDB = "https://api.themoviedb.org/3"


def prov(pid, name, prio=1):
    return {"provider_id": pid, "provider_name": name, "logo_path": f"/{pid}.png", "display_priority": prio}


# --- Veto ---------------------------------------------------------------------


def test_veto_only_against_suggested_films_and_one_per_person(client):
    login(client, "marc")
    assert client.post("/api/veto", json={"movie_id": 694}).status_code == 422
    client.post("/api/suggestions", json={"movie_id": 694})
    client.post("/api/suggestions", json={"movie_id": 348})
    assert client.post("/api/veto", json={"movie_id": 694}).json() == {"veto": 694}
    assert client.post("/api/veto", json={"movie_id": 348}).json() == {"veto": 348}  # replaces
    s = {m["id"]: m["veto_von"] for m in client.get("/api/suggestions").json()["suggestions"]}
    assert s == {694: [], 348: [1]}
    client.delete("/api/veto")
    assert all(not m["veto_von"] for m in client.get("/api/suggestions").json()["suggestions"])


def test_veto_needs_a_name(client):
    assert client.post("/api/veto", json={"movie_id": 694}).status_code == 401


def test_wheel_skips_vetoed_films(client, browser):
    login(client, "marc")
    lena = browser()
    login(lena, "lena")
    for mid in (694, 348):
        client.post("/api/suggestions", json={"movie_id": mid})
    lena.post("/api/veto", json={"movie_id": 694})
    assert [m["id"] for m in client.get("/api/spin").json()["pool"]] == [348]
    assert all(client.post("/api/spin").json()["pick"]["id"] == 348 for _ in range(5))


def test_when_everything_is_vetoed_the_wheel_stays_empty(client, browser):
    login(client, "marc")
    client.post("/api/wishlist", json={"movie_id": 9552})  # must NOT sneak in as fallback
    client.post("/api/suggestions", json={"movie_id": 694})
    client.post("/api/veto", json={"movie_id": 694})
    assert client.get("/api/spin").json()["pool"] == []
    assert client.post("/api/spin").json()["pick"] is None


def test_vetoes_expire_with_the_film(client, browser):
    login(client, "marc")
    lena = browser()
    login(lena, "lena")
    client.post("/api/suggestions", json={"movie_id": 694})
    client.post("/api/suggestions", json={"movie_id": 348})
    lena.post("/api/veto", json={"movie_id": 694})
    # watched: the veto goes with the suggestion
    client.post("/api/watched", json={"movie_id": 694})
    assert lena.post("/api/veto", json={"movie_id": 348}).status_code == 200  # free again
    # last suggester withdraws: veto against it disappears too
    client.delete("/api/suggestions/348")
    client.post("/api/suggestions", json={"movie_id": 348})
    assert client.get("/api/suggestions").json()["suggestions"][0]["veto_von"] == []


def test_clearing_suggestions_clears_vetoes(client):
    login(client, "marc")
    become_host(client)
    client.post("/api/suggestions", json={"movie_id": 694})
    client.post("/api/veto", json={"movie_id": 694})
    client.delete("/api/suggestions/alle")
    client.post("/api/suggestions", json={"movie_id": 694})
    assert client.get("/api/suggestions").json()["suggestions"][0]["veto_von"] == []


def test_veto_shows_in_activity(client):
    login(client, "marc")
    client.post("/api/suggestions", json={"movie_id": 694})
    client.post("/api/veto", json={"movie_id": 694})
    events = client.get("/api/events").json()["events"]
    assert any(e["typ"] == "veto" and e["wer"] == "marc" and e["film"] == "Shining" for e in events)


# --- Abos ---------------------------------------------------------------------


def test_abos_per_person(client, browser):
    assert client.post("/api/abos", json={"anbieter": [8]}).status_code == 401
    me = login(client, "marc")
    assert client.post("/api/abos", json={"anbieter": [9, 8, 8]}).json() == {"abos": [8, 9]}
    client.post("/api/abos", json={"anbieter": [337]})  # replaces
    users = client.get("/api/users").json()
    assert users["ich"]["abos"] == [337]
    assert {u["id"]: u["abos"] for u in users["users"]} == {me["id"]: [337]}


# --- Where to watch -------------------------------------------------------------


def test_where_to_watch_without_tmdb(client):
    assert client.get("/api/movies/694/anbieter").json() == {"verfuegbar": False}


@respx.mock
def test_where_to_watch_groups_and_puts_our_abos_first(client, tmdb_on, browser):
    route = respx.get(f"{TMDB}/movie/694/watch/providers").mock(
        return_value=httpx.Response(
            200,
            json={
                "results": {
                    "DE": {
                        "link": "https://www.themoviedb.org/movie/694/watch?locale=DE",
                        "flatrate": [prov(9, "Prime Video", 1), prov(384, "HBO Max", 5)],
                        "free": [prov(2285, "JustWatch TV", 2)],
                        "ads": [prov(2285, "JustWatch TV", 2), prov(538, "Plex", 9)],
                        "rent": [prov(2, "Apple TV Store", 3)],
                    },
                    "US": {"flatrate": [prov(8, "Netflix")]},
                }
            },
        )
    )
    marc = login(client, "marc")
    client.post("/api/abos", json={"anbieter": [384]})
    w = client.get("/api/movies/694/anbieter").json()
    assert w["verfuegbar"] and w["quelle"] == "JustWatch" and w["link"].endswith("locale=DE")
    assert [(p["name"], p["bei"]) for p in w["abo"]] == [("HBO Max", [marc["id"]]), ("Prime Video", [])]
    assert [p["name"] for p in w["kostenlos"]] == ["JustWatch TV", "Plex"]  # free + ads, no duplicates
    assert w["leihen"][0]["logo"].endswith("/w92/2.png")
    client.get("/api/movies/694/anbieter")
    assert route.call_count == 1  # cached


@respx.mock
def test_provider_list_keeps_the_ones_we_have(client, tmdb_on):
    results = [
        {"provider_id": 1000 + i, "provider_name": f"P{i}", "logo_path": None, "display_priorities": {"DE": i}}
        for i in range(1, 60)
    ]
    respx.get(f"{TMDB}/watch/providers/movie").mock(return_value=httpx.Response(200, json={"results": results}))
    login(client, "marc")
    client.post("/api/abos", json={"anbieter": [1055]})
    ids = [p["id"] for p in client.get("/api/anbieter", params={"limit": 5}).json()["anbieter"]]
    assert ids == [1001, 1002, 1003, 1004, 1005, 1055]


@respx.mock
def test_discover_by_our_abos(client, tmdb_on):
    route = respx.get(f"{TMDB}/discover/movie").mock(return_value=httpx.Response(200, json={"results": []}))
    login(client, "marc")
    r = client.get("/api/discover", params={"abos": True}).json()
    assert r["results"] == [] and "Abos" in r["hinweis"]
    assert not route.called
    client.post("/api/abos", json={"anbieter": [9, 8]})
    client.get("/api/discover", params={"abos": True})
    params = route.calls.last.request.url.params
    assert params["with_watch_providers"] == "8|9|2100"  # Prime with ads comes with Prime
    assert params["watch_region"] == "DE"
    assert params["with_watch_monetization_types"] == "flatrate"


def test_discover_by_abos_needs_tmdb(client):
    assert "TMDB" in client.get("/api/discover", params={"abos": True}).json()["hinweis"]


# --- Trailer ---------------------------------------------------------------------


def video(key, typ="Trailer", lang="de", official=True, site="YouTube", date="2018-01-01"):
    return {
        "key": key,
        "type": typ,
        "iso_639_1": lang,
        "official": official,
        "site": site,
        "name": key,
        "published_at": date,
    }


@respx.mock
def test_trailer_prefers_german_official_trailers(client, tmdb_on):
    respx.get(f"{TMDB}/movie/694/videos").mock(
        return_value=httpx.Response(
            200,
            json={
                "results": [
                    video("en-teaser", "Teaser", "en"),
                    video("de-fan", lang="de", official=False),
                    video("vimeo", site="Vimeo"),
                    video("de-clip", "Clip"),
                    video("de-offiziell"),
                    video("en-trailer", lang="en"),
                ]
            },
        )
    )
    assert client.get("/api/movies/694/trailer").json()["trailer"] == {
        "key": "de-offiziell",
        "name": "de-offiziell",
        "sprache": "de",
        "typ": "Trailer",
    }


@respx.mock
def test_trailer_falls_back_to_english_and_is_null_without_any(client, tmdb_on):
    respx.get(f"{TMDB}/movie/694/videos").mock(
        return_value=httpx.Response(200, json={"results": [video("en", lang="en"), video("clip", "Clip")]})
    )
    assert client.get("/api/movies/694/trailer").json()["trailer"]["key"] == "en"
    respx.get(f"{TMDB}/movie/348/videos").mock(
        return_value=httpx.Response(200, json={"results": [video("x", "Featurette")]})
    )
    assert client.get("/api/movies/348/trailer").json() == {"trailer": None}


@respx.mock
def test_provider_list_only_offers_real_subscriptions(client, tmdb_on):
    results = [
        {"provider_id": pid, "provider_name": name, "logo_path": None, "display_priorities": {"DE": i}}
        for i, (pid, name) in enumerate(
            [
                (8, "Netflix"),
                (2, "Apple TV Store"),
                (9, "Prime Video"),
                (2100, "Prime Video with Ads"),
                (192, "YouTube"),
            ]
        )
    ]
    respx.get(f"{TMDB}/watch/providers/movie").mock(return_value=httpx.Response(200, json={"results": results}))
    assert [p["name"] for p in client.get("/api/anbieter").json()["anbieter"]] == ["Netflix", "Prime Video"]


@respx.mock
def test_prime_with_ads_counts_as_prime(client, tmdb_on):
    respx.get(f"{TMDB}/movie/694/watch/providers").mock(
        return_value=httpx.Response(200, json={"results": {"DE": {"flatrate": [prov(2100, "Prime Video with Ads")]}}})
    )
    discover = respx.get(f"{TMDB}/discover/movie").mock(return_value=httpx.Response(200, json={"results": []}))
    marc = login(client, "marc")
    client.post("/api/abos", json={"anbieter": [9]})
    assert client.get("/api/movies/694/anbieter").json()["abo"][0]["bei"] == [marc["id"]]
    client.get("/api/discover", params={"abos": True})
    assert discover.calls.last.request.url.params["with_watch_providers"] == "9|2100"
