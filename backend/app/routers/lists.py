"""Wishlist ('Merkliste'), suggestions for the next evening ('Vorschläge') and vetoes."""

from __future__ import annotations

from collections import defaultdict

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlmodel import Session as DBSession
from sqlmodel import col, select

from ..db import get_session
from ..gruppen import aktive_gruppe, require_gruppen_admin
from ..models import Movie, Suggestion, User, Veto, Wishlist
from ..serialize import iso, movie_dict, with_flags
from ..session import require_user
from ..util import ensure_movie

router = APIRouter(prefix="/api", tags=["lists"])


class MovieRef(BaseModel):
    movie_id: int


@router.get("/wishlist")
def get_wishlist(gid: int = Depends(aktive_gruppe), db: DBSession = Depends(get_session)):
    rows = db.exec(
        select(Wishlist, Movie).join(Movie).where(Wishlist.gruppe_id == gid).order_by(col(Wishlist.created_at).desc())
    ).all()
    items = [movie_dict(m) | {"gemerkt_von": w.user_id, "gemerkt_am": iso(w.created_at)} for w, m in rows]
    return {"wishlist": with_flags(db, items)}


@router.post("/wishlist", status_code=201)
async def add_wishlist(
    body: MovieRef,
    user: User = Depends(require_user),
    gid: int = Depends(aktive_gruppe),
    db: DBSession = Depends(get_session),
):
    await ensure_movie(db, body.movie_id)
    if not db.exec(select(Wishlist).where(Wishlist.movie_id == body.movie_id, Wishlist.gruppe_id == gid)).first():
        db.add(Wishlist(movie_id=body.movie_id, user_id=user.id, gruppe_id=gid))
        db.commit()
    return {"ok": True}


@router.delete("/wishlist/{movie_id}")
def remove_wishlist(movie_id: int, gid: int = Depends(aktive_gruppe), db: DBSession = Depends(get_session)):
    for w in db.exec(select(Wishlist).where(Wishlist.movie_id == movie_id, Wishlist.gruppe_id == gid)).all():
        db.delete(w)
    db.commit()
    return {"ok": True}


@router.get("/suggestions")
def get_suggestions(gid: int = Depends(aktive_gruppe), db: DBSession = Depends(get_session)):
    """One entry per film, with everyone who suggested it — most wanted first."""
    rows = db.exec(
        select(Suggestion, Movie).join(Movie).where(Suggestion.gruppe_id == gid).order_by(Suggestion.created_at)
    ).all()
    grouped: dict[int, dict] = {}
    von: dict[int, list[int]] = defaultdict(list)
    for s, m in rows:
        grouped.setdefault(m.id, movie_dict(m) | {"seit": iso(s.created_at)})
        von[m.id].append(s.user_id)
    veto_von: dict[int, list[int]] = defaultdict(list)
    for v in db.exec(select(Veto).where(Veto.gruppe_id == gid)).all():
        veto_von[v.movie_id].append(v.user_id)
    items = [m | {"von": von[mid], "veto_von": sorted(veto_von[mid])} for mid, m in grouped.items()]
    items.sort(key=lambda m: -len(m["von"]))  # stable: ties keep oldest first
    return {"suggestions": items}


def _drop_orphan_vetoes(db: DBSession, gid: int) -> None:
    """A veto only means something while the film is up for the evening."""
    suggested = select(Suggestion.movie_id).where(Suggestion.gruppe_id == gid)
    for v in db.exec(select(Veto).where(Veto.gruppe_id == gid, col(Veto.movie_id).not_in(suggested))).all():
        db.delete(v)


@router.post("/veto")
def veto(
    body: MovieRef,
    user: User = Depends(require_user),
    gid: int = Depends(aktive_gruppe),
    db: DBSession = Depends(get_session),
):
    """'Not with me': one veto per person and group; a new one replaces the old."""
    if not db.exec(select(Suggestion).where(Suggestion.movie_id == body.movie_id, Suggestion.gruppe_id == gid)).first():
        raise HTTPException(422, "Ein Veto gibt es nur gegen Filme, die gerade vorgeschlagen sind.")
    for old in db.exec(select(Veto).where(Veto.user_id == user.id, Veto.gruppe_id == gid)).all():
        db.delete(old)
    db.flush()
    db.add(Veto(user_id=user.id, movie_id=body.movie_id, gruppe_id=gid))
    db.commit()
    return {"veto": body.movie_id}


@router.delete("/veto")
def withdraw_veto(
    user: User = Depends(require_user), gid: int = Depends(aktive_gruppe), db: DBSession = Depends(get_session)
):
    for old in db.exec(select(Veto).where(Veto.user_id == user.id, Veto.gruppe_id == gid)).all():
        db.delete(old)
    db.commit()
    return {"veto": None}


@router.post("/suggestions", status_code=201)
async def add_suggestion(
    body: MovieRef,
    user: User = Depends(require_user),
    gid: int = Depends(aktive_gruppe),
    db: DBSession = Depends(get_session),
):
    await ensure_movie(db, body.movie_id)
    exists = db.exec(
        select(Suggestion).where(
            Suggestion.movie_id == body.movie_id, Suggestion.user_id == user.id, Suggestion.gruppe_id == gid
        )
    ).first()
    if not exists:
        db.add(Suggestion(movie_id=body.movie_id, user_id=user.id, gruppe_id=gid))
        db.commit()
    return {"ok": True}


@router.delete("/suggestions/alle", dependencies=[Depends(require_gruppen_admin)])
def clear_all(gid: int = Depends(aktive_gruppe), db: DBSession = Depends(get_session)):
    for s in db.exec(select(Suggestion).where(Suggestion.gruppe_id == gid)).all():
        db.delete(s)
    db.flush()
    _drop_orphan_vetoes(db, gid)
    db.commit()
    return {"ok": True}


@router.delete("/suggestions/{movie_id}")
def withdraw(
    movie_id: int,
    user: User = Depends(require_user),
    gid: int = Depends(aktive_gruppe),
    db: DBSession = Depends(get_session),
):
    for s in db.exec(
        select(Suggestion).where(
            Suggestion.movie_id == movie_id, Suggestion.user_id == user.id, Suggestion.gruppe_id == gid
        )
    ).all():
        db.delete(s)
    db.flush()
    _drop_orphan_vetoes(db, gid)
    db.commit()
    return {"ok": True}


@router.delete("/suggestions")
def clear_mine(
    user: User = Depends(require_user), gid: int = Depends(aktive_gruppe), db: DBSession = Depends(get_session)
):
    for s in db.exec(select(Suggestion).where(Suggestion.user_id == user.id, Suggestion.gruppe_id == gid)).all():
        db.delete(s)
    db.flush()
    _drop_orphan_vetoes(db, gid)
    db.commit()
    return {"ok": True}
