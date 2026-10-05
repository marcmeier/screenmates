"""Cookie sessions and the authorization dependencies built on them.

There are no passwords: a browser first answers the group's access question
(see `routers/zugang.py`), then picks a name (optionally guarded by a "film as
PIN"). Administration is a right of individual people (`User.is_admin`), not of
a browser. Reads never create a session row; one is created only when a browser
answers the access question or logs in.
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
    u = db.get(User, sess.user_id)
    # A name waiting for approval can't be used, even if a session still points at it.
    return u if u is not None and u.freigegeben else None


def is_admin(user: User | None = Depends(current_user)) -> bool:
    return bool(user and user.is_admin)


def require_user(user: User | None = Depends(current_user)) -> User:
    if user is None:
        raise HTTPException(401, "Bitte zuerst einen Namen wählen.")
    return user


def require_admin(admin: bool = Depends(is_admin)) -> None:
    if not admin:
        raise HTTPException(403, "Das darf nur ein Admin.")


def require_owner_or_admin(owner_id: int | None, user: User | None, admin: bool) -> None:
    if admin or (user is not None and owner_id == user.id):
        return
    raise HTTPException(403, "Das darf nur der Ersteller oder ein Admin.")
