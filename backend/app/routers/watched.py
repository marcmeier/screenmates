"""The watched log: entries, ratings, guestbook notes, hearts, participants."""

from __future__ import annotations

from collections import defaultdict
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlmodel import Session as DBSession
from sqlmodel import col, select

from .. import erfolge
from ..db import get_session
from ..gruppen import aktive_gruppe, gruppen_admin, mitglieder, require_owner_or_gruppen_admin
from ..models import (
    Movie,
    NoteHeart,
    Suggestion,
    User,
    Veto,
    Watched,
    WatchedNote,
    WatchedParticipant,
    WatchedRating,
    Wishlist,
)
from ..serialize import iso, movie_dict
from ..session import current_user, require_user
from ..util import ensure_movie

router = APIRouter(prefix="/api", tags=["watched"])


class AlsGesehen(BaseModel):
    movie_id: int
    watched_at: datetime | None = None


class Bewerten(BaseModel):
    stars: int = Field(ge=1, le=5)


class GesehenAendern(BaseModel):
    watched_at: datetime | None = None
    hidden: bool | None = None


class Gaestebuch(BaseModel):
    text: str = Field(min_length=1, max_length=2000)
    parent_id: int | None = None


class Dabei(BaseModel):
    user_ids: list[int] = Field(max_length=100)


class Herz(BaseModel):
    note_id: int


def _payload(db: DBSession, entries: list[Watched]) -> list[dict]:
    """Serialise watched entries with a fixed number of queries, regardless of size."""
    if not entries:
        return []
    ids = [w.id for w in entries]
    movies = {m.id: m for m in db.exec(select(Movie).where(col(Movie.id).in_({w.movie_id for w in entries}))).all()}
    ratings = defaultdict(list)
    for r in db.exec(select(WatchedRating).where(col(WatchedRating.watched_id).in_(ids))).all():
        ratings[r.watched_id].append(r)
    parts = defaultdict(list)
    for p in db.exec(select(WatchedParticipant).where(col(WatchedParticipant.watched_id).in_(ids))).all():
        parts[p.watched_id].append(p.user_id)
    notes = db.exec(
        select(WatchedNote).where(col(WatchedNote.watched_id).in_(ids)).order_by(WatchedNote.created_at)
    ).all()
    hearts = defaultdict(list)
    if notes:
        note_ids = [n.id for n in notes]
        for h in db.exec(select(NoteHeart).where(col(NoteHeart.note_id).in_(note_ids))).all():
            hearts[h.note_id].append(h.user_id)

    # Build the comment trees in memory.
    nodes = {
        n.id: {
            "id": n.id,
            "user_id": n.user_id,
            "text": n.text,
            "created_at": iso(n.created_at),
            "hearts": hearts[n.id],
            "replies": [],
        }
        for n in notes
    }
    roots = defaultdict(list)
    for n in notes:
        if n.parent_id in nodes:
            nodes[n.parent_id]["replies"].append(nodes[n.id])
        else:
            roots[n.watched_id].append(nodes[n.id])

    out = []
    for w in entries:
        rs = ratings[w.id]
        out.append(
            {
                "id": w.id,
                "movie_id": w.movie_id,
                "movie": movie_dict(movies[w.movie_id]) if w.movie_id in movies else None,
                "watched_at": iso(w.watched_at),
                "hidden": w.hidden,
                "rating_avg": round(sum(r.stars for r in rs) / len(rs), 1) if rs else None,
                "ratings": [{"id": r.id, "user_id": r.user_id, "stars": r.stars} for r in rs],
                "participants": parts[w.id],
                "notes": roots[w.id],
            }
        )
    return out


def _get(db: DBSession, watched_id: int, gid: int) -> Watched:
    w = db.get(Watched, watched_id)
    if w is None or w.gruppe_id != gid:
        raise HTTPException(404, "Eintrag nicht gefunden.")
    return w


def _one(db: DBSession, w: Watched) -> dict:
    db.refresh(w)
    return _payload(db, [w])[0]


@router.get("/watched")
def list_watched(
    alle: bool = False,
    movie_id: int | None = None,
    gid: int = Depends(aktive_gruppe),
    db: DBSession = Depends(get_session),
):
    stmt = select(Watched).where(Watched.gruppe_id == gid).order_by(col(Watched.watched_at).desc())
    if not alle:
        stmt = stmt.where(col(Watched.hidden).is_(False))
    if movie_id is not None:  # the film's evenings, newest first (detail sheet)
        stmt = stmt.where(Watched.movie_id == movie_id)
    return {"watched": _payload(db, list(db.exec(stmt).all()))}


@router.post("/watched", status_code=201)
async def add_watched(
    body: AlsGesehen,
    user: User = Depends(require_user),
    gid: int = Depends(aktive_gruppe),
    db: DBSession = Depends(get_session),
):
    await ensure_movie(db, body.movie_id)
    w = Watched(movie_id=body.movie_id, gruppe_id=gid)
    if body.watched_at:
        w.watched_at = body.watched_at
    db.add(w)
    db.flush()
    db.add(WatchedParticipant(watched_id=w.id, user_id=user.id))
    # Whoever suggested it hit the mark (counts once the evening is confirmed).
    for s in db.exec(select(Suggestion).where(Suggestion.movie_id == body.movie_id, Suggestion.gruppe_id == gid)).all():
        erfolge.protokoll(db, "treffer", s.user_id, str(w.id))
    # Seeing a film fulfils it: drop it from the wishlist, the open suggestions and any veto.
    for stale in [
        *db.exec(select(Wishlist).where(Wishlist.movie_id == body.movie_id, Wishlist.gruppe_id == gid)).all(),
        *db.exec(select(Suggestion).where(Suggestion.movie_id == body.movie_id, Suggestion.gruppe_id == gid)).all(),
        *db.exec(select(Veto).where(Veto.movie_id == body.movie_id, Veto.gruppe_id == gid)).all(),
    ]:
        db.delete(stale)
    db.commit()
    return _one(db, w)


