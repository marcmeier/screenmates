"""TMDB client.

One shared `httpx.AsyncClient` (opened/closed by the app lifespan), movies only
— TMDB movie and TV ids live in separate id spaces, and the catalogue keys on
the id, so mixing both would let a series overwrite an unrelated film.

Without an API key every call returns "nothing" so the app runs on seed data.
Upstream failures surface as `TMDBError`, which the app maps to HTTP 502.
"""

from __future__ import annotations

import json
import time
from datetime import date
from typing import Any

import httpx

from .config import settings
from .sprache import tr

BASE = "https://api.themoviedb.org/3"
HORROR = 27

# A movie night needs a feature film: TMDB lists shorts and music videos
# (e.g. "Thriller", 14 min) among films too.
MIN_RUNTIME = 60
# Ranking by rating is meaningless for films with a handful of votes.
MIN_VOTES_FOR_RATING = 200

# TMDB's movie genre ids are stable; list results only carry ids, not names.
# German and English names, as TMDB gives them in details for de-DE and en-US.
GENRES_DE: dict[int, str] = {
    28: "Action",
    12: "Abenteuer",
    16: "Animation",
    35: "Komödie",
    80: "Krimi",
    99: "Dokumentarfilm",
    18: "Drama",
    10751: "Familie",
    14: "Fantasy",
    36: "Historie",
    27: "Horror",
    10402: "Musik",
    9648: "Mystery",
    10749: "Liebesfilm",
    878: "Science Fiction",
    10770: "TV-Film",
    53: "Thriller",
    10752: "Kriegsfilm",
    37: "Western",
}
GENRES_EN: dict[int, str] = {
    28: "Action",
    12: "Adventure",
    16: "Animation",
    35: "Comedy",
    80: "Crime",
    99: "Documentary",
    18: "Drama",
    10751: "Family",
    14: "Fantasy",
    36: "History",
    27: "Horror",
    10402: "Music",
    9648: "Mystery",
    10749: "Romance",
    878: "Science Fiction",
    10770: "TV Movie",
    53: "Thriller",
    10752: "War",
    37: "Western",
}


def genres(sprache: str | None = None) -> dict[int, str]:
    """Genre names in a language ("de"/"en"); by default in the film data's language (TMDB_LANGUAGE)."""
    sprache = sprache or settings.tmdb_language[:2].lower()
    return GENRES_DE if sprache == "de" else GENRES_EN


class TMDBError(Exception):
    """TMDB was unreachable or answered with an unexpected error."""


_client: httpx.AsyncClient | None = None


async def startup() -> None:
    global _client
    _client = httpx.AsyncClient(base_url=BASE, timeout=settings.tmdb_timeout)


async def shutdown() -> None:
    global _client
    if _client is not None:
        await _client.aclose()
        _client = None


async def _get(path: str, params: dict[str, Any] | None = None) -> dict[str, Any] | None:
    """GET a TMDB resource. Returns None when disabled or on 404."""
    if not settings.tmdb_enabled:
        return None
    if _client is None:  # used outside the app lifespan (scripts, tests)
        await startup()
    params = {"language": settings.tmdb_language, **(params or {})}
    headers = {}
    key = settings.tmdb_api_key
    if key.startswith("ey"):  # v4 read access token
        headers["Authorization"] = f"Bearer {key}"
    else:
        params["api_key"] = key
    try:
        r = await _client.get(path, params=params, headers=headers)
    except httpx.HTTPError as e:
        raise TMDBError(tr("TMDB nicht erreichbar: {fehler}", fehler=e.__class__.__name__)) from e
    if r.status_code == 404:
        return None
    if r.status_code >= 400:
        raise TMDBError(tr("TMDB antwortete mit {status}", status=r.status_code))
    return r.json()


class Treffer(list):
    """A page of TMDB results that knows how many there are in total."""

    def __init__(self, items, data: dict[str, Any]):
        super().__init__(items)
        self.gesamt: int = data.get("total_results", len(items))
        self.seiten: int = min(data.get("total_pages", 1), MAX_SEITE)


# TMDB never serves pages beyond 500.
MAX_SEITE = 500


def _year(release_date: str) -> int | None:
    head = (release_date or "")[:4]
    return int(head) if head.isdigit() else None


