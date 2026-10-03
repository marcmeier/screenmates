"""Cookie sessions and the authorization dependencies built on them.

There are no passwords: a browser session picks a name (optionally guarded by a
"film as PIN") and may additionally unlock host mode with the host film. Reads
never create a session row; one is created only when a browser logs in.
"""

import secrets

from fastapi import Depends, HTTPException, Request, Response
from sqlmodel import Session as DBSession

from .config import settings
from .db import get_session
from .models import Session, User

COOKIE = settings.session_cookie
MAX_AGE = 60 * 60 * 24 * 365


def current_session(request: Request, db: DBSession = Depends(get_session)) -> Session | None:
    sid = request.cookies.get(COOKIE)
    return db.get(Session, sid) if sid else None


def ensure_session(request: Request, response: Response, db: DBSession) -> Session:
    sess = current_session(request, db)
    if sess:
        return sess
    sess = Session(sid=secrets.token_urlsafe(32))
    db.add(sess)
    db.commit()
    response.set_cookie(
        COOKIE,
        sess.sid,
        max_age=MAX_AGE,
        httponly=True,
        samesite="lax",
        secure=settings.cookie_secure,
        path="/",
    )
    return sess


def current_user(sess: Session | None = Depends(current_session), db: DBSession = Depends(get_session)) -> User | None:
    if sess is None or sess.user_id is None:
        return None
    return db.get(User, sess.user_id)


def is_host(sess: Session | None = Depends(current_session)) -> bool:
    return bool(sess and sess.is_host)


def require_user(user: User | None = Depends(current_user)) -> User:
    if user is None:
        raise HTTPException(401, "Bitte zuerst einen Namen wählen.")
    return user


def require_host(host: bool = Depends(is_host)) -> None:
    if not host:
        raise HTTPException(403, "Nur im Host-Modus erlaubt.")


def require_owner_or_host(owner_id: int | None, user: User | None, host: bool) -> None:
    if host or (user is not None and owner_id == user.id):
        return
    raise HTTPException(403, "Das darf nur der Ersteller oder der Host.")
