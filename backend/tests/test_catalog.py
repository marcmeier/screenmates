"""Catalogue endpoints, both on seed data and against a mocked TMDB."""

import httpx
import respx

from app import tmdb

TMDB = "https://api.themoviedb.org/3"


def titles(r):
    return [m["title"] for m in r.json()["results"]]


def test_status_reports_seed(client):
    s = client.get("/api/status").json()
    assert s["movie_count"] == 12
    assert (s["wishlist_count"], s["watched_count"]) == (0, 0)
    assert s["tmdb"] is False


def test_local_search_scans_whole_catalogue(client):
    # Regression: the fallback used to look only at the first `limit` rows.
    assert titles(client.get("/api/search", params={"q": "midsommar", "limit": 1})) == ["Midsommar"]


def test_local_search_matches_original_title(client):
    assert titles(client.get("/api/search", params={"q": "the thing"})) == ["Das Ding aus einer anderen Welt"]


def test_discover_filters_and_sort(client):
    r = client.get("/api/discover", params={"jahr_min": 2015, "sort": "primary_release_date.asc"})
    years = [m["year"] for m in r.json()["results"]]
    assert years == sorted(years)
    assert min(years) >= 2015


def test_discover_genre_include_exclude(client):
    scifi = titles(client.get("/api/discover", params={"include": "878"}))
    assert set(scifi) == {"Alien", "Das Ding aus einer anderen Welt"}
    no_thriller = titles(client.get("/api/discover", params={"exclude": "53"}))
    assert "Shining" not in no_thriller
    assert "Alien" in no_thriller


def test_discover_rejects_unknown_sort(client):
    assert client.get("/api/discover", params={"sort": "drop table"}).status_code == 422


def test_similar_falls_back_to_shared_genres(client):
    similar = titles(client.get("/api/movies/348/aehnliche"))
    assert similar[0] == "Das Ding aus einer anderen Welt"
    assert "Alien" not in similar


def test_unknown_movie_is_404_without_tmdb(client):
    assert client.get("/api/movies/999999").status_code == 404


def test_results_carry_group_flags(client):
    from .conftest import login

    login(client, "marc")
    client.post("/api/wishlist", json={"movie_id": 694})
    shining = next(m for m in client.get("/api/discover").json()["results"] if m["id"] == 694)
    assert shining["gemerkt"] is True
    assert shining["gesehen"] is False


def test_normalise_maps_genre_ids():
    data = tmdb.normalise({"id": 1, "title": "X", "genre_ids": [27, 53, 424242], "release_date": "1999-10-01"})
    assert data["year"] == 1999
    assert data["genres"] == '["Horror", "Thriller"]'


@respx.mock
def test_tmdb_results_have_posters_and_genre_lists(client, tmdb_on):
    respx.get(f"{TMDB}/search/movie").mock(
        return_value=httpx.Response(
            200,
            json={
                "results": [
                    {
                        "id": 10,
                        "title": "Suspiria",
                        "poster_path": "/p.jpg",
                        "genre_ids": [27],
                        "release_date": "1977-02-01",
                    }
                ]
            },
        )
    )
    m = client.get("/api/search", params={"q": "suspiria"}).json()["results"][0]
    assert m["poster_url"].endswith("/w342/p.jpg")
    assert m["genres"] == ["Horror"]
    assert m["year"] == 1977


@respx.mock
def test_tmdb_failures_become_502(client, tmdb_on):
    respx.get(f"{TMDB}/search/movie").mock(return_value=httpx.Response(500))
    assert client.get("/api/search", params={"q": "x"}).status_code == 502
    respx.get(f"{TMDB}/discover/movie").mock(side_effect=httpx.ConnectTimeout("slow"))
    assert client.get("/api/discover").status_code == 502


@respx.mock
def test_detail_completes_list_rows_from_tmdb(client, tmdb_on):
    route = respx.get(f"{TMDB}/movie/694").mock(
        return_value=httpx.Response(
            200, json={"id": 694, "title": "Shining", "runtime": 144, "genres": [{"id": 27, "name": "Horror"}]}
        )
    )
    client.get("/api/movies/694")  # seed row has a runtime, so no fetch
    assert not route.called
    from .conftest import login

    login(client, "marc")
    respx.get(f"{TMDB}/movie/5").mock(
        return_value=httpx.Response(200, json={"id": 5, "title": "Neu", "runtime": 90, "genres": []})
    )
    assert client.post("/api/wishlist", json={"movie_id": 5}).status_code == 201
    assert client.get("/api/movies/5").json()["runtime"] == 90


