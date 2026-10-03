"""Turn ORM rows (and normalised TMDB results) into the JSON the frontend uses.

Every movie the API returns goes through `movie_dict`, whether it comes from
the database or straight from TMDB, so both look identical to the client.
"""

from __future__ import annotations

import json
from collections import defaultdict
from datetime import UTC, datetime
from typing import Any

from sqlmodel import Session as DBSession
from sqlmodel import select

from .config import settings
from .models import Movie, Suggestion, User, Watched, Wishlist


def iso(dt: datetime | None) -> str | None:
    """ISO-8601 in UTC. SQLite drops tzinfo, so naive values are UTC by contract."""
    if dt is None:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=UTC)
    return dt.astimezone(UTC).isoformat().replace("+00:00", "Z")


def _img(path: str, size: str) -> str | None:
    return f"{settings.tmdb_image_base}/{size}{path}" if path else None


def movie_dict(m: Movie | dict[str, Any]) -> dict[str, Any]:
    if isinstance(m, dict):
        m = Movie(**m)
    return {
        "id": m.id,
        "title": m.title,
        "original_title": m.original_title,
        "overview": m.overview,
        "release_date": m.release_date,
        "year": m.year,
        "runtime": m.runtime,
        "poster_url": _img(m.poster_path, "w342"),
        "backdrop_url": _img(m.backdrop_path, "w1280"),
        "vote_average": round(m.vote_average or 0, 1),
        "vote_count": m.vote_count,
        "genres": json.loads(m.genres or "[]"),
        "collection": m.collection,
        "is_canon": m.is_canon,
    }


def with_flags(db: DBSession, movies: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Annotate movie dicts with the group's state: watched, wishlisted, suggested by whom.

    One query per flag for the whole page instead of three per movie.
    """
    ids = [m["id"] for m in movies]
    if not ids:
        return movies
    gesehen = set(db.exec(select(Watched.movie_id).where(Watched.movie_id.in_(ids))).all())
    gemerkt = set(db.exec(select(Wishlist.movie_id).where(Wishlist.movie_id.in_(ids))).all())
    vorgeschlagen: dict[int, list[int]] = defaultdict(list)
    for mid, uid in db.exec(select(Suggestion.movie_id, Suggestion.user_id).where(Suggestion.movie_id.in_(ids))).all():
        vorgeschlagen[mid].append(uid)
    for m in movies:
        m["gesehen"] = m["id"] in gesehen
        m["gemerkt"] = m["id"] in gemerkt
        m["vorgeschlagen_von"] = vorgeschlagen.get(m["id"], [])
    return movies


def user_dict(u: User, abos: list[int] | None = None) -> dict[str, Any]:
    return {
        "id": u.id,
        "name": u.name,
        "color": u.color,
        "dabei": u.dabei,
        "hat_schutz": u.schutz_movie_id is not None,
        "created_at": iso(u.created_at),
        "abos": abos or [],  # TMDB provider ids
    }
