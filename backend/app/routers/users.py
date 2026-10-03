"""Users, name selection (the lightweight 'login'), and film-as-PIN protection."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request, Response
from pydantic import BaseModel
from sqlmodel import Session as DBSession
from sqlmodel import select

from ..db import get_session
from ..models import Session, User
from ..serialize import user_dict
from ..session import current_session, current_user, set_session_user

router = APIRouter(prefix="/api", tags=["users"])

PALETTE = ["#e50914", "#f5a623", "#7ed321", "#4a90e2", "#bd10e0", "#50e3c2", "#ff6b6b", "#b8860b"]


class NameAnlegen(BaseModel):
    name: str


class NameWaehlen(BaseModel):
    user_id: int | None = None
    movie_id: int | None = None  # the protection film, when a user is guarded


class SchutzSetzen(BaseModel):
    movie_id: int | None = None


@router.get("/users")
def list_users(db: DBSession = Depends(get_session), user: User | None = Depends(current_user)):
    rows = db.exec(select(User).order_by(User.created_at)).all()
    return {"users": [user_dict(u) for u in rows], "ich": user_dict(user) if user else None}


@router.post("/users")
def create_user(body: NameAnlegen, db: DBSession = Depends(get_session)):
    name = body.name.strip()
    if not name:
        raise HTTPException(400, "Name fehlt")
    if db.exec(select(User).where(User.name == name)).first():
        raise HTTPException(409, "Name schon vergeben")
    color = PALETTE[db.exec(select(User)).all().__len__() % len(PALETTE)]
    u = User(name=name, color=color)
    db.add(u)
    db.commit()
    db.refresh(u)
    return user_dict(u)


@router.post("/users/waehlen")
def choose_user(
    body: NameWaehlen,
    db: DBSession = Depends(get_session),
    sess: Session = Depends(current_session),
):
    if body.user_id is None:
        set_session_user(db, sess.sid, None)
        return {"ich": None}
    u = db.get(User, body.user_id)
    if u is None:
        raise HTTPException(404, "Unbekannt")
    if u.schutz_movie_id is not None and u.schutz_movie_id != body.movie_id:
        raise HTTPException(403, "Falscher Film")
    set_session_user(db, sess.sid, u.id)
    return {"ich": user_dict(u)}


@router.delete("/users/{user_id}")
def delete_user(user_id: int, db: DBSession = Depends(get_session)):
    u = db.get(User, user_id)
    if u:
        db.delete(u)
        db.commit()
    return {"ok": True}


@router.get("/users/{user_id}/schutz")
def get_schutz(user_id: int, db: DBSession = Depends(get_session)):
    u = db.get(User, user_id)
    if u is None:
        raise HTTPException(404)
    return {"hat_schutz": u.schutz_movie_id is not None, "movie_id": u.schutz_movie_id}


@router.post("/users/{user_id}/schutz")
def set_schutz(user_id: int, body: SchutzSetzen, db: DBSession = Depends(get_session)):
    u = db.get(User, user_id)
    if u is None:
        raise HTTPException(404)
    u.schutz_movie_id = body.movie_id
    db.add(u)
    db.commit()
    return {"hat_schutz": u.schutz_movie_id is not None}
