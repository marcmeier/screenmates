"""Talking during the show: a chat next to the Kino's screen, and reactions flying across it.

Messages are kept in the database for ``AUFBEWAHREN`` (30 days), then they age
out. Reactions are only a moment on screen: they live in memory, the last
``BEHALTEN`` of the last ``ALTER``.

Every open Kino page polls `GET /api/kino/chat?seit=<message id>&rseit=<reaction id>`
and gets what's new. A page that just opened asks without cursors and gets the
latest messages (no old reactions) plus both cursors; older messages come page
by page from `GET /api/kino/chat/aelter?vor=<id>`.

Writes don't bump the live counters (see live.STILL): a chat message must not
make every open app reload. A little rate limit keeps a stuck key quiet.
"""

from __future__ import annotations

import itertools
import time
from collections import defaultdict, deque
from dataclasses import asdict, dataclass
from datetime import timedelta

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlmodel import Session as DBSession
from sqlmodel import col, delete, select

from .. import erfolge
from ..db import get_session
from ..gruppen import aktive_gruppe
from ..models import KinoNachricht, KinoState, User, Zaehler, now
from ..serialize import iso
from ..session import require_user
from ..util import utc
from . import kino

router = APIRouter(prefix="/api/kino", tags=["kino"])

REAKTIONEN = ("😂", "😱", "❤️", "👏", "🍿", "🔥", "😴", "🤯")
AUFBEWAHREN = timedelta(days=30)  # messages age out after this
SEITE = 50  # messages per page (a freshly opened chat, or "older")
BEHALTEN = 200  # reactions kept in memory per group …
ALTER = 60  # … for at most this many seconds
LIMITS = {"text": (5, 10.0), "reaktion": (12, 5.0)}  # at most n per window (seconds), per person


@dataclass
class Eintrag:
    id: int
    typ: str  # text | reaktion
    user_id: int | None
    inhalt: str
    at: int  # ms since the epoch


_reaktionen: dict[int, deque[Eintrag]] = defaultdict(lambda: deque(maxlen=BEHALTEN))
_takt: dict[tuple[int, str], deque[float]] = defaultdict(deque)
_mitgeredet: set[tuple[int, str]] = set()  # (user, show) already recorded for the achievement
_ids = itertools.count(1)


class Nachricht(BaseModel):
    text: str = Field(min_length=1, max_length=300)


class Reaktion(BaseModel):
    emoji: str = Field(max_length=8)


def _eintrag(n: KinoNachricht) -> dict:
    return asdict(Eintrag(n.id, "text", n.user_id, n.text, int(utc(n.am).timestamp() * 1000)))


def _frische_reaktionen(gid: int) -> deque[Eintrag]:
    v = _reaktionen[gid]
    grenze = (time.time() - ALTER) * 1000
    while v and v[0].at < grenze:
        v.popleft()
    return v


def aufraeumen(db: DBSession) -> None:
    """Messages older than AUFBEWAHREN go (no commit)."""
    db.exec(delete(KinoNachricht).where(col(KinoNachricht.am) < now() - AUFBEWAHREN))


def _bremse(uid: int, typ: str) -> None:
    n, fenster = LIMITS[typ]
    q = _takt[(uid, typ)]
    while q and q[0] < time.monotonic() - fenster:
        q.popleft()
    if len(q) >= n:
        raise HTTPException(429, "Nicht so schnell – kurz durchatmen.")
    q.append(time.monotonic())


def _mitreden(db: DBSession, gid: int, user: User, zaehler: str) -> None:
    """Count it for the sidebar, and record chatting along during a show (a secret achievement)."""
    z = db.get(Zaehler, zaehler) or Zaehler(key=zaehler)
    z.wert += 1
    db.add(z)
    st = db.get(KinoState, gid)
    if st and st.gestartet and user.id in kino._viewers(gid):
        show = iso(st.gestartet)
        if (user.id, show) not in _mitgeredet:
            _mitgeredet.add((user.id, show))
            erfolge.protokoll(db, "kino_chat", user.id, show)


def _letzte(db: DBSession, gid: int) -> int:
    n = db.exec(
        select(KinoNachricht.id).where(KinoNachricht.gruppe_id == gid).order_by(col(KinoNachricht.id).desc())
    ).first()
    return n or 0


@router.get("/chat")
def chat(
    seit: int | None = Query(None, ge=0),
    rseit: int | None = Query(None, ge=0),
    gid: int = Depends(aktive_gruppe),
    _: User = Depends(require_user),
    db: DBSession = Depends(get_session),
):
    reaktionen = list(_frische_reaktionen(gid))
    if seit is None:  # just opened: the latest messages, no stale reactions
        aufraeumen(db)
        db.commit()
        neu = db.exec(
            select(KinoNachricht)
            .where(KinoNachricht.gruppe_id == gid)
            .order_by(col(KinoNachricht.id).desc())
            .limit(SEITE)
        ).all()[::-1]
        eintraege = [_eintrag(n) for n in neu]
        mehr = len(neu) == SEITE
    else:
        neu = db.exec(
            select(KinoNachricht)
            .where(KinoNachricht.gruppe_id == gid, col(KinoNachricht.id) > seit)
            .order_by(KinoNachricht.id)
        ).all()
        eintraege = [_eintrag(n) for n in neu]
        eintraege += [asdict(r) for r in reaktionen if rseit is not None and r.id > rseit]
        mehr = None
    return {
        "eintraege": eintraege,
        "letzte": max(_letzte(db, gid), seit or 0),
        "rletzte": max((r.id for r in reaktionen), default=rseit or 0),
        "mehr": mehr,  # only when just opened: are there older messages?
        "reaktionen": REAKTIONEN,
        "tage": AUFBEWAHREN.days,
    }


@router.get("/chat/aelter")
def older(
    vor: int = Query(ge=1),
    gid: int = Depends(aktive_gruppe),
    _: User = Depends(require_user),
    db: DBSession = Depends(get_session),
):
    alt = db.exec(
        select(KinoNachricht)
        .where(KinoNachricht.gruppe_id == gid, col(KinoNachricht.id) < vor)
        .order_by(col(KinoNachricht.id).desc())
        .limit(SEITE)
    ).all()[::-1]
    return {"eintraege": [_eintrag(n) for n in alt], "mehr": len(alt) == SEITE}


@router.post("/chat", status_code=201)
def say(
    body: Nachricht,
    gid: int = Depends(aktive_gruppe),
    user: User = Depends(require_user),
    db: DBSession = Depends(get_session),
):
    text = " ".join(body.text.split())
    if not text:
        raise HTTPException(422, "Leere Nachricht.")
    _bremse(user.id, "text")
    n = KinoNachricht(gruppe_id=gid, user_id=user.id, text=text)
    db.add(n)
    _mitreden(db, gid, user, "kino_chat")
    aufraeumen(db)
    db.commit()
    db.refresh(n)
    return _eintrag(n)


@router.post("/reaktion", status_code=201)
def react(
    body: Reaktion,
    gid: int = Depends(aktive_gruppe),
    user: User = Depends(require_user),
    db: DBSession = Depends(get_session),
):
    if body.emoji not in REAKTIONEN:
        raise HTTPException(422, "Diese Reaktion gibt es nicht.")
    _bremse(user.id, "reaktion")
    e = Eintrag(next(_ids), "reaktion", user.id, body.emoji, int(time.time() * 1000))
    _frische_reaktionen(gid).append(e)
    _mitreden(db, gid, user, "kino_reaktionen")
    db.commit()
    return asdict(e)
