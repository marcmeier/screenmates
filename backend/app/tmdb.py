"""Thin TMDB client with a graceful no-key fallback.

When no API key is configured every method returns empty results, so the app
still runs on whatever seed data is in the database. All movie dicts are
normalised to the shape the frontend expects (see `movie_to_dict`)."""
from __future__ import annotations

import json
from typing import Any

import httpx

from .config import settings
from .models import Movie

BASE = "https://api.themoviedb.org/3"


def _year(release_date: str) -> int | None:
    if release_date and len(release_date) >= 4 and release_date[:4].isdigit():
        return int(release_date[:4])
    return None


async def _get(path: str, params: dict[str, Any] | None = None) -> dict[str, Any]:
    if not settings.tmdb_enabled:
        return {}
    params = dict(params or {})
    params.setdefault("language", settings.tmdb_language)
    headers = {"Authorization": f"Bearer {settings.tmdb_api_key}"} if settings.tmdb_api_key.startswith("ey") else {}
    if not headers:
        params["api_key"] = settings.tmdb_api_key
    async with httpx.AsyncClient(timeout=15) as client:
        r = await client.get(f"{BASE}{path}", params=params, headers=headers)
        r.raise_for_status()
        return r.json()


def normalise(raw: dict[str, Any], media_type: str | None = None) -> dict[str, Any]:
    mt = media_type or raw.get("media_type") or ("tv" if "name" in raw and "title" not in raw else "movie")
    title = raw.get("title") or raw.get("name") or ""
    original = raw.get("original_title") or raw.get("original_name") or ""
    release = raw.get("release_date") or raw.get("first_air_date") or ""
    genres = raw.get("genres")
    if genres and isinstance(genres[0], dict):
        genres = [g["name"] for g in genres]
    collection = ""
    if isinstance(raw.get("belongs_to_collection"), dict):
        collection = raw["belongs_to_collection"].get("name", "")
    return {
        "id": raw["id"],
        "media_type": mt,
        "title": title,
        "original_title": original,
        "overview": raw.get("overview", ""),
        "release_date": release,
        "year": _year(release),
        "runtime": raw.get("runtime"),
        "poster_path": raw.get("poster_path") or "",
        "backdrop_path": raw.get("backdrop_path") or "",
        "vote_average": raw.get("vote_average", 0.0) or 0.0,
        "vote_count": raw.get("vote_count", 0) or 0,
        "popularity": raw.get("popularity", 0.0) or 0.0,
        "genres": json.dumps(genres or []),
        "collection": collection,
    }


def to_movie(raw: dict[str, Any], media_type: str | None = None, is_canon: bool = False) -> Movie:
    data = normalise(raw, media_type)
    return Movie(is_canon=is_canon, **data)


async def search(query: str, limit: int = 24) -> list[dict[str, Any]]:
    data = await _get("/search/multi", {"query": query, "include_adult": "false"})
    results = [
        normalise(r)
        for r in data.get("results", [])
        if r.get("media_type") in ("movie", "tv")
    ]
    return results[:limit]


async def details(movie_id: int, media_type: str = "movie") -> dict[str, Any] | None:
    data = await _get(f"/{media_type}/{movie_id}")
    return normalise(data, media_type) if data else None


async def credits(movie_id: int, media_type: str = "movie") -> dict[str, Any]:
    return await _get(f"/{media_type}/{movie_id}/credits")


async def similar(movie_id: int, media_type: str = "movie") -> list[dict[str, Any]]:
    data = await _get(f"/{media_type}/{movie_id}/recommendations")
    return [normalise(r, media_type) for r in data.get("results", [])]


async def discover_horror(limit: int = 24, sort: str = "popularity.desc", **flt: Any) -> list[dict[str, Any]]:
    params: dict[str, Any] = {"with_genres": "27", "sort_by": sort, "include_adult": "false"}
    if flt.get("jahr_min"):
        params["primary_release_date.gte"] = f"{flt['jahr_min']}-01-01"
    if flt.get("jahr_max"):
        params["primary_release_date.lte"] = f"{flt['jahr_max']}-12-31"
    if flt.get("note_min"):
        params["vote_average.gte"] = flt["note_min"]
    if flt.get("note_max"):
        params["vote_average.lte"] = flt["note_max"]
    if flt.get("stimmen_min"):
        params["vote_count.gte"] = flt["stimmen_min"]
    if flt.get("dauer_min"):
        params["with_runtime.gte"] = flt["dauer_min"]
    if flt.get("dauer_max"):
        params["with_runtime.lte"] = flt["dauer_max"]
    data = await _get("/discover/movie", params)
    return [normalise(r, "movie") for r in data.get("results", [])][:limit]


async def person_search(query: str) -> list[dict[str, Any]]:
    data = await _get("/search/person", {"query": query})
    return data.get("results", [])


async def person_movies(person_id: int) -> dict[str, Any]:
    return await _get(f"/person/{person_id}/combined_credits")
