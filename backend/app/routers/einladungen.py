"""Invitations and requests per group.

Group admins (and server admins) create invitation links for their group:
"direkt" lets people in right away, otherwise they ask and an admin of the
group decides. A link can expire, be limited to a number of people, and be
withdrawn. Whoever already has a name joins the group with a link (or asks to).
"""

from __future__ import annotations

import secrets
from datetime import UTC, datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlmodel import Session as DBSession
from sqlmodel import col, select

from ..db import get_session
from ..gruppen import aufnehmen, gruppe_oder_404, ist_gruppen_admin
from ..models import Beitrittsanfrage, Einladung, Gruppe, Mitglied, User
from ..serialize import iso
from ..session import current_user, is_admin, require_user
from .users import ensure_not_last_admin
from .zugang import gueltig

router = APIRouter(prefix="/api", tags=["einladungen"])


class EinladungAnlegen(BaseModel):
    direkt: bool = False
    tage: int | None = Field(7, ge=1, le=365)  # None: no expiry
    max_nutzungen: int | None = Field(None, ge=1, le=100)  # None: unlimited
    notiz: str = Field("", max_length=60)


class Annehmen(BaseModel):
    token: str = Field(min_length=8, max_length=100)


class Entscheidung(BaseModel):
    annehmen: bool


def _verwalten(db: DBSession, gid: int, user: User | None, admin: bool) -> Gruppe:
    g = gruppe_oder_404(db, gid)
    if not ist_gruppen_admin(db, gid, user, admin):
        raise HTTPException(403, "Das darf nur ein Admin dieser Gruppe.")
    return g


def _dict(e: Einladung) -> dict:
    return {
        "id": e.id,
        "token": e.token,
        "direkt": e.direkt,
        "notiz": e.notiz,
        "nutzungen": e.nutzungen,
        "max_nutzungen": e.max_nutzungen,
        "gueltig_bis": iso(e.gueltig_bis),
        "erstellt_am": iso(e.erstellt_am),
        "erstellt_von": e.erstellt_von,
        "gueltig": gueltig(e),
    }


# --- links -----------------------------------------------------------------------------------


@router.get("/admin/gruppen/{gid}/einladungen")
def list_invites(
    gid: int,
    db: DBSession = Depends(get_session),
    user: User | None = Depends(current_user),
    admin: bool = Depends(is_admin),
):
    _verwalten(db, gid, user, admin)
    rows = db.exec(
        select(Einladung)
        .where(Einladung.gruppe_id == gid, col(Einladung.widerrufen).is_(False))
        .order_by(col(Einladung.erstellt_am).desc())
    ).all()
    return {"einladungen": [_dict(e) for e in rows]}


@router.post("/admin/gruppen/{gid}/einladungen", status_code=201)
def create_invite(
    gid: int,
    body: EinladungAnlegen,
    db: DBSession = Depends(get_session),
    user: User | None = Depends(current_user),
    admin: bool = Depends(is_admin),
):
    _verwalten(db, gid, user, admin)
    e = Einladung(
        token=secrets.token_urlsafe(18),
        gruppe_id=gid,
        erstellt_von=user.id if user else None,
        direkt=body.direkt,
        gueltig_bis=datetime.now(UTC) + timedelta(days=body.tage) if body.tage else None,
        max_nutzungen=body.max_nutzungen,
        notiz=body.notiz.strip(),
    )
    db.add(e)
    db.commit()
    db.refresh(e)
    return _dict(e)


@router.delete("/admin/einladungen/{eid}")
def withdraw_invite(
    eid: int,
    db: DBSession = Depends(get_session),
    user: User | None = Depends(current_user),
    admin: bool = Depends(is_admin),
):
    """Withdraw a link. Whoever came in with it keeps their name and group."""
    e = db.get(Einladung, eid)
    if e is None:
        raise HTTPException(404)
    _verwalten(db, e.gruppe_id, user, admin)
    e.widerrufen = True
    db.add(e)
    db.commit()
    return {"ok": True}


# --- joining with a name you already have ----------------------------------------------------------


@router.post("/einladungen/annehmen")
def accept(body: Annehmen, db: DBSession = Depends(get_session), user: User = Depends(require_user)):
    e = db.exec(select(Einladung).where(Einladung.token == body.token.strip())).first()
    if not gueltig(e):
        raise HTTPException(403, "Diese Einladung gilt nicht (mehr). Frag nach einem neuen Link.")
    g = db.get(Gruppe, e.gruppe_id)
    if db.exec(select(Mitglied).where(Mitglied.gruppe_id == e.gruppe_id, Mitglied.user_id == user.id)).first():
        return {"status": "mitglied", "gruppe": g.name, "gruppe_id": g.id}
    e.nutzungen += 1
    db.add(e)
    if e.direkt:
        aufnehmen(db, e.gruppe_id, user.id)
        db.commit()
        return {"status": "aufgenommen", "gruppe": g.name, "gruppe_id": g.id}
    if not db.exec(
        select(Beitrittsanfrage).where(Beitrittsanfrage.gruppe_id == e.gruppe_id, Beitrittsanfrage.user_id == user.id)
    ).first():
        db.add(Beitrittsanfrage(gruppe_id=e.gruppe_id, user_id=user.id, einladung_id=e.id))
    db.commit()
    return {"status": "angefragt", "gruppe": g.name, "gruppe_id": g.id}


# --- requests: new names and join requests ------------------------------------------------------


@router.get("/admin/gruppen/{gid}/anfragen")
def requests(
    gid: int,
    db: DBSession = Depends(get_session),
    user: User | None = Depends(current_user),
    admin: bool = Depends(is_admin),
):
    """Who wants in: new names that came with this group's link, and existing names asking to join."""
    _verwalten(db, gid, user, admin)
    neu = db.exec(
        select(User).where(col(User.freigegeben).is_(False), User.antrag_gruppe_id == gid).order_by(User.created_at)
    ).all()
    beitritt = db.exec(
        select(Beitrittsanfrage).where(Beitrittsanfrage.gruppe_id == gid).order_by(Beitrittsanfrage.am)
    ).all()
    return {
        "anfragen": [{"user_id": u.id, "name": u.name, "neu": True, "seit": iso(u.created_at)} for u in neu]
        + [{"user_id": a.user_id, "name": None, "neu": False, "seit": iso(a.am)} for a in beitritt]
    }


@router.post("/admin/gruppen/{gid}/anfragen/{user_id}")
def decide(
    gid: int,
    user_id: int,
    body: Entscheidung,
    db: DBSession = Depends(get_session),
    user: User | None = Depends(current_user),
    admin: bool = Depends(is_admin),
):
    _verwalten(db, gid, user, admin)
    u = db.get(User, user_id)
    if u is None:
        raise HTTPException(404)
    if not u.freigegeben and u.antrag_gruppe_id == gid:  # a new name that came with our link
        if body.annehmen:
            u.freigegeben = True
            db.add(u)
            aufnehmen(db, gid, u.id)
        else:
            ensure_not_last_admin(db, u)
            db.delete(u)
        db.commit()
        return {"ok": True}
    a = db.exec(
        select(Beitrittsanfrage).where(Beitrittsanfrage.gruppe_id == gid, Beitrittsanfrage.user_id == user_id)
    ).first()
    if a is None:
        raise HTTPException(404, "Keine offene Anfrage.")
    if body.annehmen:
        aufnehmen(db, gid, user_id)
    else:
        db.delete(a)
    db.commit()
    return {"ok": True}
