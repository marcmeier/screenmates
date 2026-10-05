"""Around the movie night: who'll like a film, the next date, and memories."""

from __future__ import annotations

import asyncio
from collections import defaultdict
from datetime import UTC, date, datetime, timedelta
from zoneinfo import ZoneInfo

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlmodel import Session as DBSession
from sqlmodel import col, select

from .. import erfolge, tmdb
from ..config import settings
from ..db import get_session
from ..gruppen import aktive_gruppe
from ..models import Abend, Movie, User, Watched, WatchedRating, now
from ..prognose import MIN_BEWERTUNGEN, Film, vorhersage
from ..serialize import iso
from ..session import require_user
from ..util import ensure_movie, upsert_movie
from . import gastgeber
from .watched import _payload

router = APIRouter(prefix="/api", tags=["abend"])

BERLIN = ZoneInfo("Europe/Berlin")
# Rated films without keywords are completed from TMDB, at most this many per request.
STICHWORTE_PRO_ANFRAGE = 30


def _utc(dt: datetime | None) -> datetime | None:
    """SQLite hands back naive datetimes; they are UTC by contract."""
    if dt is None:
        return None
    return dt.replace(tzinfo=UTC) if dt.tzinfo is None else dt.astimezone(UTC)


# --- Wem gefällt's? -----------------------------------------------------------


async def _stichworte(db: DBSession, filme: list[Movie]) -> None:
    """Fill in TMDB keywords for films that lack them (best effort, bounded)."""
    fehlen = [m.id for m in filme if m.keywords == ""][:STICHWORTE_PRO_ANFRAGE]
    if not fehlen or not settings.tmdb_enabled:
        return
    gate = asyncio.Semaphore(5)

    async def laden(mid: int):
        async with gate:
            try:
                return await tmdb.details(mid)
            except tmdb.TMDBError:
                return None

    for data in await asyncio.gather(*(laden(mid) for mid in fehlen)):
        if data is not None:
            upsert_movie(db, data)
    db.commit()


@router.get("/movies/{movie_id}/prognose")
async def prognose(movie_id: int, db: DBSession = Depends(get_session)):
    ziel = await ensure_movie(db, movie_id)
    rows = db.exec(
        select(WatchedRating.user_id, Watched.movie_id, WatchedRating.stars)
        .join(Watched, col(Watched.id) == WatchedRating.watched_id)
        .where(col(Watched.hidden).is_(False))
        .order_by(Watched.watched_at)
    ).all()
    sterne: dict[int, dict[int, list[int]]] = defaultdict(lambda: defaultdict(list))
    for uid, mid, s in rows:
        sterne[uid][mid].append(s)  # dicts keep insertion order: oldest film first

    filme = {m.id: m for m in db.exec(select(Movie).where(col(Movie.id).in_({mid for _, mid, _ in rows}))).all()}
    await _stichworte(db, [ziel, *filme.values()])
    zf = Film.aus(ziel)
    film = {mid: Film.aus(m) for mid, m in filme.items()}

    prognosen, zu_wenig = [], []
    for u in db.exec(select(User).order_by(User.name)).all():
        meine = sterne.get(u.id, {})
        if movie_id in meine:
            continue  # rated it already: the real stars are shown, no guess needed
        # Seen twice, rated twice: the average counts.
        p = vorhersage(zf, [(film[mid], sum(v) / len(v)) for mid, v in meine.items() if mid in film])
        if p is None:
            zu_wenig.append({"user_id": u.id, "bewertungen": len(meine)})
            continue
        prognosen.append(
            {
                "user_id": u.id,
                "sterne": round(p.wert * 2) / 2,
                "wert": round(p.wert, 2),
                "sicherheit": p.sicherheit,
                "weil": {"movie_id": p.weil[0].id, "titel": p.weil[0].titel, "sterne": p.weil[1]} if p.weil else None,
            }
        )
    prognosen.sort(key=lambda x: -x["wert"])
    return {"prognosen": prognosen, "zu_wenig": zu_wenig, "min": MIN_BEWERTUNGEN}


# --- Termin (for the invitation) ---------------------------------------------


class TerminSetzen(BaseModel):
    termin: datetime
    notiz: str = Field("", max_length=80)


def _abend(db: DBSession, gid: int) -> Abend:
    return db.get(Abend, gid) or Abend(id=gid)


def _termin_dict(a: Abend) -> dict:
    termin = _utc(a.termin)
    # A date that is long over doesn't belong on the next invitation.
    if termin is None or termin < datetime.now(UTC) - timedelta(hours=6):
        return {"termin": None, "notiz": "", "gesetzt_von": None}
    return {"termin": iso(termin), "notiz": a.notiz, "gesetzt_von": a.gesetzt_von}


@router.get("/termin")
def get_termin(gid: int = Depends(aktive_gruppe), db: DBSession = Depends(get_session)):
    return _termin_dict(_abend(db, gid))


@router.put("/termin")
def set_termin(
    body: TerminSetzen,
    user: User = Depends(require_user),
    gid: int = Depends(aktive_gruppe),
    db: DBSession = Depends(get_session),
):
    termin = body.termin if body.termin.tzinfo else body.termin.replace(tzinfo=BERLIN)
    jetzt = datetime.now(UTC)
    if not jetzt - timedelta(hours=6) <= termin <= jetzt + timedelta(days=366):
        raise HTTPException(422, "Der Termin muss in der Zukunft liegen (höchstens ein Jahr).")
    a = _abend(db, gid)
    gastgeber.termin_gesetzt(db, a, user, a.termin)
    a.termin, a.notiz, a.gesetzt_von, a.gesetzt_am = termin.astimezone(UTC), body.notiz.strip(), user.id, now()
    db.add(a)
    erfolge.protokoll(db, "termin", user.id, termin.astimezone(BERLIN).date().isoformat())
    db.commit()
    return _termin_dict(a)


@router.delete("/termin")
def clear_termin(gid: int = Depends(aktive_gruppe), db: DBSession = Depends(get_session)):
    a = _abend(db, gid)
    a.termin, a.notiz, a.gesetzt_am = None, "", None
    db.add(a)
    db.commit()
    return _termin_dict(a)


# --- Heute vor einem Jahr -----------------------------------------------------

FENSTER_TAGE = 3


def _gleicher_tag(d: date, jahr: int) -> date:
    try:
        return d.replace(year=jahr)
    except ValueError:  # 29 February in a normal year
        return d.replace(year=jahr, day=28)


@router.get("/erinnerungen")
def erinnerungen(
    heute: date | None = Query(None), gid: int = Depends(aktive_gruppe), db: DBSession = Depends(get_session)
):
    """Films watched around today's date in earlier years (±3 days)."""
    heute = heute or datetime.now(BERLIN).date()
    treffer = []
    for w in db.exec(select(Watched).where(col(Watched.hidden).is_(False), Watched.gruppe_id == gid)).all():
        tag = _utc(w.watched_at).astimezone(BERLIN).date()
        jahre = heute.year - tag.year
        if jahre < 1:
            continue
        abstand = (_gleicher_tag(tag, heute.year) - heute).days
        if abs(abstand) <= FENSTER_TAGE:
            treffer.append((w, jahre, abstand))
    treffer.sort(key=lambda t: (abs(t[2]), t[1]))
    eintraege = {e["id"]: e for e in _payload(db, [w for w, _, _ in treffer])}
    return {
        "erinnerungen": [{"jahre": j, "tage": a, "eintrag": eintraege[w.id]} for w, j, a in treffer],
    }
