"""Groups: switching the active group, and managing groups and members."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request, Response
from pydantic import BaseModel, Field
from sqlalchemy.exc import IntegrityError
from sqlmodel import Session as DBSession
from sqlmodel import col, select

from ..db import get_session
from ..gruppen import gruppe_oder_404, ist_gruppen_admin, mitgliedschaften
from ..models import Abend, Gruppe, Info, KinoState, Mitglied, Session, User
from ..session import current_session, current_user, ensure_session, is_admin, require_admin, require_user
from ..sprache import tr
from .users import clean_name

router = APIRouter(prefix="/api", tags=["gruppen"])


class Aktiv(BaseModel):
    gruppe_id: int


class GruppeAnlegen(BaseModel):
    name: str = Field(min_length=1, max_length=40)


class MitgliedSetzen(BaseModel):
    admin: bool = False


def _gruppe_dict(db: DBSession, g: Gruppe) -> dict:
    ms = db.exec(select(Mitglied).where(Mitglied.gruppe_id == g.id).order_by(Mitglied.seit)).all()
    return {
        "id": g.id,
        "name": g.name,
        "mitglieder": [{"user_id": m.user_id, "admin": m.ist_admin, "dabei": m.dabei} for m in ms],
    }


def _verwalten(db: DBSession, gid: int, user: User | None, admin: bool) -> Gruppe:
    g = gruppe_oder_404(db, gid)
    if not ist_gruppen_admin(db, gid, user, admin):
        raise HTTPException(403, "Das darf nur ein Admin dieser Gruppe.")
    return g


# --- my groups -------------------------------------------------------------------------


@router.get("/gruppen")
def my_groups(
    db: DBSession = Depends(get_session),
    user: User = Depends(require_user),
    sess: Session | None = Depends(current_session),
):
    ms = mitgliedschaften(db, user.id)
    gruppen = db.exec(select(Gruppe).where(col(Gruppe.id).in_(list(ms))).order_by(Gruppe.name)).all()
    aktiv = sess.gruppe_id if sess and sess.gruppe_id in ms else (min(ms) if ms else None)
    return {"aktiv": aktiv, "gruppen": [{"id": g.id, "name": g.name, "admin": ms[g.id].ist_admin} for g in gruppen]}


@router.post("/gruppen/aktiv")
def switch(
    body: Aktiv,
    request: Request,
    response: Response,
    db: DBSession = Depends(get_session),
    user: User = Depends(require_user),
):
    if body.gruppe_id not in mitgliedschaften(db, user.id):
        raise HTTPException(403, "Du bist nicht in dieser Gruppe.")
    sess = ensure_session(request, response, db)
    sess.gruppe_id = body.gruppe_id
    db.add(sess)
    db.commit()
    return {"aktiv": body.gruppe_id}


# --- administration ----------------------------------------------------------------------


@router.get("/admin/gruppen")
def manageable(
    db: DBSession = Depends(get_session), user: User | None = Depends(current_user), admin: bool = Depends(is_admin)
):
    """Server admins: every group. Group admins: the groups they run."""
    if user is None:
        raise HTTPException(401, "Bitte zuerst einen Namen wählen.")
    gruppen = db.exec(select(Gruppe).order_by(Gruppe.name)).all()
    if not admin:
        eigene = {gid for gid, m in mitgliedschaften(db, user.id).items() if m.ist_admin}
        gruppen = [g for g in gruppen if g.id in eigene]
        if not gruppen:
            raise HTTPException(403, "Das darf nur ein Admin.")
    return {"gruppen": [_gruppe_dict(db, g) for g in gruppen], "server_admin": admin}


@router.post("/admin/gruppen", status_code=201, dependencies=[Depends(require_admin)])
def create_group(body: GruppeAnlegen, db: DBSession = Depends(get_session)):
    g = Gruppe(name=clean_name(body.name))
    db.add(g)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(409, tr("Eine Gruppe „{name}“ gibt es schon.", name=g.name)) from None
    db.refresh(g)
    return _gruppe_dict(db, g)


@router.patch("/admin/gruppen/{gid}")
def rename_group(
    gid: int,
    body: GruppeAnlegen,
    db: DBSession = Depends(get_session),
    user: User | None = Depends(current_user),
    admin: bool = Depends(is_admin),
):
    g = _verwalten(db, gid, user, admin)
    g.name = clean_name(body.name)
    db.add(g)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(409, tr("Eine Gruppe „{name}“ gibt es schon.", name=g.name)) from None
    return _gruppe_dict(db, g)


@router.delete("/admin/gruppen/{gid}", dependencies=[Depends(require_admin)])
def delete_group(gid: int, db: DBSession = Depends(get_session)):
    """Delete a group with everything in it: chronicle, ratings, guestbook, lists, date, Kino."""
    g = gruppe_oder_404(db, gid)
    for model in (Abend, Info, KinoState):  # their id is the group id
        row = db.get(model, gid)
        if row is not None:
            db.delete(row)
    for s in db.exec(select(Session).where(Session.gruppe_id == gid)).all():
        s.gruppe_id = None
        db.add(s)
    db.delete(g)
    db.commit()
    return {"ok": True}


@router.put("/admin/gruppen/{gid}/mitglieder/{user_id}")
def set_member(
    gid: int,
    user_id: int,
    body: MitgliedSetzen,
    db: DBSession = Depends(get_session),
    user: User | None = Depends(current_user),
    admin: bool = Depends(is_admin),
):
    """Add someone to the group, or change their group-admin right."""
    g = _verwalten(db, gid, user, admin)
    neu = db.get(User, user_id)
    if neu is None or not neu.freigegeben:
        raise HTTPException(404, "Diesen Namen gibt es nicht (oder er ist noch nicht freigegeben).")
    m = db.exec(select(Mitglied).where(Mitglied.gruppe_id == gid, Mitglied.user_id == user_id)).first()
    m = m or Mitglied(gruppe_id=gid, user_id=user_id)
    m.ist_admin = body.admin
    db.add(m)
    db.commit()
    return _gruppe_dict(db, g)


@router.delete("/admin/gruppen/{gid}/mitglieder/{user_id}")
def remove_member(
    gid: int,
    user_id: int,
    db: DBSession = Depends(get_session),
    user: User | None = Depends(current_user),
    admin: bool = Depends(is_admin),
):
    """Take someone out of the group. Their ratings and comments there stay."""
    g = _verwalten(db, gid, user, admin)
    for m in db.exec(select(Mitglied).where(Mitglied.gruppe_id == gid, Mitglied.user_id == user_id)).all():
        db.delete(m)
    for s in db.exec(select(Session).where(Session.user_id == user_id, Session.gruppe_id == gid)).all():
        s.gruppe_id = None
        db.add(s)
    db.commit()
    return _gruppe_dict(db, g)
