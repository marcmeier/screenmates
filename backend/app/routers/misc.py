"""Status, info panel, spin wheel, activity feed, KI search, sync."""

from __future__ import annotations

import asyncio
import random

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlmodel import Session as DBSession
from sqlmodel import col, func, select

from .. import erfolge, ki, tmdb
from ..config import settings
from ..db import get_session
from ..gruppen import aktive_gruppe, aktuelle_gruppe, mitglieder, require_gruppen_admin
from ..models import (
    Abend,
    AppMeta,
    Erfolg,
    Feature,
    Info,
    Movie,
    Suggestion,
    User,
    Veto,
    Watched,
    WatchedNote,
    Wishlist,
    now,
)
from ..serialize import iso, movie_dict, with_flags
from ..session import require_admin
from ..util import upsert_movie

router = APIRouter(prefix="/api", tags=["misc"])

SYNC_PAGES = 10  # 20 films per page
_sync_lock = asyncio.Lock()


class InfoSetzen(BaseModel):
    text: str = Field(max_length=20_000)


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


@router.get("/health")
def health():
    return {"ok": True}


@router.get("/status")
def status(db: DBSession = Depends(get_session)):
    return {
        "movie_count": db.exec(select(func.count()).select_from(Movie)).one(),
        "canon_count": db.exec(select(func.count()).select_from(Movie).where(col(Movie.is_canon))).one(),
        # The active group's lists (0 without a group).
        "wishlist_count": db.exec(
            select(func.count()).select_from(Wishlist).where(Wishlist.gruppe_id == aktuelle_gruppe())
        ).one(),
        "watched_count": db.exec(
            select(func.count())
            .select_from(Watched)
            .where(col(Watched.hidden).is_(False), Watched.gruppe_id == aktuelle_gruppe())
        ).one(),
        "last_sync": iso(_meta(db).last_sync),
        "syncing": _sync_lock.locked(),
        "tmdb": settings.tmdb_enabled,
        "ki": settings.llm_enabled,
        "kino": settings.kino_enabled,
        "image_base": settings.tmdb_image_base,
    }


@router.get("/info")
def get_info(gid: int = Depends(aktive_gruppe), db: DBSession = Depends(get_session)):
    info = db.get(Info, gid) or Info(id=gid)
    return {"text": info.text, "updated_at": iso(info.updated_at) if info.text else None}


@router.put("/info", dependencies=[Depends(require_gruppen_admin)])
def put_info(body: InfoSetzen, gid: int = Depends(aktive_gruppe), db: DBSession = Depends(get_session)):
    info = db.get(Info, gid) or Info(id=gid)
    info.text, info.updated_at = body.text, now()
    db.add(info)
    db.commit()
    return {"text": info.text, "updated_at": iso(info.updated_at)}


# --- Spin wheel ---------------------------------------------------------------


def _pool(db: DBSession, gid: int) -> list[dict]:
    """Suggested films, weighted by how many people want them, minus vetoed ones.

    Only when nothing is suggested at all does the wheel fall back to the wishlist;
    if every suggestion has been vetoed, the wheel stays empty on purpose.
    """
    counts = db.exec(
        select(Suggestion.movie_id, func.count()).where(Suggestion.gruppe_id == gid).group_by(Suggestion.movie_id)
    ).all()
    if counts:
        vetoed = set(db.exec(select(Veto.movie_id).where(Veto.gruppe_id == gid)).all())
        counts = [(mid, n) for mid, n in counts if mid not in vetoed]
    else:
        counts = [(mid, 1) for mid in db.exec(select(Wishlist.movie_id).where(Wishlist.gruppe_id == gid)).all()]
    movies = {m.id: m for m in db.exec(select(Movie).where(col(Movie.id).in_([c[0] for c in counts]))).all()}
    return [movie_dict(movies[mid]) | {"gewicht": n} for mid, n in counts if mid in movies]


@router.get("/spin")
def spin_pool(gid: int = Depends(aktive_gruppe), db: DBSession = Depends(get_session)):
    return {"pool": _pool(db, gid)}