@respx.mock
def test_discover_defaults_to_feature_films_with_enough_votes(client, tmdb_on):
    route = respx.get(f"{TMDB}/discover/movie").mock(return_value=httpx.Response(200, json={"results": []}))
    client.get("/api/discover")
    params = route.calls.last.request.url.params
    assert params["with_runtime.gte"] == "60"
    assert "vote_count.gte" not in params
    client.get("/api/discover", params={"sort": "vote_average.desc"})
    assert route.calls.last.request.url.params["vote_count.gte"] == "200"
    client.get("/api/discover", params={"sort": "vote_average.desc", "stimmen_min": 0, "dauer_min": 0})
    params = route.calls.last.request.url.params
    assert params["vote_count.gte"] == "0"
    assert params["with_runtime.gte"] == "0"


def test_local_rating_sort_ignores_shorts_and_one_vote_wonders(client, db):
    from app.models import Movie

    db.add(Movie(id=1, title="Thriller", runtime=14, vote_average=9.9, vote_count=800))
    db.add(Movie(id=2, title="Family", runtime=95, vote_average=10.0, vote_count=1))
    db.add(Movie(id=3, title="Ohne Laufzeit", runtime=None, vote_average=9.5, vote_count=900))
    db.commit()
    top = titles(client.get("/api/discover", params={"sort": "vote_average.desc"}))
    assert "Thriller" not in top
    assert "Family" not in top
    assert top[0] == "Ohne Laufzeit"


@respx.mock
def test_people_with_horror_credits_come_first(client, tmdb_on):
    respx.get(f"{TMDB}/search/person").mock(
        return_value=httpx.Response(
            200,
            json={
                "results": [
                    {
                        "id": 1,
                        "name": "Sabrina Carpenter",
                        "known_for_department": "Acting",
                        "known_for": [{"title": "Pop", "genre_ids": [10402]}],
                    },
                    {
                        "id": 2,
                        "name": "John Carpenter",
                        "known_for_department": "Directing",
                        "known_for": [{"title": "Halloween", "genre_ids": [27, 53]}],
                    },
                ]
            },
        )
    )
    people = client.get("/api/personen", params={"q": "carpenter"}).json()["results"]
    assert [(p["name"], p["bereich"], p["horror"]) for p in people] == [
        ("John Carpenter", "Regie", True),
        ("Sabrina Carpenter", "Schauspiel", False),
    ]


@respx.mock
def test_filmography_skips_cameos_and_starts_with_best_known(client, tmdb_on):
    respx.get(f"{TMDB}/person/7").mock(return_value=httpx.Response(200, json={"id": 7, "name": "John Carpenter"}))
    respx.get(f"{TMDB}/person/7/movie_credits").mock(
        return_value=httpx.Response(
            200,
            json={
                "cast": [
                    {"id": 1, "title": "Making-of", "genre_ids": [27], "character": "Self", "vote_count": 5},
                    {
                        "id": 2,
                        "title": "Doku",
                        "genre_ids": [27],
                        "character": "Self (archive footage)",
                        "vote_count": 9,
                    },
                ],
                "crew": [
                    {
                        "id": 3,
                        "title": "Firestarter",
                        "genre_ids": [27],
                        "job": "Original Music Composer",
                        "vote_count": 900,
                    },
                    {"id": 4, "title": "Halloween", "genre_ids": [27], "job": "Director", "vote_count": 6000},
                    {"id": 4, "title": "Halloween", "genre_ids": [27], "job": "Writer", "vote_count": 6000},
                    {"id": 5, "title": "Danke", "genre_ids": [27], "job": "Thanks", "vote_count": 50},
                ],
            },
        )
    )
    r = client.get("/api/personen/7/filme").json()
    assert r["person"]["name"] == "John Carpenter"
    assert [(m["title"], m["rollen"]) for m in r["results"]] == [
        ("Halloween", ["Regie", "Drehbuch"]),
        ("Firestarter", ["Musik"]),
    ]
