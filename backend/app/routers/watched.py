"""The watched log: entries, ratings, guestbook notes, hearts, participants."""
from __future__ import annotations

from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlmodel import Session as DBSession
from sqlmodel import select

from ..db import get_session
from ..models import (Movie, NoteHeart, User, Watched, WatchedNote,
                      WatchedParticipant, WatchedRating)
from ..serialize import movie_dict
from ..session import current_user
from ..util import ensure_movie

router = APIRouter(prefix="/api", tags=["watched"])


class AlsGesehen(BaseModel):
    movie_id: int


class Bewerten(BaseModel):
    stars: int


class GesehenAendern(BaseModel):
    watched_at: datetime | None = None
    hidden: bool | None = None


class Gaestebuch(BaseModel):
    text: str
    parent_id: int | None = None


class Dabei(BaseModel):
    user_ids: list[int]


class Herz(BaseModel):
    note_id: int


def _entry_dict(db: DBSession, w: Watched) -> dict:
    m = db.get(Movie, w.movie_id)
    ratings = db.exec(select(WatchedRating).where(WatchedRating.watched_id == w.id)).all()
    notes = db.exec(select(WatchedNote).where(WatchedNote.watched_id == w.id)).all()
    parts = db.exec(select(WatchedParticipant).where(WatchedParticipant.watched_id == w.id)).all()
    avg = round(sum(r.stars for r in ratings) / len(ratings), 1) if ratings else None
    return {
        "id": w.id,
        "movie_id": w.movie_id,
        "movie": movie_dict(m) if m else None,
        "watched_at": w.watched_at.isoformat(),
        "hidden": w.hidden,
        "rating_avg": avg,
        "ratings": [{"user_id": r.user_id, "stars": r.stars} for r in ratings],
        "participants": [p.user_id for p in parts],
        "notes": [_note_dict(db, n) for n in notes if n.parent_id is None],
    }


def _note_dict(db: DBSession, n: WatchedNote) -> dict:
    hearts = db.exec(select(NoteHeart).where(NoteHeart.note_id == n.id)).all()
    replies = db.exec(
        select(WatchedNote).where(WatchedNote.parent_id == n.id)
    ).all()
    return {
        "id": n.id,
        "user_id": n.user_id,
        "text": n.text,
        "created_at": n.created_at.isoformat(),
        "hearts": [h.user_id for h in hearts],
        "replies": [_note_dict(db, r) for r in replies],
    }


@router.get("/watched")
def list_watched(db: DBSession = Depends(get_session)):
    rows = db.exec(select(Watched).order_by(Watched.watched_at.desc())).all()
    return {"watched": [_entry_dict(db, w) for w in rows]}


@router.post("/watched")
async def add_watched(body: AlsGesehen, db: DBSession = Depends(get_session)):
    await ensure_movie(db, body.movie_id)
    w = Watched(movie_id=body.movie_id)
    db.add(w)
    db.commit()
    db.refresh(w)
    return _entry_dict(db, w)


@router.patch("/watched/{watched_id}")
def edit_watched(watched_id: int, body: GesehenAendern, db: DBSession = Depends(get_session)):
    w = db.get(Watched, watched_id)
    if w is None:
        raise HTTPException(404)
    if body.watched_at is not None:
        w.watched_at = body.watched_at
    if body.hidden is not None:
        w.hidden = body.hidden
    db.add(w)
    db.commit()
    return _entry_dict(db, w)


@router.delete("/watched/{watched_id}")
def delete_watched(watched_id: int, db: DBSession = Depends(get_session)):
    w = db.get(Watched, watched_id)
    if w:
        db.delete(w)
        db.commit()
    return {"ok": True}


@router.post("/watched/{watched_id}/rating")
def rate(watched_id: int, body: Bewerten, db: DBSession = Depends(get_session), user: User | None = Depends(current_user)):
    if user is None:
        raise HTTPException(401, "Kein Nutzer gewählt")
    existing = db.exec(
        select(WatchedRating).where(WatchedRating.watched_id == watched_id, WatchedRating.user_id == user.id)
    ).first()
    if existing:
        existing.stars = body.stars
        db.add(existing)
    else:
        db.add(WatchedRating(watched_id=watched_id, user_id=user.id, stars=body.stars))
    db.commit()
    return _entry_dict(db, db.get(Watched, watched_id))


@router.delete("/watched/rating/{rating_id}")
def delete_rating(rating_id: int, db: DBSession = Depends(get_session)):
    r = db.get(WatchedRating, rating_id)
    if r:
        db.delete(r)
        db.commit()
    return {"ok": True}


@router.post("/watched/{watched_id}/notes")
def add_note(watched_id: int, body: Gaestebuch, db: DBSession = Depends(get_session), user: User | None = Depends(current_user)):
    n = WatchedNote(watched_id=watched_id, user_id=user.id if user else None, text=body.text, parent_id=body.parent_id)
    db.add(n)
    db.commit()
    db.refresh(n)
    return _note_dict(db, n)


@router.delete("/watched-notes/{note_id}")
def delete_note(note_id: int, db: DBSession = Depends(get_session)):
    n = db.get(WatchedNote, note_id)
    if n:
        db.delete(n)
        db.commit()
    return {"ok": True}


@router.post("/watched/hearts")
def heart(body: Herz, db: DBSession = Depends(get_session), user: User | None = Depends(current_user)):
    if user is None:
        raise HTTPException(401)
    existing = db.exec(
        select(NoteHeart).where(NoteHeart.note_id == body.note_id, NoteHeart.user_id == user.id)
    ).first()
    if existing:
        db.delete(existing)
        db.commit()
        return {"hearted": False}
    db.add(NoteHeart(note_id=body.note_id, user_id=user.id))
    db.commit()
    return {"hearted": True}


@router.post("/watched/{watched_id}/dabei")
def set_participants(watched_id: int, body: Dabei, db: DBSession = Depends(get_session)):
    for p in db.exec(select(WatchedParticipant).where(WatchedParticipant.watched_id == watched_id)).all():
        db.delete(p)
    for uid in body.user_ids:
        db.add(WatchedParticipant(watched_id=watched_id, user_id=uid))
    db.commit()
    return _entry_dict(db, db.get(Watched, watched_id))
