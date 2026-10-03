"""Status, info panel, host mode, spin wheel, activity feed, KI search, sync."""

from __future__ import annotations

import asyncio
import random
import time
from collections import defaultdict, deque

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlmodel import Session as DBSession
from sqlmodel import col, func, select

from .. import ki, tmdb
from ..config import settings
from ..db import get_session
from ..models import (
    AppMeta,
    Feature,
    HostState,
    Info,
    Movie,
    Session,
    Suggestion,
    User,
    Watched,
    WatchedNote,
    Wishlist,
    now,
)
from ..serialize import iso, movie_dict, with_flags
from ..session import current_session, is_host, require_host, require_user
from ..util import upsert_movie

router = APIRouter(prefix="/api", tags=["misc"])

SYNC_PAGES = 10  # 20 films per page
_sync_lock = asyncio.Lock()

MAX_TRIES, WINDOW = 8, 600
_host_fails: dict[str, deque[float]] = defaultdict(deque)


class InfoSetzen(BaseModel):
    text: str = Field(max_length=20_000)


class HostModus(BaseModel):
    an: bool
    movie_id: int | None = None


class HostFilm(BaseModel):
    movie_id: int


class KiSuche(BaseModel):
    beschreibung: str = Field("", max_length=1000)
    mit_sammlung: bool = False  # only films already in our catalogue
    ohne_gesehene: bool = True
    jahr_min: int | None = None
    jahr_max: int | None = None
    note_min: float | None = None
    dauer_max: int | None = None
    limit: int = Field(12, ge=1, le=24)


def _meta(db: DBSession) -> AppMeta:
    return db.get(AppMeta, 1) or AppMeta(id=1)


def _host_state(db: DBSession) -> HostState:
    return db.get(HostState, 1) or HostState(id=1)


@router.get("/health")
def health():
    return {"ok": True}


@router.get("/status")
def status(db: DBSession = Depends(get_session)):
    return {
        "movie_count": db.exec(select(func.count()).select_from(Movie)).one(),
        "canon_count": db.exec(select(func.count()).select_from(Movie).where(col(Movie.is_canon))).one(),
        "last_sync": iso(_meta(db).last_sync),
        "syncing": _sync_lock.locked(),
        "tmdb": settings.tmdb_enabled,
        "ki": settings.llm_enabled,
        "image_base": settings.tmdb_image_base,
    }


@router.get("/info")
def get_info(db: DBSession = Depends(get_session)):
    info = db.get(Info, 1) or Info(id=1)
    return {"text": info.text, "updated_at": iso(info.updated_at) if info.text else None}


@router.put("/info", dependencies=[Depends(require_host)])
def put_info(body: InfoSetzen, db: DBSession = Depends(get_session)):
    info = db.get(Info, 1) or Info(id=1)
    info.text, info.updated_at = body.text, now()
    db.add(info)
    db.commit()
    return {"text": info.text, "updated_at": iso(info.updated_at)}


# --- Host mode ---------------------------------------------------------------
# The host film is a shared secret. The first person to enable host mode picks
# it; afterwards anyone who clicks the same film becomes host for their session.


@router.get("/host")
def get_host(db: DBSession = Depends(get_session), host: bool = Depends(is_host)):
    return {"host": host, "eingerichtet": _host_state(db).movie_id is not None}


@router.post("/host")
def set_host(
    body: HostModus,
    _: User = Depends(require_user),
    sess: Session | None = Depends(current_session),
    db: DBSession = Depends(get_session),
):
    # require_user guarantees a logged-in session exists.
    if not body.an:
        sess.is_host = False
    else:
        state = _host_state(db)
        if body.movie_id is None:
            raise HTTPException(422, "Bitte den Host-Film anklicken.")
        if state.movie_id is None:
            state.movie_id = body.movie_id
            db.add(state)
        else:
            fails = _host_fails[sess.sid]
            while fails and fails[0] < time.monotonic() - WINDOW:
                fails.popleft()
            if len(fails) >= MAX_TRIES:
                raise HTTPException(429, "Zu viele Fehlversuche – bitte später nochmal.")
            if body.movie_id != state.movie_id:
                fails.append(time.monotonic())
                raise HTTPException(403, "Das ist nicht der Host-Film.")
            _host_fails.pop(sess.sid, None)
        sess.is_host = True
    db.add(sess)
    db.commit()
    return {"host": sess.is_host, "eingerichtet": True}


@router.get("/host/film", dependencies=[Depends(require_host)])
def get_host_film(db: DBSession = Depends(get_session)):
    state = _host_state(db)
    m = db.get(Movie, state.movie_id) if state.movie_id else None
    return {"movie": movie_dict(m) if m else None}


@router.post("/host/film", dependencies=[Depends(require_host)])
def set_host_film(body: HostFilm, db: DBSession = Depends(get_session)):
    state = _host_state(db)
    state.movie_id = body.movie_id
    db.add(state)
    db.commit()
    return {"ok": True}


# --- Spin wheel ---------------------------------------------------------------


def _pool(db: DBSession) -> list[dict]:
    """Suggested films, weighted by how many people want them (wishlist if none)."""
    counts = db.exec(select(Suggestion.movie_id, func.count()).group_by(Suggestion.movie_id)).all()
    if not counts:
        counts = [(mid, 1) for mid in db.exec(select(Wishlist.movie_id)).all()]
    movies = {m.id: m for m in db.exec(select(Movie).where(col(Movie.id).in_([c[0] for c in counts]))).all()}
    return [movie_dict(movies[mid]) | {"gewicht": n} for mid, n in counts if mid in movies]


