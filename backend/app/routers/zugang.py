"""The front door: screenmates is invite-only.

As soon as the server has a name, a browser only gets in with an invitation
link (`#/einladung/<token>`) or a session it already has. Group admins create
invitations for their group (see `einladungen.py`); a fresh install stays open
until the first name (its admin) exists.

Without access the whole API is closed, apart from what the door itself needs
and what authenticates on its own (health check, MediaMTX's callback, OBS with
its stream key).
"""

from __future__ import annotations

import time
from collections import defaultdict, deque
from datetime import UTC, datetime

from fastapi import APIRouter, Depends, HTTPException, Request, Response
from pydantic import BaseModel, Field
from sqlmodel import Session as DBSession
from sqlmodel import select

from ..db import get_session
from ..models import Einladung, Gruppe, User
from ..session import current_session, ensure_session

router = APIRouter(prefix="/api", tags=["zugang"])

# Paths that stay reachable without access: the door itself, the health check,
# and what authenticates on its own: the Kino's MediaMTX callback and OBS with
# its stream key, and the calendar feed with its personal token.
OFFEN = (
    "/api/health",
    "/api/zugang",
    "/api/ueber",
    "/api/kino/mtx-auth",
    "/api/kino/whip",
    "/api/kino/sitzung/whip/",
    "/api/kalender/",
)

# Wrong codes: per client IP, plus a cap for everyone together. Tokens can't be
# guessed anyway; this keeps the door quiet.
MAX_PRO_IP, MAX_GESAMT, FENSTER = 10, 100, 900
_fehl_ip: dict[str, deque[float]] = defaultdict(deque)
_fehl_alle: deque[float] = deque()


class Code(BaseModel):
    token: str = Field(min_length=8, max_length=100)


def _aware(dt: datetime) -> datetime:
    return dt if dt.tzinfo else dt.replace(tzinfo=UTC)


def gueltig(e: Einladung | None) -> bool:
    """Not withdrawn, not expired, not used up."""
    if e is None or e.widerrufen:
        return False
    if e.gueltig_bis and _aware(e.gueltig_bis) < datetime.now(UTC):
        return False
    return e.max_nutzungen is None or e.nutzungen < e.max_nutzungen


def einladung_der_sitzung(db: DBSession, sess) -> Einladung | None:
    e = db.get(Einladung, sess.einladung_id) if sess and sess.einladung_id else None
    return e if gueltig(e) else None


def _geschlossen(db: DBSession) -> bool:
    """Closed as soon as anyone has a name; a fresh install waits for its first (the admin)."""
    return db.exec(select(User.id).limit(1)).first() is not None


def _aktuell(q: deque[float]) -> deque[float]:
    while q and q[0] < time.monotonic() - FENSTER:
        q.popleft()
    return q


def zugang_pruefen(request: Request, db: DBSession = Depends(get_session)) -> None:
    """App-wide dependency: closes the API to browsers without access."""
    path = request.url.path
    if not path.startswith("/api/") or path.startswith(OFFEN):
        return
    sess = current_session(request, db)
    if sess and (sess.zugang or sess.user_id is not None):
        return
    if not _geschlossen(db):
        return
    raise HTTPException(423, "screenmates gibt es nur mit Einladung.")


@router.get("/zugang")
def get_zugang(request: Request, db: DBSession = Depends(get_session)):
    sess = current_session(request, db)
    gesperrt = _geschlossen(db)
    offen = not gesperrt or bool(sess and (sess.zugang or sess.user_id is not None))
    e = einladung_der_sitzung(db, sess)
    g = db.get(Gruppe, e.gruppe_id) if e else None
    return {
        "gesperrt": gesperrt,
        "offen": offen,
        "einladung": {"gruppe": g.name, "direkt": e.direkt} if e and g else None,
    }


@router.post("/zugang")
def enter(body: Code, request: Request, response: Response, db: DBSession = Depends(get_session)):
    """Come in with an invitation; the browser keeps it for creating (or joining with) a name."""
    ip = request.client.host if request.client else "?"
    fehl = _aktuell(_fehl_ip[ip])
    if len(fehl) >= MAX_PRO_IP or len(_aktuell(_fehl_alle)) >= MAX_GESAMT:
        raise HTTPException(429, "Zu viele Fehlversuche – bitte in einer Viertelstunde nochmal.")
    e = db.exec(select(Einladung).where(Einladung.token == body.token.strip())).first()
    if not gueltig(e):
        fehl.append(time.monotonic())
        _fehl_alle.append(time.monotonic())
        raise HTTPException(403, "Diese Einladung gilt nicht (mehr). Frag nach einem neuen Link.")
    sess = ensure_session(request, response, db)
    sess.zugang = True
    sess.einladung_id = e.id
    db.add(sess)
    db.commit()
    g = db.get(Gruppe, e.gruppe_id)
    return {"offen": True, "einladung": {"gruppe": g.name if g else "", "direkt": e.direkt}}
