"""User administration for admins: requests, names, rights, sessions.

Deleting a name and resetting someone's film password live in `users.py`
(DELETE /api/users/{id}, POST /api/users/{id}/schutz), next to the owner's own
calls; invitations are in `einladungen.py`.
"""

from __future__ import annotations

import re
from collections import Counter, defaultdict
from datetime import UTC, datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.exc import IntegrityError
from sqlmodel import Session as DBSession
from sqlmodel import col, select

from ..config import settings
from ..db import get_session
from ..gruppen import aufnehmen
from ..models import KiAnfrage, Session, User
from ..serialize import iso, user_dict
from ..session import require_admin
from .users import clean_name, ensure_not_last_admin, in_einzige_gruppe, new_user

router = APIRouter(prefix="/api/admin", tags=["admin"], dependencies=[Depends(require_admin)])

FARBE = re.compile(r"^#[0-9a-fA-F]{6}$")


class NeuerName(BaseModel):
    name: str = Field(min_length=1, max_length=30)


class Aendern(BaseModel):
    name: str | None = Field(None, min_length=1, max_length=30)
    color: str | None = None
    admin: bool | None = None
    freigegeben: bool | None = None  # True approves a request


def _admin_dict(u: User, sitzungen: int) -> dict:
    return user_dict(u) | {"sitzungen": sitzungen, "seit": iso(u.created_at), "antrag_gruppe_id": u.antrag_gruppe_id}


def _sitzungen(db: DBSession) -> Counter[int]:
    return Counter(uid for uid in db.exec(select(Session.user_id).where(col(Session.user_id).is_not(None))).all())


@router.get("/users")
def list_all(db: DBSession = Depends(get_session)):
    """Everyone, requests first, with how many browsers are logged in as them."""
    rows = db.exec(select(User).order_by(col(User.freigegeben), User.created_at)).all()
    n = _sitzungen(db)
    return {"users": [_admin_dict(u, n[u.id]) for u in rows]}


@router.post("/users", status_code=201)
def create(body: NeuerName, db: DBSession = Depends(get_session)):
    return _admin_dict(new_user(db, clean_name(body.name), freigegeben=True), 0)


@router.patch("/users/{user_id}")
def change(user_id: int, body: Aendern, db: DBSession = Depends(get_session)):
    u = db.get(User, user_id)
    if u is None:
        raise HTTPException(404)
    if (body.admin is False and u.is_admin) or (body.freigegeben is False and u.freigegeben):
        ensure_not_last_admin(db, u)
    if body.name is not None:
        u.name = clean_name(body.name)
    if body.color is not None:
        if not FARBE.match(body.color):
            raise HTTPException(422, "Farbe bitte als #rrggbb.")
        u.color = body.color.lower()
    if body.freigegeben is not None:
        if body.freigegeben and not u.freigegeben:
            if u.antrag_gruppe_id is not None:
                aufnehmen(db, u.antrag_gruppe_id, u.id)
            else:
                in_einzige_gruppe(db, u)
        u.freigegeben = body.freigegeben
    if body.admin is not None:
        if body.admin and not u.freigegeben:
            raise HTTPException(409, "Erst freigeben, dann zum Admin machen.")
        u.is_admin = body.admin
    db.add(u)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(409, f"„{body.name}“ gibt es schon.") from None
    db.refresh(u)
    return _admin_dict(u, _sitzungen(db)[u.id])


@router.post("/users/{user_id}/abmelden")
def logout_everywhere(user_id: int, db: DBSession = Depends(get_session)):
    """End every browser session of this person. Those browsers also lose their access."""
    if db.get(User, user_id) is None:
        raise HTTPException(404)
    rows = db.exec(select(Session).where(Session.user_id == user_id)).all()
    for s in rows:
        db.delete(s)
    db.commit()
    return {"beendet": len(rows)}


# --- KI usage ------------------------------------------------------------------


@router.get("/ki-nutzung")
def ki_nutzung(db: DBSession = Depends(get_session)):
    """How much the KI search is used, and what it cost (as far as the provider says)."""
    anfragen = db.exec(select(KiAnfrage).order_by(col(KiAnfrage.id).desc())).all()
    jetzt = datetime.now(UTC)
    heute = jetzt.replace(hour=0, minute=0, second=0, microsecond=0)

    def at(a: KiAnfrage) -> datetime:
        return a.at if a.at.tzinfo else a.at.replace(tzinfo=UTC)

    def summe(auswahl: list[KiAnfrage]) -> dict:
        kosten = [a.kosten for a in auswahl if a.kosten is not None]
        return {
            "anfragen": len(auswahl),
            "fehler": sum(not a.ok for a in auswahl),
            "tokens_ein": sum(a.tokens_ein for a in auswahl),
            "tokens_aus": sum(a.tokens_aus for a in auswahl),
            "kosten": round(sum(kosten), 6) if kosten else None,
            "ohne_kosten": len(auswahl) - len(kosten),  # requests the provider didn't price
        }

    zeitraeume = {
        "heute": [a for a in anfragen if at(a) >= heute],
        "7_tage": [a for a in anfragen if at(a) >= jetzt - timedelta(days=7)],
        "30_tage": [a for a in anfragen if at(a) >= jetzt - timedelta(days=30)],
        "gesamt": list(anfragen),
    }
    pro_person: dict[int | None, list[KiAnfrage]] = defaultdict(list)
    for a in anfragen:
        pro_person[a.user_id].append(a)
    return {
        "aktiv": settings.llm_enabled,
        "modell": settings.llm_model_name if settings.llm_enabled else None,
        "anbieter": settings.llm_backend if settings.llm_enabled else None,
        "summen": {k: summe(v) for k, v in zeitraeume.items()},
        "pro_person": sorted(
            ({"user_id": uid} | summe(v) for uid, v in pro_person.items()), key=lambda p: -p["anfragen"]
        ),
        "letzte": [
            {
                "at": iso(a.at),
                "user_id": a.user_id,
                "modell": a.modell,
                "tokens_ein": a.tokens_ein,
                "tokens_aus": a.tokens_aus,
                "kosten": a.kosten,
                "ok": a.ok,
                "fehler": a.fehler,
            }
            for a in anfragen[:20]
        ],
    }
