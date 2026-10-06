"""Catalogue and date helpers shared by several modules."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any
from zoneinfo import ZoneInfo

from fastapi import HTTPException
from sqlmodel import Session as DBSession

from . import tmdb
from .models import Movie
from .sprache import aktuell

BERLIN = ZoneInfo("Europe/Berlin")
WOCHENTAGE = ("Montag", "Dienstag", "Mittwoch", "Donnerstag", "Freitag", "Samstag", "Sonntag")
MONATE = (
    "Januar",
    "Februar",
    "März",
    "April",
    "Mai",
    "Juni",
    "Juli",
    "August",
    "September",
    "Oktober",
    "November",
    "Dezember",
)


def utc(dt: datetime) -> datetime:
    """SQLite hands back naive datetimes; they are UTC by contract."""
    return dt.replace(tzinfo=UTC) if dt.tzinfo is None else dt.astimezone(UTC)


WEEKDAYS = ("Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday")
MONTHS = (
    "January",
    "February",
    "March",
    "April",
    "May",
    "June",
    "July",
    "August",
    "September",
    "October",
    "November",
    "December",
)


def termin_text(dt: datetime) -> str:
    """'Freitag, 9. Oktober, 20:00 Uhr' (or 'Friday 9 October, 20:00') in German time, no locale needed."""
    d = utc(dt).astimezone(BERLIN)
    if aktuell() == "en":
        return f"{WEEKDAYS[d.weekday()]} {d.day} {MONTHS[d.month - 1]}, {d:%H:%M}"
    return f"{WOCHENTAGE[d.weekday()]}, {d.day}. {MONATE[d.month - 1]}, {d:%H:%M} Uhr"


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
