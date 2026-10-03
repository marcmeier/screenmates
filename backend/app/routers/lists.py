"""Wishlist ('Merkliste') and suggestions ('Vorschläge')."""
from __future__ import annotations

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlmodel import Session as DBSession
from sqlmodel import select

from ..db import get_session
from ..models import Movie, Suggestion, User, Wishlist
from ..serialize import movie_dict
from ..session import current_user
from ..util import ensure_movie

router = APIRouter(prefix="/api", tags=["lists"])


class MovieRef(BaseModel):
    movie_id: int


@router.get("/wishlist")
def get_wishlist(db: DBSession = Depends(get_session)):
    rows = db.exec(select(Wishlist).order_by(Wishlist.created_at.desc())).all()
    out = []
    for w in rows:
        m = db.get(Movie, w.movie_id)
        if m:
            out.append(movie_dict(m, {"wishlist_id": w.id}))
    return {"wishlist": out}


@router.post("/wishlist")
async def add_wishlist(body: MovieRef, db: DBSession = Depends(get_session), user: User | None = Depends(current_user)):
    await ensure_movie(db, body.movie_id)
    if not db.exec(select(Wishlist).where(Wishlist.movie_id == body.movie_id)).first():
        db.add(Wishlist(movie_id=body.movie_id, user_id=user.id if user else None))
        db.commit()
    return {"ok": True}


@router.delete("/wishlist/{movie_id}")
def remove_wishlist(movie_id: int, db: DBSession = Depends(get_session)):
    for w in db.exec(select(Wishlist).where(Wishlist.movie_id == movie_id)).all():
        db.delete(w)
    db.commit()
    return {"ok": True}


@router.get("/suggestions")
def get_suggestions(db: DBSession = Depends(get_session)):
    rows = db.exec(select(Suggestion).order_by(Suggestion.created_at.desc())).all()
    out = []
    for s in rows:
        m = db.get(Movie, s.movie_id)
        if m:
            out.append(movie_dict(m, {"suggestion_id": s.id, "user_id": s.user_id}))
    return {"suggestions": out}


@router.post("/suggestions")
async def add_suggestion(body: MovieRef, db: DBSession = Depends(get_session), user: User | None = Depends(current_user)):
    await ensure_movie(db, body.movie_id)
    db.add(Suggestion(movie_id=body.movie_id, user_id=user.id if user else None))
    db.commit()
    return {"ok": True}


@router.delete("/suggestions")
def clear_mine(db: DBSession = Depends(get_session), user: User | None = Depends(current_user)):
    if user:
        for s in db.exec(select(Suggestion).where(Suggestion.user_id == user.id)).all():
            db.delete(s)
        db.commit()
    return {"ok": True}


@router.delete("/suggestions/alle")
def clear_all(db: DBSession = Depends(get_session)):
    for s in db.exec(select(Suggestion)).all():
        db.delete(s)
    db.commit()
    return {"ok": True}
