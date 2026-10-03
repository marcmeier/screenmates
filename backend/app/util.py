"""Shared helpers that would otherwise cause circular imports between routers."""
from __future__ import annotations

from fastapi import HTTPException
from sqlmodel import Session as DBSession

from . import tmdb
from .models import Movie


async def ensure_movie(db: DBSession, movie_id: int, media_type: str = "movie") -> Movie:
    """Return the catalogue row for a movie, fetching it from TMDB on a miss."""
    m = db.get(Movie, movie_id)
    if m:
        return m
    det = await tmdb.details(movie_id, media_type)
    if det is None:
        raise HTTPException(404, "Film nicht im Katalog und TMDB nicht verfügbar")
    m = Movie(**tmdb.normalise(det, media_type))
    db.add(m)
    db.commit()
    db.refresh(m)
    return m
