"""Wishlist ('Merkliste') and suggestions for the next evening ('Vorschläge')."""

from __future__ import annotations

from collections import defaultdict

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlmodel import Session as DBSession
from sqlmodel import col, select

from ..db import get_session
from ..models import Movie, Suggestion, User, Wishlist
from ..serialize import iso, movie_dict, with_flags
from ..session import require_host, require_user
from ..util import ensure_movie

router = APIRouter(prefix="/api", tags=["lists"])


class MovieRef(BaseModel):
    movie_id: int


@router.get("/wishlist")
def get_wishlist(db: DBSession = Depends(get_session)):
    rows = db.exec(select(Wishlist, Movie).join(Movie).order_by(col(Wishlist.created_at).desc())).all()
    items = [movie_dict(m) | {"gemerkt_von": w.user_id, "gemerkt_am": iso(w.created_at)} for w, m in rows]
    return {"wishlist": with_flags(db, items)}


@router.post("/wishlist", status_code=201)
async def add_wishlist(body: MovieRef, user: User = Depends(require_user), db: DBSession = Depends(get_session)):
    await ensure_movie(db, body.movie_id)
    if not db.exec(select(Wishlist).where(Wishlist.movie_id == body.movie_id)).first():
        db.add(Wishlist(movie_id=body.movie_id, user_id=user.id))
        db.commit()
    return {"ok": True}


@router.delete("/wishlist/{movie_id}", dependencies=[Depends(require_user)])
def remove_wishlist(movie_id: int, db: DBSession = Depends(get_session)):
    for w in db.exec(select(Wishlist).where(Wishlist.movie_id == movie_id)).all():
        db.delete(w)
    db.commit()
    return {"ok": True}


@router.get("/suggestions")
def get_suggestions(db: DBSession = Depends(get_session)):
    """One entry per film, with everyone who suggested it — most wanted first."""
    rows = db.exec(select(Suggestion, Movie).join(Movie).order_by(Suggestion.created_at)).all()
    grouped: dict[int, dict] = {}
    von: dict[int, list[int]] = defaultdict(list)
    for s, m in rows:
        grouped.setdefault(m.id, movie_dict(m) | {"seit": iso(s.created_at)})
        von[m.id].append(s.user_id)
    items = [m | {"von": von[mid]} for mid, m in grouped.items()]
    items.sort(key=lambda m: -len(m["von"]))  # stable: ties keep oldest first
    return {"suggestions": items}


@router.post("/suggestions", status_code=201)
async def add_suggestion(body: MovieRef, user: User = Depends(require_user), db: DBSession = Depends(get_session)):
    await ensure_movie(db, body.movie_id)
    exists = db.exec(
        select(Suggestion).where(Suggestion.movie_id == body.movie_id, Suggestion.user_id == user.id)
    ).first()
    if not exists:
        db.add(Suggestion(movie_id=body.movie_id, user_id=user.id))
        db.commit()
    return {"ok": True}


@router.delete("/suggestions/alle", dependencies=[Depends(require_host)])
def clear_all(db: DBSession = Depends(get_session)):
    for s in db.exec(select(Suggestion)).all():
        db.delete(s)
    db.commit()
    return {"ok": True}


@router.delete("/suggestions/{movie_id}")
def withdraw(movie_id: int, user: User = Depends(require_user), db: DBSession = Depends(get_session)):
    for s in db.exec(select(Suggestion).where(Suggestion.movie_id == movie_id, Suggestion.user_id == user.id)).all():
        db.delete(s)
    db.commit()
    return {"ok": True}


@router.delete("/suggestions")
def clear_mine(user: User = Depends(require_user), db: DBSession = Depends(get_session)):
    for s in db.exec(select(Suggestion).where(Suggestion.user_id == user.id)).all():
        db.delete(s)
    db.commit()
    return {"ok": True}