def normalise(raw: dict[str, Any]) -> dict[str, Any]:
    """Map a TMDB movie (list item or detail) onto `Movie` columns."""
    if raw.get("genres"):
        genre_namen = [g["name"] for g in raw["genres"]]
    else:
        namen = genres()
        genre_namen = [namen[g] for g in raw.get("genre_ids", []) if g in namen]
    collection = raw.get("belongs_to_collection") or {}
    release = raw.get("release_date") or ""
    return {
        "id": raw["id"],
        "media_type": "movie",
        "title": raw.get("title") or raw.get("original_title") or "",
        "original_title": raw.get("original_title") or "",
        "overview": raw.get("overview") or "",
        "release_date": release,
        "year": _year(release),
        "runtime": raw.get("runtime") or None,
        "poster_path": raw.get("poster_path") or "",
        "backdrop_path": raw.get("backdrop_path") or "",
        "vote_average": raw.get("vote_average") or 0.0,
        "vote_count": raw.get("vote_count") or 0,
        "popularity": raw.get("popularity") or 0.0,
        "genres": json.dumps(genre_namen, ensure_ascii=False),
        "collection": collection.get("name", "") if isinstance(collection, dict) else "",
        # only details carry keywords; "" leaves what we already have untouched
        "keywords": json.dumps([k["name"] for k in raw["keywords"].get("keywords", [])], ensure_ascii=False)
        if isinstance(raw.get("keywords"), dict)
        else "",
    }


async def search(query: str, page: int = 1) -> list[dict[str, Any]] | None:
    data = await _get("/search/movie", {"query": query, "include_adult": "false", "page": page})
    return None if data is None else Treffer([normalise(r) for r in data.get("results", [])], data)


async def details(movie_id: int) -> dict[str, Any] | None:
    data = await _get(f"/movie/{movie_id}", {"append_to_response": "keywords"})
    return normalise(data) if data else None


async def credits(movie_id: int) -> dict[str, Any] | None:
    return await _get(f"/movie/{movie_id}/credits")


async def similar(movie_id: int) -> list[dict[str, Any]] | None:
    data = await _get(f"/movie/{movie_id}/recommendations")
    return None if data is None else [normalise(r) for r in data.get("results", [])]


async def discover(
    *,
    sort: str = "popularity.desc",
    page: int = 1,
    include: list[int] | None = None,
    exclude: list[int] | None = None,
    jahr_min: int | None = None,
    jahr_max: int | None = None,
    note_min: float | None = None,
    note_max: float | None = None,
    stimmen_min: int | None = None,
    stimmen_max: int | None = None,
    dauer_min: int | None = None,
    dauer_max: int | None = None,
    abo_anbieter: list[int] | None = None,
    monetarisierung: str | None = None,
    sprachen: list[str] | None = None,
) -> list[dict[str, Any]] | None:
    """Discover films. `include` genres must all apply (TMDB: comma = AND).

    `abo_anbieter` keeps films that are in a subscription with any of these
    providers in the configured region (TMDB/JustWatch availability).
    `monetarisierung` ("flatrate", "free|ads", …) changes how they must be on offer;
    on its own it keeps everything offered that way by anyone.
    """
    params: dict[str, Any] = {
        "with_genres": ",".join(str(g) for g in include or []),
        "sort_by": sort,
        "include_adult": "false",
        "page": page,
    }
    if not params["with_genres"]:
        del params["with_genres"]
    if exclude:
        params["without_genres"] = ",".join(str(g) for g in exclude)
    ranges = {
        "primary_release_date.gte": f"{jahr_min}-01-01" if jahr_min else None,
        # Never films that aren't out yet: they can't be watched on a movie night.
        "primary_release_date.lte": min(f"{jahr_max}-12-31" if jahr_max else "9999", date.today().isoformat()),
        "vote_average.gte": note_min,
        "vote_average.lte": note_max,
        "vote_count.gte": stimmen_min,
        "vote_count.lte": stimmen_max,
        "with_runtime.gte": dauer_min,
        "with_runtime.lte": dauer_max,
    }
    params.update({k: v for k, v in ranges.items() if v is not None})
    if sprachen:
        params["with_original_language"] = "|".join(sprachen)
    if abo_anbieter:
        params["with_watch_providers"] = "|".join(str(p) for p in abo_anbieter)  # | = any of them
    if abo_anbieter or monetarisierung:
        params["watch_region"] = settings.tmdb_region
        params["with_watch_monetization_types"] = monetarisierung or "flatrate"
    data = await _get("/discover/movie", params)
    return None if data is None else Treffer([normalise(r) for r in data.get("results", [])], data)


async def person_search(query: str) -> list[dict[str, Any]] | None:
    data = await _get("/search/person", {"query": query})
    return None if data is None else data.get("results", [])


async def person(person_id: int) -> dict[str, Any] | None:
    return await _get(f"/person/{person_id}")


