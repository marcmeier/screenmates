"""The bell: the latest notifications in the app (see push.glocke), and which are unread."""

from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlmodel import Session as DBSession
from sqlmodel import col, func, select

from ..db import get_session
from ..models import Benachrichtigung, User
from ..serialize import iso
from ..session import require_user

router = APIRouter(prefix="/api/glocke", tags=["glocke"])

ANZAHL = 30


def ungelesen(db: DBSession, uid: int) -> int:
    return db.exec(
        select(func.count())
        .select_from(Benachrichtigung)
        .where(Benachrichtigung.user_id == uid, col(Benachrichtigung.gelesen).is_(False))
    ).one()


@router.get("")
def bell(user: User = Depends(require_user), db: DBSession = Depends(get_session)):
    rows = db.exec(
        select(Benachrichtigung)
        .where(Benachrichtigung.user_id == user.id)
        .order_by(col(Benachrichtigung.id).desc())
        .limit(ANZAHL)
    ).all()
    return {
        "eintraege": [
            {
                "id": b.id,
                "art": b.art,
                "titel": b.titel,
                "text": b.text,
                "url": b.url,
                "am": iso(b.am),
                "neu": not b.gelesen,
            }
            for b in rows
        ],
        "ungelesen": ungelesen(db, user.id),
    }


@router.post("/gelesen")
def read_all(user: User = Depends(require_user), db: DBSession = Depends(get_session)):
    for b in db.exec(
        select(Benachrichtigung).where(Benachrichtigung.user_id == user.id, col(Benachrichtigung.gelesen).is_(False))
    ).all():
        b.gelesen = True
        db.add(b)
    db.commit()
    return {"ungelesen": 0}
