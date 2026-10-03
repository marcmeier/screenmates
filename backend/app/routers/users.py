"""Users, name selection (the lightweight login), film-as-PIN, attendance."""

from __future__ import annotations

import time
from collections import defaultdict, deque

from fastapi import APIRouter, Depends, HTTPException, Request, Response
from pydantic import BaseModel, Field
from sqlalchemy.exc import IntegrityError
from sqlmodel import Session as DBSession
from sqlmodel import func, select

from ..db import get_session
from ..models import User
from ..serialize import user_dict
from ..session import (
    current_user,
    ensure_session,
    is_host,
    require_host,
    require_owner_or_host,
    require_user,
)

router = APIRouter(prefix="/api", tags=["users"])

PALETTE = ["#e50914", "#f5a623", "#7ed321", "#4a90e2", "#bd10e0", "#50e3c2", "#ff6b6b", "#d4a017"]

# Film-as-PIN guesses: at most MAX_TRIES wrong films per user per WINDOW seconds.
MAX_TRIES, WINDOW = 8, 600
_fails: dict[int, deque[float]] = defaultdict(deque)


def _throttled(user_id: int) -> bool:
    q = _fails[user_id]
    while q and q[0] < time.monotonic() - WINDOW:
        q.popleft()
    return len(q) >= MAX_TRIES


class NameAnlegen(BaseModel):
    name: str = Field(min_length=1, max_length=30)


class NameWaehlen(BaseModel):
    user_id: int | None = None
    movie_id: int | None = None  # the protection film, when the user is guarded


class SchutzSetzen(BaseModel):
    movie_id: int | None = None  # None removes the protection


@router.get("/users")
def list_users(
    db: DBSession = Depends(get_session),
    user: User | None = Depends(current_user),
    host: bool = Depends(is_host),
):
    rows = db.exec(select(User).order_by(User.created_at)).all()
    return {"users": [user_dict(u) for u in rows], "ich": user_dict(user) if user else None, "host": host}


@router.post("/users", status_code=201)
def create_user(body: NameAnlegen, db: DBSession = Depends(get_session)):
    name = " ".join(body.name.split())
    if not name:
        raise HTTPException(422, "Name fehlt.")
    count = db.exec(select(func.count()).select_from(User)).one()
    u = User(name=name, color=PALETTE[count % len(PALETTE)])
    db.add(u)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(409, f"„{name}“ gibt es schon.") from None
    db.refresh(u)
    return user_dict(u)


@router.post("/users/waehlen")
def choose_user(body: NameWaehlen, request: Request, response: Response, db: DBSession = Depends(get_session)):
    sess = ensure_session(request, response, db)
    if body.user_id is None:  # logout also drops host rights
        sess.user_id, sess.is_host = None, False
        db.add(sess)
        db.commit()
        return {"ich": None, "host": False}
    u = db.get(User, body.user_id)
    if u is None:
        raise HTTPException(404, "Diesen Namen gibt es nicht.")
    if u.schutz_movie_id is not None:
        if _throttled(u.id):
            raise HTTPException(429, "Zu viele Fehlversuche – bitte später nochmal.")
        if body.movie_id != u.schutz_movie_id:
            _fails[u.id].append(time.monotonic())
            raise HTTPException(403, "Das ist nicht der richtige Film.")
        _fails.pop(u.id, None)
    if sess.user_id != u.id:
        sess.is_host = False  # host rights belong to a person, not a browser
    sess.user_id = u.id
    db.add(sess)
    db.commit()
    return {"ich": user_dict(u), "host": sess.is_host}


@router.delete("/users/{user_id}", dependencies=[Depends(require_host)])
def delete_user(user_id: int, db: DBSession = Depends(get_session)):
    u = db.get(User, user_id)
    if u is None:
        raise HTTPException(404)
    db.delete(u)
    db.commit()
    return {"ok": True}


@router.get("/users/{user_id}/schutz")
def get_schutz(user_id: int, db: DBSession = Depends(get_session)):
    u = db.get(User, user_id)
    if u is None:
        raise HTTPException(404)
    return {"hat_schutz": u.schutz_movie_id is not None}


@router.post("/users/{user_id}/schutz")
def set_schutz(
    user_id: int,
    body: SchutzSetzen,
    db: DBSession = Depends(get_session),
    user: User | None = Depends(current_user),
    host: bool = Depends(is_host),
):
    u = db.get(User, user_id)
    if u is None:
        raise HTTPException(404)
    require_owner_or_host(u.id, user, host)
    u.schutz_movie_id = body.movie_id
    db.add(u)
    db.commit()
    return {"hat_schutz": u.schutz_movie_id is not None}


@router.post("/dabei")
def toggle_dabei(user: User = Depends(require_user), db: DBSession = Depends(get_session)):
    user.dabei = not user.dabei
    db.add(user)
    db.commit()
    return {"dabei": user.dabei}


@router.delete("/dabei", dependencies=[Depends(require_host)])
def reset_dabei(db: DBSession = Depends(get_session)):
    for u in db.exec(select(User).where(User.dabei)).all():
        u.dabei = False
        db.add(u)
    db.commit()
    return {"ok": True}
