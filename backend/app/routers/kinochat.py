"""Talking during the show: a chat next to the Kino's screen, and reactions flying across it.

Kept in memory per group, like the Kino's audience: the last ``BEHALTEN``
entries of the last ``ALTER``, gone after a restart (so is the stream).
Every open Kino page polls `GET /api/kino/chat?seit=<id>` and gets what's new;
a page that just opened asks without `seit` and gets the recent messages but
not old reactions.

Writes don't bump the live counters (see live.STILL): a chat message must not
make every open app reload. A little rate limit keeps a stuck key quiet.
"""

from __future__ import annotations

import itertools
import time
from collections import defaultdict, deque
from dataclasses import asdict, dataclass

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlmodel import Session as DBSession

from .. import erfolge
from ..db import get_session
from ..gruppen import aktive_gruppe
from ..models import KinoState, User, Zaehler
from ..serialize import iso
from ..session import require_user
from . import kino

router = APIRouter(prefix="/api/kino", tags=["kino"])

REAKTIONEN = ("😂", "😱", "❤️", "👏", "🍿", "🔥", "😴", "🤯")
BEHALTEN = 200
ALTER = 6 * 3600  # seconds
VERLAUF = 50  # messages a freshly opened page gets
LIMITS = {"text": (5, 10.0), "reaktion": (12, 5.0)}  # at most n per window (seconds), per person


@dataclass
class Eintrag:
    id: int
    typ: str  # text | reaktion
    user_id: int
    inhalt: str
    at: int  # ms since the epoch


_verlauf: dict[int, deque[Eintrag]] = defaultdict(lambda: deque(maxlen=BEHALTEN))
_takt: dict[tuple[int, str], deque[float]] = defaultdict(deque)
_mitgeredet: set[tuple[int, str]] = set()  # (user, show) already recorded for the achievement
_ids = itertools.count(1)


class Nachricht(BaseModel):
    text: str = Field(min_length=1, max_length=300)


class Reaktion(BaseModel):
    emoji: str = Field(max_length=8)


def _frisch(gid: int) -> deque[Eintrag]:
    v = _verlauf[gid]
    grenze = (time.time() - ALTER) * 1000
    while v and v[0].at < grenze:
        v.popleft()
    return v


def _bremse(uid: int, typ: str) -> None:
    n, fenster = LIMITS[typ]
    q = _takt[(uid, typ)]
    while q and q[0] < time.monotonic() - fenster:
        q.popleft()
    if len(q) >= n:
        raise HTTPException(429, "Nicht so schnell – kurz durchatmen.")
    q.append(time.monotonic())


def _zaehlen(db: DBSession, key: str) -> None:
    z = db.get(Zaehler, key) or Zaehler(key=key)
    z.wert += 1
    db.add(z)


def _neu(db: DBSession, gid: int, user: User, typ: str, inhalt: str) -> dict:
    _bremse(user.id, typ)
    e = Eintrag(next(_ids), typ, user.id, inhalt, int(time.time() * 1000))
    _frisch(gid).append(e)
    _zaehlen(db, "kino_chat" if typ == "text" else "kino_reaktionen")
    # Chatting along while watching a show: a secret achievement, once per show.
    st = db.get(KinoState, gid)
    if st and st.gestartet and user.id in kino._viewers(gid):
        show = iso(st.gestartet)
        if (user.id, show) not in _mitgeredet:
            _mitgeredet.add((user.id, show))
            erfolge.protokoll(db, "kino_chat", user.id, show)
    db.commit()
    return asdict(e)


@router.get("/chat")
def chat(seit: int | None = Query(None, ge=0), gid: int = Depends(aktive_gruppe), _: User = Depends(require_user)):
    v = list(_frisch(gid))
    # Just opened (no `seit`): the conversation so far, but no stale reactions.
    neu = [e for e in v if e.typ == "text"][-VERLAUF:] if seit is None else [e for e in v if e.id > seit]
    letzte = max((e.id for e in v), default=0)
    return {"eintraege": [asdict(e) for e in neu], "letzte": max(letzte, seit or 0), "reaktionen": REAKTIONEN}


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
    return _neu(db, gid, user, "text", text)


@router.post("/reaktion", status_code=201)
def react(
    body: Reaktion,
    gid: int = Depends(aktive_gruppe),
    user: User = Depends(require_user),
    db: DBSession = Depends(get_session),
):
    if body.emoji not in REAKTIONEN:
        raise HTTPException(422, "Diese Reaktion gibt es nicht.")
    return _neu(db, gid, user, "reaktion", body.emoji)