@router.get("/spin")
def spin_pool(db: DBSession = Depends(get_session)):
    return {"pool": _pool(db)}


@router.post("/spin")
def spin(db: DBSession = Depends(get_session)):
    pool = _pool(db)
    if not pool:
        return {"pick": None, "pool": []}
    pick = random.choices(pool, weights=[m["gewicht"] for m in pool])[0]
    return {"pick": pick, "pool": pool}


# --- Activity feed ------------------------------------------------------------


@router.get("/events")
def events(limit: int = 30, db: DBSession = Depends(get_session)):
    limit = max(1, min(limit, 100))
    names = {u.id: u.name for u in db.exec(select(User)).all()}
    titles = dict(db.exec(select(Movie.id, Movie.title)).all())
    feed: list[dict] = []
    for w in db.exec(
        select(Watched).where(col(Watched.hidden).is_(False)).order_by(col(Watched.created_at).desc()).limit(limit)
    ):
        feed.append({"typ": "gesehen", "at": w.created_at, "film": titles.get(w.movie_id), "movie_id": w.movie_id})
    for s in db.exec(select(Suggestion).order_by(col(Suggestion.created_at).desc()).limit(limit)):
        feed.append(
            {
                "typ": "vorschlag",
                "at": s.created_at,
                "wer": names.get(s.user_id),
                "film": titles.get(s.movie_id),
                "movie_id": s.movie_id,
            }
        )
    for n in db.exec(select(WatchedNote).order_by(col(WatchedNote.created_at).desc()).limit(limit)):
        feed.append({"typ": "kommentar", "at": n.created_at, "wer": names.get(n.user_id), "text": n.text[:120]})
    for f in db.exec(select(Feature).order_by(col(Feature.created_at).desc()).limit(limit)):
        feed.append({"typ": "wunsch", "at": f.created_at, "wer": names.get(f.user_id), "text": f.text[:120]})
    feed.sort(key=lambda e: iso(e["at"]), reverse=True)
    return {"events": [e | {"at": iso(e["at"])} for e in feed[:limit]]}


# --- KI search ----------------------------------------------------------------


@router.post("/ki-suche")
async def ki_suche(body: KiSuche, db: DBSession = Depends(get_session)):
    if not settings.llm_enabled:
        raise HTTPException(503, "Die KI-Suche ist nicht eingerichtet (LLM_API_KEY fehlt).")
    gesehen_ids = set(db.exec(select(Watched.movie_id)).all())
    vermeiden = (
        list(db.exec(select(Movie.title).where(col(Movie.id).in_(gesehen_ids))).all()) if body.ohne_gesehene else []
    )
    try:
        ideen = await ki.vorschlaege(body.beschreibung, body.limit + 4, vermeiden)
    except ki.KIError as e:
        raise HTTPException(502, str(e)) from e

    results: list[dict] = []
    seen: set[int] = set()
    for idee in ideen:
        titel = idee.get("originaltitel") or idee.get("titel")
        jahr = idee.get("jahr") if isinstance(idee.get("jahr"), int) else None
        movie = await _resolve(db, titel, jahr, nur_lokal=body.mit_sammlung)
        if movie is None or movie["id"] in seen:
            continue
        if body.ohne_gesehene and movie["id"] in gesehen_ids:
            continue
        if not _passes(movie, body):
            continue
        seen.add(movie["id"])
        results.append(movie | {"warum": str(idee.get("warum") or "")[:300]})
        if len(results) >= body.limit:
            break
    return {"results": with_flags(db, results)}


async def _resolve(db: DBSession, titel: str, jahr: int | None, *, nur_lokal: bool) -> dict | None:
    local = db.exec(select(Movie).where(col(Movie.title).ilike(titel) | col(Movie.original_title).ilike(titel))).all()
    for m in local:
        if jahr is None or m.year in (jahr - 1, jahr, jahr + 1):
            return movie_dict(m)
    if nur_lokal:
        return None
    hits = await tmdb.search(titel) or []
    for h in hits:
        if jahr is None or (h["year"] and abs(h["year"] - jahr) <= 1):
            return movie_dict(h)
    return None


def _passes(m: dict, f: KiSuche) -> bool:
    y = m.get("year") or 0
    return not (
        (f.jahr_min and y < f.jahr_min)
        or (f.jahr_max and y > f.jahr_max)
        or (f.note_min and m["vote_average"] < f.note_min)
        or (f.dauer_max and m.get("runtime") and m["runtime"] > f.dauer_max)
    )


# --- TMDB sync ----------------------------------------------------------------


@router.post("/sync", dependencies=[Depends(require_host)])
async def sync(db: DBSession = Depends(get_session)):
    """Pull the most popular and the best-rated horror films into the catalogue as canon."""
    if not settings.tmdb_enabled:
        raise HTTPException(503, "TMDB ist nicht eingerichtet (TMDB_API_KEY fehlt).")
    if _sync_lock.locked():
        raise HTTPException(409, "Sync läuft bereits.")
    async with _sync_lock:
        before = db.exec(select(func.count()).select_from(Movie)).one()
        for sort, extra in (("popularity.desc", {}), ("vote_average.desc", {"stimmen_min": 500})):
            for page in range(1, SYNC_PAGES + 1):
                results = await tmdb.discover(sort=sort, page=page, **extra) or []
                for raw in results:
                    upsert_movie(db, raw, is_canon=True)
                db.commit()
                if len(results) < 20:
                    break
        meta = _meta(db)
        meta.last_sync = now()
        db.add(meta)
        db.commit()
        after = db.exec(select(func.count()).select_from(Movie)).one()
    return {"ok": True, "neu": after - before, "gesamt": after}
