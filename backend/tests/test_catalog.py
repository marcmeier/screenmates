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