@router.post("/spin")
def spin(gid: int = Depends(aktive_gruppe), db: DBSession = Depends(get_session)):
    pool = _pool(db, gid)
    if not pool:
        return {"pick": None, "pool": []}
    pick = random.choices(pool, weights=[m["gewicht"] for m in pool])[0]
    return {"pick": pick, "pool": pool}


# --- Activity feed ------------------------------------------------------------


@router.get("/events")
def events(limit: int = 30, gid: int = Depends(aktive_gruppe), db: DBSession = Depends(get_session)):
    """The active group's feed (wishes are for the whole server, unlocks only of members)."""
    limit = max(1, min(limit, 100))
    leute = mitglieder(db, gid)
    names = {u.id: u.name for u in db.exec(select(User)).all()}
    titles = dict(db.exec(select(Movie.id, Movie.title)).all())
    feed: list[dict] = []
    for w in db.exec(
        select(Watched)
        .where(col(Watched.hidden).is_(False), Watched.gruppe_id == gid)
        .order_by(col(Watched.created_at).desc())
        .limit(limit)
    ):
        feed.append({"typ": "gesehen", "at": w.created_at, "film": titles.get(w.movie_id), "movie_id": w.movie_id})
    for s in db.exec(
        select(Suggestion).where(Suggestion.gruppe_id == gid).order_by(col(Suggestion.created_at).desc()).limit(limit)
    ):
        feed.append(
            {
                "typ": "vorschlag",
                "at": s.created_at,
                "wer": names.get(s.user_id),
                "film": titles.get(s.movie_id),
                "movie_id": s.movie_id,
            }
        )
    for n in db.exec(
        select(WatchedNote)
        .join(Watched)
        .where(Watched.gruppe_id == gid)
        .order_by(col(WatchedNote.created_at).desc())
        .limit(limit)
    ):
        feed.append({"typ": "kommentar", "at": n.created_at, "wer": names.get(n.user_id), "text": n.text[:120]})
    for v in db.exec(select(Veto).where(Veto.gruppe_id == gid).order_by(col(Veto.created_at).desc()).limit(limit)):
        feed.append(
            {
                "typ": "veto",
                "at": v.created_at,
                "wer": names.get(v.user_id),
                "film": titles.get(v.movie_id),
                "movie_id": v.movie_id,
            }
        )
    abend = db.get(Abend, gid)
    if abend and abend.termin and abend.gesetzt_am:
        feed.append(
            {"typ": "termin", "at": abend.gesetzt_am, "wer": names.get(abend.gesetzt_von), "termin": iso(abend.termin)}
        )
    for f in db.exec(select(Feature).order_by(col(Feature.created_at).desc()).limit(limit)):
        feed.append({"typ": "wunsch", "at": f.created_at, "wer": names.get(f.user_id), "text": f.text[:120]})
    for e in db.exec(
        select(Erfolg)
        .where(col(Erfolg.entzogen).is_(False), col(Erfolg.rueckwirkend).is_(False))
        .order_by(col(Erfolg.am).desc())
        .limit(limit)
    ):
        d = erfolge.NACH_KEY.get(e.schluessel)
        if d and e.user_id in leute:
            feed.append(
                {
                    "typ": "erfolg",
                    "at": e.am,
                    "wer": names.get(e.user_id),
                    "user_id": e.user_id,
                    "key": d.key,
                    "name": "einen geheimen Erfolg" if d.geheim else f"„{d.name}“",
                    "emoji": d.emoji,
                    "stufe": d.stufe,
                }
            )
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


@router.post("/sync", dependencies=[Depends(require_admin)])
async def sync(db: DBSession = Depends(get_session)):
    """Pull the most popular and the best-rated films into the catalogue as canon."""
    if not settings.tmdb_enabled:
        raise HTTPException(503, "TMDB ist nicht eingerichtet (TMDB_API_KEY fehlt).")
    if _sync_lock.locked():
        raise HTTPException(409, "Sync läuft bereits.")
    async with _sync_lock:
        before = db.exec(select(func.count()).select_from(Movie)).one()
        passes = (
            ("popularity.desc", {"stimmen_min": 50}),  # skips unreleased films with 1 vote
            ("vote_average.desc", {"stimmen_min": 500}),
        )
        for sort, extra in passes:
            extra = {"dauer_min": tmdb.MIN_RUNTIME, **extra}
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
