"""Catalogue helpers shared by several routers."""

from __future__ import annotations

from typing import Any

from fastapi import HTTPException
from sqlmodel import Session as DBSession

from . import tmdb
from .models import Movie


def upsert_movie(db: DBSession, data: dict[str, Any], *, is_canon: bool = False) -> Movie:
    """Insert or refresh a catalogue row from normalised TMDB data (no commit)."""
    m = db.get(Movie, data["id"])
    if m is None:
        m = Movie(**data, is_canon=is_canon)
    else:
        for k, v in data.items():
            # List results lack runtime/collection; don't wipe what details gave us.
            if v in (None, "") and getattr(m, k):
                continue
            setattr(m, k, v)
        m.is_canon = m.is_canon or is_canon
    db.add(m)
    return m


async def ensure_movie(db: DBSession, movie_id: int) -> Movie:
    """Return the catalogue row for a movie, fetching it from TMDB on a miss."""
    m = db.get(Movie, movie_id)
    if m:
        return m
    data = await tmdb.details(movie_id)
    if data is None:
        raise HTTPException(404, "Film nicht gefunden.")
    m = upsert_movie(db, data)
    db.commit()
    db.refresh(m)
    return m