@router.patch("/watched/{watched_id}")
def edit_watched(
    watched_id: int, body: GesehenAendern, gid: int = Depends(aktive_gruppe), db: DBSession = Depends(get_session)
):
    w = _get(db, watched_id, gid)
    if body.watched_at is not None:
        w.watched_at = body.watched_at
    if body.hidden is not None:
        w.hidden = body.hidden
    db.add(w)
    db.commit()
    return _one(db, w)


@router.delete("/watched/{watched_id}")
def delete_watched(
    watched_id: int,
    gid: int = Depends(aktive_gruppe),
    ok: bool = Depends(gruppen_admin),
    db: DBSession = Depends(get_session),
):
    if not ok:
        raise HTTPException(403, "Das darf nur ein Admin dieser Gruppe.")
    db.delete(_get(db, watched_id, gid))
    db.commit()
    return {"ok": True}


@router.post("/watched/{watched_id}/rating")
def rate(
    watched_id: int,
    body: Bewerten,
    user: User = Depends(require_user),
    gid: int = Depends(aktive_gruppe),
    db: DBSession = Depends(get_session),
):
    w = _get(db, watched_id, gid)
    r = db.exec(
        select(WatchedRating).where(WatchedRating.watched_id == watched_id, WatchedRating.user_id == user.id)
    ).first() or WatchedRating(watched_id=watched_id, user_id=user.id)
    r.stars = body.stars
    db.add(r)
    db.commit()
    return _one(db, w)


@router.delete("/watched/rating/{rating_id}")
def delete_rating(
    rating_id: int,
    db: DBSession = Depends(get_session),
    user: User | None = Depends(current_user),
    gid: int = Depends(aktive_gruppe),
    admin: bool = Depends(gruppen_admin),
):
    r = db.get(WatchedRating, rating_id)
    if r is None:
        raise HTTPException(404)
    _get(db, r.watched_id, gid)
    require_owner_or_gruppen_admin(r.user_id, user, admin)
    db.delete(r)
    db.commit()
    return {"ok": True}


@router.post("/watched/{watched_id}/notes", status_code=201)
def add_note(
    watched_id: int,
    body: Gaestebuch,
    user: User = Depends(require_user),
    gid: int = Depends(aktive_gruppe),
    db: DBSession = Depends(get_session),
):
    w = _get(db, watched_id, gid)
    if body.parent_id is not None:
        parent = db.get(WatchedNote, body.parent_id)
        if parent is None or parent.watched_id != watched_id:
            raise HTTPException(422, "Antwort passt nicht zu diesem Eintrag.")
    db.add(WatchedNote(watched_id=watched_id, user_id=user.id, text=body.text.strip(), parent_id=body.parent_id))
    db.commit()
    return _one(db, w)


@router.delete("/watched-notes/{note_id}")
def delete_note(
    note_id: int,
    db: DBSession = Depends(get_session),
    user: User | None = Depends(current_user),
    gid: int = Depends(aktive_gruppe),
    admin: bool = Depends(gruppen_admin),
):
    n = db.get(WatchedNote, note_id)
    if n is None:
        raise HTTPException(404)
    _get(db, n.watched_id, gid)
    require_owner_or_gruppen_admin(n.user_id, user, admin)
    db.delete(n)
    db.commit()
    return {"ok": True}


@router.post("/watched/hearts")
def heart(
    body: Herz,
    user: User = Depends(require_user),
    gid: int = Depends(aktive_gruppe),
    db: DBSession = Depends(get_session),
):
    n = db.get(WatchedNote, body.note_id)
    if n is None:
        raise HTTPException(404)
    _get(db, n.watched_id, gid)
    existing = db.exec(select(NoteHeart).where(NoteHeart.note_id == body.note_id, NoteHeart.user_id == user.id)).first()
    if existing:
        db.delete(existing)
    else:
        db.add(NoteHeart(note_id=body.note_id, user_id=user.id))
    db.commit()
    return {"hearted": existing is None}


@router.post("/watched/{watched_id}/dabei")
def set_participants(
    watched_id: int, body: Dabei, gid: int = Depends(aktive_gruppe), db: DBSession = Depends(get_session)
):
    w = _get(db, watched_id, gid)
    wanted = set(body.user_ids)
    if wanted - mitglieder(db, gid):
        raise HTTPException(422, "Nur Mitglieder der Gruppe können dabei gewesen sein.")
    for p in db.exec(select(WatchedParticipant).where(WatchedParticipant.watched_id == watched_id)).all():
        db.delete(p)
    db.flush()
    for uid in sorted(wanted):
        db.add(WatchedParticipant(watched_id=watched_id, user_id=uid))
    db.commit()
    return _one(db, w)
