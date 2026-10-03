"""Status, info panel, host mode, spin wheel, attendance, KI search, sync."""
from __future__ import annotations

import random

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlmodel import Session as DBSession
from sqlmodel import func, select

from .. import tmdb
from ..config import settings
from ..db import get_session
from ..models import (HostState, Info, Movie, Suggestion, User, Watched,
                      Wishlist)
from ..serialize import movie_dict
from ..session import current_user

router = APIRouter(prefix="/api", tags=["misc"])


class InfoSetzen(BaseModel):
    text: str


class HostModus(BaseModel):
    an: bool
    schluessel: str | None = None
    movie_id: int | None = None


class HostFilm(BaseModel):
    movie_id: int | None = None


class KiSuche(BaseModel):
    beschreibung: str = ""
    mit_sammlung: bool = False
    ohne_gesehene: bool = False
    include: str = ""
    exclude: str = ""
    limit: int = 24


@router.get("/health")
def health():
    return {"ok": True}


@router.get("/status")
def status(db: DBSession = Depends(get_session)):
    movie_count = db.exec(select(func.count()).select_from(Movie)).one()
    canon_count = db.exec(select(func.count()).select_from(Movie).where(Movie.is_canon == True)).one()  # noqa: E712
    return {
        "movie_count": movie_count,
        "canon_count": canon_count,
        "tmdb": settings.tmdb_enabled,
        "ki": settings.llm_enabled,
        "image_base": settings.tmdb_image_base,
        "syncing": False,
    }


@router.get("/features/flags")
def feature_flags():
    return {"tmdb": settings.tmdb_enabled, "ki": settings.llm_enabled, "clips": True}


@router.get("/info")
def get_info(db: DBSession = Depends(get_session)):
    info = db.get(Info, 1) or Info(id=1, text="")
    return {"text": info.text, "updated_at": info.updated_at.isoformat()}


@router.put("/info")
def put_info(body: InfoSetzen, db: DBSession = Depends(get_session)):
    info = db.get(Info, 1)
    if info is None:
        info = Info(id=1)
    info.text = body.text
    from ..models import now
    info.updated_at = now()
    db.add(info)
    db.commit()
    return {"text": info.text}


def _host(db: DBSession) -> HostState:
    h = db.get(HostState, 1)
    if h is None:
        h = HostState(id=1)
        db.add(h)
        db.commit()
        db.refresh(h)
    return h


@router.get("/host")
def get_host(db: DBSession = Depends(get_session)):
    h = _host(db)
    return {"an": h.an, "schluessel": h.schluessel}


@router.post("/host")
def set_host(body: HostModus, db: DBSession = Depends(get_session)):
    h = _host(db)
    h.an = body.an
    if body.schluessel is not None:
        h.schluessel = body.schluessel
    if body.movie_id is not None:
        h.movie_id = body.movie_id
    db.add(h)
    db.commit()
    return {"an": h.an}


@router.get("/host/film")
def get_host_film(db: DBSession = Depends(get_session)):
    h = _host(db)
    m = db.get(Movie, h.movie_id) if h.movie_id else None
    return {"movie": movie_dict(m) if m else None}


@router.post("/host/film")
def set_host_film(body: HostFilm, db: DBSession = Depends(get_session)):
    h = _host(db)
    h.movie_id = body.movie_id
    db.add(h)
    db.commit()
    return {"ok": True}


@router.get("/spin")
def spin_pool(db: DBSession = Depends(get_session)):
    """The wheel draws from current suggestions, falling back to the wishlist."""
    sug = db.exec(select(Suggestion)).all()
    ids = [s.movie_id for s in sug] or [w.movie_id for w in db.exec(select(Wishlist)).all()]
    pool = [movie_dict(m) for mid in ids if (m := db.get(Movie, mid))]
    return {"pool": pool}


@router.post("/spin")
def spin(db: DBSession = Depends(get_session)):
    pool = spin_pool(db)["pool"]
    if not pool:
        return {"pick": None, "pool": []}
    return {"pick": random.choice(pool), "pool": pool}


@router.post("/dabei")
def dabei(db: DBSession = Depends(get_session), user: User | None = Depends(current_user)):
    """Toggle 'I'm in for movie night' — minimal: just echoes the current user."""
    return {"ich": user.id if user else None, "dabei": user is not None}


@router.get("/events")
def events(db: DBSession = Depends(get_session)):
    """Lightweight activity feed (the original uses this for live updates)."""
    recent = db.exec(select(Watched).order_by(Watched.watched_at.desc()).limit(10)).all()
    return {"events": [{"type": "watched", "movie_id": w.movie_id, "at": w.watched_at.isoformat()} for w in recent]}


@router.post("/ki-suche")
async def ki_suche(body: KiSuche, db: DBSession = Depends(get_session)):
    if not settings.llm_enabled:
        # Graceful fallback: keyword discover so the tab still works without a key.
        results = await tmdb.discover_horror(limit=body.limit)
        return {
            "results": results,
            "hinweis": "KI nicht konfiguriert (LLM_API_KEY fehlt) – zeige beliebte Horrorfilme.",
        }
    # TODO: call the LLM to turn `beschreibung` into discover filters / a ranked list.
    results = await tmdb.discover_horror(limit=body.limit)
    return {"results": results, "hinweis": None}


@router.post("/sync")
async def sync(db: DBSession = Depends(get_session)):
    """Pull a page of popular horror from TMDB into the local catalogue as canon."""
    if not settings.tmdb_enabled:
        return {"ok": False, "reason": "TMDB_API_KEY fehlt"}
    added = 0
    results = await tmdb.discover_horror(limit=60)
    for raw in results:
        if db.get(Movie, raw["id"]) is None:
            db.add(Movie(is_canon=True, **{k: raw[k] for k in raw if k in Movie.model_fields}))
            added += 1
    db.commit()
    return {"ok": True, "added": added}
