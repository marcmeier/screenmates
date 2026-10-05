"""Groups: independent circles of friends on one server.

Names, admins, profile pictures and achievements belong to the server; the
movie night belongs to a group: who's in, suggestions, vetoes, the case, the
date, the info card, the watched chronicle with its ratings and guestbook, the
wishlist, and the Kino. Only members see a group's content.

Each browser session has an active group (`Session.gruppe_id`); every
group-scoped endpoint works on it. The single-row tables `Abend`, `Info` and
`KinoState` use the group id as their id.

Rights: server admins create groups and appoint group admins; group admins (and
server admins) add and remove members and do what used to be admin-only on the
movie night (clear suggestions, reset attendance, edit the info card, run the
Kino …).
"""

from __future__ import annotations

from contextvars import ContextVar

from fastapi import Depends, HTTPException, Request
from sqlmodel import Session as DBSession
from sqlmodel import select

from .db import engine, get_session
from .models import Gruppe, Mitglied, Session, User
from .session import COOKIE, current_session, is_admin, require_user

# The active group of the current request, for code that only *marks* things for
# the group (catalogue flags, "our subscriptions") and works without one too.
_aktuell: ContextVar[int | None] = ContextVar("gruppe", default=None)


def mitgliedschaften(db: DBSession, user_id: int) -> dict[int, Mitglied]:
    return {m.gruppe_id: m for m in db.exec(select(Mitglied).where(Mitglied.user_id == user_id)).all()}


def _waehlen(sess: Session | None, ms: dict[int, Mitglied]) -> int | None:
    if not ms:
        return None
    return sess.gruppe_id if sess and sess.gruppe_id in ms else min(ms)


def aktive_gruppe(
    sess: Session | None = Depends(current_session),
    user: User = Depends(require_user),
    db: DBSession = Depends(get_session),
) -> int:
    """The group this request works on; the user must be a member of one."""
    gid = _waehlen(sess, mitgliedschaften(db, user.id))
    if gid is None:
        raise HTTPException(409, "Du bist noch in keiner Gruppe – ein Admin nimmt dich auf.")
    return gid


async def kontext(request: Request) -> None:
    """App-wide: remember the active group (or None) for catalogue flags and the like.

    Async on purpose: a context variable set here is visible to the endpoint,
    also when that runs in the thread pool.
    """
    gid = None
    sid = request.cookies.get(COOKIE)
    if sid:
        with DBSession(engine) as db:
            sess = db.get(Session, sid)
            if sess and sess.user_id is not None:
                gid = _waehlen(sess, mitgliedschaften(db, sess.user_id))
    _aktuell.set(gid)


def aktuelle_gruppe() -> int | None:
    return _aktuell.get()


def mitglieder(db: DBSession, gid: int | None) -> set[int]:
    if gid is None:
        return set()
    return set(db.exec(select(Mitglied.user_id).where(Mitglied.gruppe_id == gid)).all())


def ist_gruppen_admin(db: DBSession, gid: int, user: User | None, server_admin: bool) -> bool:
    if server_admin:
        return True
    if user is None:
        return False
    m = db.exec(select(Mitglied).where(Mitglied.gruppe_id == gid, Mitglied.user_id == user.id)).first()
    return bool(m and m.ist_admin)


def gruppen_admin(
    gid: int = Depends(aktive_gruppe),
    user: User = Depends(require_user),
    admin: bool = Depends(is_admin),
    db: DBSession = Depends(get_session),
) -> bool:
    """Admin rights in the active group (group admin, or server admin who is a member)."""
    return ist_gruppen_admin(db, gid, user, admin)


def require_gruppen_admin(ok: bool = Depends(gruppen_admin)) -> None:
    if not ok:
        raise HTTPException(403, "Das darf nur ein Admin dieser Gruppe.")


def require_owner_or_gruppen_admin(owner_id: int | None, user: User | None, gruppen_admin: bool) -> None:
    if gruppen_admin or (user is not None and owner_id == user.id):
        return
    raise HTTPException(403, "Das darf nur der Ersteller oder ein Admin der Gruppe.")


def gruppe_oder_404(db: DBSession, gid: int) -> Gruppe:
    g = db.get(Gruppe, gid)
    if g is None:
        raise HTTPException(404, "Diese Gruppe gibt es nicht.")
    return g
