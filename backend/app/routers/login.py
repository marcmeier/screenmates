"""Names belong to browsers. A one-time login code connects another one.

A browser may use a name when it created the name or redeemed a login code for
it (`SessionName`). There are no passwords: a code is the only way onto a new
device. You make one on a device that already uses your name (Profile →
Settings); an admin can make one for anyone (Admin → People, or
`python -m app.cli login <name>` on the server), e.g. after a lost phone.

Codes look like `ABCD-EFGH` (40 bits, short enough to type on a TV), work once
and only for a while; only their hash is stored. Wrong codes count against the
same limit as wrong invitations (see zugang.py). A code also opens the door: the
new device needs no invitation on top.

Logging out keeps the name on the browser, so you (or someone sharing the
device) can pick it again; "forget" removes it from this browser.
"""

from __future__ import annotations

import hashlib
import secrets
from datetime import timedelta

from fastapi import APIRouter, Depends, HTTPException, Request, Response
from pydantic import BaseModel, Field
from sqlmodel import Session as DBSession
from sqlmodel import col, delete, func, select

from .. import erfolge
from ..db import get_session
from ..models import LoginCode, Session, SessionName, User, now
from ..serialize import iso, user_dict
from ..session import current_session, ensure_session, require_user
from ..util import utc
from .zugang import bremse, fehlversuch

router = APIRouter(prefix="/api/login", tags=["login"])

ALPHABET = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"  # no 0/O and 1/I to mix up
LAENGE = 8
GUELTIG_SELBST = timedelta(minutes=15)  # made on your own other device: you're right there
GUELTIG_ADMIN = timedelta(hours=24)  # made by an admin: it has to reach the person first


class Code(BaseModel):
    code: str = Field(min_length=8, max_length=100)


def _hash(code: str) -> str:
    """Case, spaces and dashes don't matter when typing a code."""
    return hashlib.sha256("".join(c for c in code.upper() if c.isalnum()).encode()).hexdigest()


def neuer_code(db: DBSession, user: User, von: User | None, gueltig: timedelta) -> dict:
    """Make a code for `user` (commits). The code itself is only in the answer."""
    db.exec(delete(LoginCode).where(col(LoginCode.used) | (col(LoginCode.valid_until) < now())))
    roh = "".join(secrets.choice(ALPHABET) for _ in range(LAENGE))
    lc = LoginCode(
        code_hash=_hash(roh), user_id=user.id, created_by=von.id if von else None, valid_until=now() + gueltig
    )
    db.add(lc)
    db.commit()
    code = f"{roh[:4]}-{roh[4:]}"
    return {"code": code, "path": f"/#/login/{code}", "valid_until": iso(lc.valid_until)}


def binden(db: DBSession, sess: Session, user_id: int) -> bool:
    """Let this browser use the name (no commit). False when it already could."""
    sess.zugang = True
    db.add(sess)
    if darf(db, sess, user_id):
        return False
    db.add(SessionName(sid=sess.sid, user_id=user_id))
    return True


def darf(db: DBSession, sess: Session | None, user_id: int) -> bool:
    if sess is None:
        return False
    return (
        db.exec(select(SessionName.id).where(SessionName.sid == sess.sid, SessionName.user_id == user_id)).first()
        is not None
    )


def namen(db: DBSession, sess: Session | None) -> list[int]:
    """The names this browser may use."""
    if sess is None:
        return []
    return sorted(db.exec(select(SessionName.user_id).where(SessionName.sid == sess.sid)).all())


def geraete(db: DBSession, user_id: int) -> int:
    return db.exec(select(func.count()).select_from(SessionName).where(SessionName.user_id == user_id)).one()


@router.post("")
def redeem(body: Code, request: Request, response: Response, db: DBSession = Depends(get_session)):
    """Use a login code: this browser gets the name (and is logged in with it)."""
    ip = bremse(request)
    lc = db.exec(select(LoginCode).where(LoginCode.code_hash == _hash(body.code))).first()
    u = db.get(User, lc.user_id) if lc else None
    if lc is None or lc.used or utc(lc.valid_until) < now() or u is None or not u.freigegeben:
        fehlversuch(ip)
        raise HTTPException(403, "Dieser Anmeldecode gilt nicht (mehr). Lass dir einen neuen geben.")
    lc.used = True
    db.add(lc)
    sess = ensure_session(request, response, db)
    neu = binden(db, sess, u.id)
    sess.user_id = u.id
    if neu and lc.created_by == u.id:
        erfolge.protokoll(db, "zweitgeraet", u.id)  # connected a device of their own
    db.commit()
    return {"ich": user_dict(u), "admin": u.is_admin}


@router.get("")
def devices(user: User = Depends(require_user), db: DBSession = Depends(get_session)):
    """On how many browsers my name is."""
    return {"geraete": geraete(db, user.id)}


@router.post("/code", status_code=201)
def own_code(user: User = Depends(require_user), db: DBSession = Depends(get_session)):
    """A code for another device of mine."""
    return neuer_code(db, user, user, GUELTIG_SELBST)


@router.post("/andere-abmelden")
def sign_out_others(
    user: User = Depends(require_user),
    sess: Session | None = Depends(current_session),
    db: DBSession = Depends(get_session),
):
    """Take my name off every other browser (a lost phone, a friend's laptop)."""
    andere = db.exec(select(SessionName).where(SessionName.user_id == user.id, SessionName.sid != sess.sid)).all()
    for b in andere:
        db.delete(b)
    for s in db.exec(select(Session).where(Session.user_id == user.id, Session.sid != sess.sid)).all():
        s.user_id = None
        db.add(s)
    db.commit()
    return {"abgemeldet": len(andere), "geraete": geraete(db, user.id)}


@router.delete("/namen/{user_id}")
def forget(user_id: int, sess: Session | None = Depends(current_session), db: DBSession = Depends(get_session)):
    """Remove a name from this browser; using it here again needs a new code."""
    if sess is not None:
        db.exec(delete(SessionName).where(SessionName.sid == sess.sid, SessionName.user_id == user_id))
        if sess.user_id == user_id:
            sess.user_id = None
            db.add(sess)
        db.commit()
    return {"namen": namen(db, sess)}