async def person_movies(person_id: int) -> dict[str, Any] | None:
    return await _get(f"/person/{person_id}/movie_credits")


# --- Where to watch (JustWatch data via TMDB) and trailers --------------------------

_cache: dict[str, tuple[float, Any]] = {}


async def _cached(key: str, ttl: float, load) -> Any:
    """Availability barely changes during an evening; don't ask TMDB on every click."""
    hit = _cache.get(key)
    if hit and hit[0] > time.monotonic():
        return hit[1]
    value = await load()
    if value is not None:
        _cache[key] = (time.monotonic() + ttl, value)
    return value


def _provider(p: dict[str, Any]) -> dict[str, Any]:
    logo = p.get("logo_path")
    return {
        "id": p["provider_id"],
        "name": p["provider_name"],
        "logo": f"{settings.tmdb_image_base}/w92{logo}" if logo else None,
    }


async def watch_providers(movie_id: int) -> dict[str, Any] | None:
    """Where a film streams in the configured region, grouped the way people decide."""

    async def load():
        data = await _get(f"/movie/{movie_id}/watch/providers")
        if data is None:
            return None
        region = data.get("results", {}).get(settings.tmdb_region, {})
        by_priority = lambda key: [  # noqa: E731
            _provider(p) for p in sorted(region.get(key, []), key=lambda p: p.get("display_priority", 999))
        ]
        kostenlos = {p["id"]: p for p in by_priority("free") + by_priority("ads")}
        return {
            "link": region.get("link"),
            "abo": by_priority("flatrate"),
            "kostenlos": list(kostenlos.values()),
            "leihen": by_priority("rent"),
            "kaufen": by_priority("buy"),
        }

    return await _cached(f"wp:{movie_id}", 6 * 3600, load)


async def provider_list() -> list[dict[str, Any]] | None:
    """All streaming services in the region, most relevant first."""

    async def load():
        data = await _get("/watch/providers/movie", {"watch_region": settings.tmdb_region})
        if data is None:
            return None
        region = settings.tmdb_region
        ranked = sorted(data.get("results", []), key=lambda p: p.get("display_priorities", {}).get(region, 999))
        return [_provider(p) for p in ranked]

    return await _cached("providers", 24 * 3600, load)


# Rent/buy shops, not subscriptions: offered per film, but not in "Meine Abos".
STORE_IDS = {
    2,
    3,
    10,
    20,
    35,
    130,
    192,
}  # Apple TV Store, Google Play, Amazon Video, maxdome, Rakuten, Sky Store, YouTube
# Listed by TMDB but no use for a shelf: a free-TV aggregator, anime-only,
# and channels that are bookable inside another service anyway.
KEIN_REGAL = {2285, 283}
KEIN_REGAL_ENDUNG = ("Amazon Channel", "Apple TV Channel", "Roku Premium Channel", "with Ads")  # free = "Kostenlos"


def regal_tauglich(p: dict[str, Any]) -> bool:
    return (
        p["id"] not in STORE_IDS
        and p["id"] not in ABO_VARIANTE
        and p["id"] not in KEIN_REGAL
        and not p["name"].endswith(KEIN_REGAL_ENDUNG)
    )


# Variants of the same subscription (e.g. Prime Video with ads) count as the main one.
ABO_VARIANTE = {2100: 9}


def abo_ids(chosen: list[int]) -> list[int]:
    """Provider ids that a set of chosen subscriptions covers, variants included."""
    covered = set(chosen) | {variant for variant, main in ABO_VARIANTE.items() if main in chosen}
    return sorted(covered)


TRAILER_TYPES = {"Trailer": 0, "Teaser": 1}


async def trailer(movie_id: int) -> dict[str, Any] | None:
    """The best YouTube trailer: German before English, trailer before teaser, official first."""
    lang = settings.tmdb_language.split("-")[0]
    data = await _get(f"/movie/{movie_id}/videos", {"include_video_language": f"{lang},en,null"})
    if not data:
        return None
    candidates = [
        v
        for v in data.get("results", [])
        if v.get("site") == "YouTube" and v.get("type") in TRAILER_TYPES and v.get("key")
    ]
    if not candidates:
        return None
    language_rank = {lang: 0, "en": 1}
    best = min(
        candidates,
        key=lambda v: (
            language_rank.get(v.get("iso_639_1"), 2),
            TRAILER_TYPES[v["type"]],
            not v.get("official", False),
            v.get("published_at") or "",
        ),
    )
    return {"key": best["key"], "name": best.get("name", ""), "sprache": best.get("iso_639_1"), "typ": best["type"]}
