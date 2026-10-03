"""Cookie-based sessions. Matches the original `filmabend_sid` scheme: a random
session id in a cookie, optionally bound to a chosen user."""
import secrets

from fastapi import Depends, Request, Response
from sqlmodel import Session as DBSession
from sqlmodel import select

from .config import settings
from .db import get_session
from .models import Session, User

COOKIE = settings.session_cookie
MAX_AGE = 60 * 60 * 24 * 365


def get_or_create_sid(request: Request, response: Response, db: DBSession) -> str:
    sid = request.cookies.get(COOKIE)
    if sid:
        row = db.get(Session, sid)
        if row:
            return sid
    sid = secrets.token_urlsafe(24)
    db.add(Session(sid=sid))
    db.commit()
    response.set_cookie(
        COOKIE, sid, max_age=MAX_AGE, httponly=True, samesite="lax", path="/"
    )
    return sid


def current_session(
    request: Request, response: Response, db: DBSession = Depends(get_session)
) -> Session:
    sid = get_or_create_sid(request, response, db)
    return db.get(Session, sid)


def current_user(sess: Session = Depends(current_session), db: DBSession = Depends(get_session)) -> User | None:
    if sess.user_id is None:
        return None
    return db.get(User, sess.user_id)


def set_session_user(db: DBSession, sid: str, user_id: int | None) -> None:
    row = db.get(Session, sid)
    if row:
        row.user_id = user_id
        db.add(row)
        db.commit()
