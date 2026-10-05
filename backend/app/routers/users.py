"""Users, name selection (the lightweight login), name requests, film-as-PIN, attendance."""

from __future__ import annotations

import time
from collections import defaultdict, deque

from fastapi import APIRouter, Depends, HTTPException, Request, Response
from pydantic import BaseModel, Field
from sqlalchemy.exc import IntegrityError
from sqlmodel import Session as DBSession
from sqlmodel import col, func, select

from ..db import get_session
from ..models import Abo, User
from ..serialize import user_dict
from ..session import (
    current_user,
    ensure_session,
    is_admin,
    require_admin,
    require_owner_or_admin,
    require_user,
)

router = APIRouter(prefix="/api", tags=["users"])

PALETTE = ["#e50914", "#f5a623", "#7ed321", "#4a90e2", "#bd10e0", "#50e3c2", "#ff6b6b", "#d4a017"]

# Film-as-PIN guesses: at most MAX_TRIES wrong films per user per WINDOW seconds.
MAX_TRIES, WINDOW = 8, 600
_fails: dict[int, deque[float]] = defaultdict(deque)

# Open name requests at a time, so the list an admin has to go through stays short.
MAX_ANTRAEGE = 20


def _throttled(user_id: int) -> bool:
    q = _fails[user_id]
    while q and q[0] < time.monotonic() - WINDOW:
        q.popleft()
    return len(q) >= MAX_TRIES


def admin_count(db: DBSession) -> int:
    return db.exec(select(func.count()).select_from(User).where(col(User.is_admin), col(User.freigegeben))).one()


def ensure_not_last_admin(db: DBSession, u: User) -> None:
    if u.is_admin and u.freigegeben and admin_count(db) <= 1:
        raise HTTPException(409, "Es muss mindestens einen Admin geben.")


def clean_name(raw: str) -> str:
    name = " ".join(raw.split())
    if not name:
        raise HTTPException(422, "Name fehlt.")
    return name


def new_user(db: DBSession, name: str, *, freigegeben: bool, admin: bool = False) -> User:
    count = db.exec(select(func.count()).select_from(User)).one()
    u = User(name=name, color=PALETTE[count % len(PALETTE)], freigegeben=freigegeben, is_admin=admin)
    db.add(u)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(409, f"„{name}“ gibt es schon.") from None
    db.refresh(u)
    return u


class NameAnlegen(BaseModel):
    name: str = Field(min_length=1, max_length=30)


class NameWaehlen(BaseModel):
    user_id: int | None = None
    movie_id: int | None = None  # the protection film, when the user is guarded


class AbosSetzen(BaseModel):
    anbieter: list[int] = Field(max_length=60)  # TMDB provider ids


class SchutzSetzen(BaseModel):
    movie_id: int | None = None  # None removes the protection


@router.get("/users")
def list_users(
    db: DBSession = Depends(get_session),
    user: User | None = Depends(current_user),
    admin: bool = Depends(is_admin),
):
    rows = db.exec(select(User).where(col(User.freigegeben)).order_by(User.created_at)).all()
    abos: dict[int, list[int]] = defaultdict(list)
    for uid, pid in db.exec(select(Abo.user_id, Abo.provider_id).order_by(Abo.provider_id)).all():
        abos[uid].append(pid)
    me = user_dict(user, abos[user.id]) if user else None
    antraege = (
        db.exec(select(func.count()).select_from(User).where(col(User.freigegeben).is_(False))).one() if admin else 0
    )
    return {"users": [user_dict(u, abos[u.id]) for u in rows], "ich": me, "admin": admin, "antraege": antraege}


@router.post("/users", status_code=201)
def create_user(body: NameAnlegen, db: DBSession = Depends(get_session), admin: bool = Depends(is_admin)):
    """Create a name. The very first one becomes admin; afterwards it's a request an admin approves."""
    name = clean_name(body.name)
    if db.exec(select(func.count()).select_from(User)).one() == 0:
        return user_dict(new_user(db, name, freigegeben=True, admin=True))
    if admin:
        return user_dict(new_user(db, name, freigegeben=True))
    offen = db.exec(select(func.count()).select_from(User).where(col(User.freigegeben).is_(False))).one()
    if offen >= MAX_ANTRAEGE:
        raise HTTPException(429, "Gerade warten schon viele Anträge – bitte später nochmal.")
    return user_dict(new_user(db, name, freigegeben=False))


@router.post("/users/waehlen")
def choose_user(body: NameWaehlen, request: Request, response: Response, db: DBSession = Depends(get_session)):
    sess = ensure_session(request, response, db)
    if body.user_id is None:  # logout; the browser keeps its access
        sess.user_id = None
        db.add(sess)
        db.commit()
        return {"ich": None, "admin": False}
    u = db.get(User, body.user_id)
    if u is None:
        raise HTTPException(404, "Diesen Namen gibt es nicht.")
    if not u.freigegeben:
        raise HTTPException(403, f"„{u.name}“ wartet noch auf die Freigabe durch einen Admin.")
    if u.schutz_movie_id is not None:
        if _throttled(u.id):
            raise HTTPException(429, "Zu viele Fehlversuche – bitte später nochmal.")
        if body.movie_id != u.schutz_movie_id:
            _fails[u.id].append(time.monotonic())
            raise HTTPException(403, "Das ist nicht der richtige Film.")
        _fails.pop(u.id, None)
    sess.user_id = u.id
    sess.zugang = True  # whoever holds a name is inside, also after logging out
    db.add(sess)
    db.commit()
    return {"ich": user_dict(u), "admin": u.is_admin}


@router.delete("/users/{user_id}", dependencies=[Depends(require_admin)])
def delete_user(user_id: int, db: DBSession = Depends(get_session)):
    """Delete a name - also how an admin turns down a request."""
    u = db.get(User, user_id)
    if u is None:
        raise HTTPException(404)
    ensure_not_last_admin(db, u)
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
    admin: bool = Depends(is_admin),
):
    u = db.get(User, user_id)
    if u is None:
        raise HTTPException(404)
    require_owner_or_admin(u.id, user, admin)
    u.schutz_movie_id = body.movie_id
    db.add(u)
    db.commit()
    return {"hat_schutz": u.schutz_movie_id is not None}


@router.post("/abos")
def set_abos(body: AbosSetzen, user: User = Depends(require_user), db: DBSession = Depends(get_session)):
    """Replace my streaming subscriptions."""
    for a in db.exec(select(Abo).where(Abo.user_id == user.id)).all():
        db.delete(a)
    db.flush()
    for pid in sorted(set(body.anbieter)):
        db.add(Abo(user_id=user.id, provider_id=pid))
    db.commit()
    return {"abos": sorted(set(body.anbieter))}


@router.post("/dabei")
def toggle_dabei(user: User = Depends(require_user), db: DBSession = Depends(get_session)):
    user.dabei = not user.dabei
    db.add(user)
    db.commit()
    return {"dabei": user.dabei}


@router.delete("/dabei", dependencies=[Depends(require_admin)])
def reset_dabei(db: DBSession = Depends(get_session)):
    for u in db.exec(select(User).where(User.dabei)).all():
        u.dabei = False
        db.add(u)
    db.commit()
    return {"ok": True}
