"""Live updates without reloading: every open app polls `GET /api/live`.

Every successful write bumps a counter: one for the whole server (names,
levels, wishes …) and one per group (evenings, ratings, hearts, lists, date …).
When an app sees a counter move, it reloads what is on screen. The same poll
carries the shared case opening (see kiste.py), so there is one request a
second or two per open app, plenty for a group of friends, and it works
through any proxy.

The counters live in memory: after a restart every app reloads once.
"""

from __future__ import annotations

import time
from collections import defaultdict

from fastapi import APIRouter, Depends, Request
from sqlmodel import Session as DBSession

from ..db import engine, get_session
from ..gruppen import _waehlen, ist_gruppen_admin, mitgliedschaften
from ..models import Session, User
from ..session import COOKIE, current_session, current_user
from . import gastgeber, kiste

router = APIRouter(prefix="/api", tags=["live"])

_stand: dict[str, int] = defaultdict(int)  # "server" and "g<id>"
_START = int(time.time())  # a restart shows as a new epoch
# Writes that change nothing anyone else has on screen. The Kino chat has its own poll.
STILL = (
    "/api/live",
    "/api/kino/da",
    "/api/kino/chat",
    "/api/kino/reaktion",
    "/api/erfolge/neu",
    "/api/zugang",
    "/api/gruppen/aktiv",
    "/api/push",
    "/api/kalender",
)


def gruppe_der_sitzung(sid: str | None) -> int | None:
    if not sid:
        return None
    with DBSession(engine) as db:
        sess = db.get(Session, sid)
        if sess is None or sess.user_id is None:
            return None
        return _waehlen(sess, mitgliedschaften(db, sess.user_id))


async def mitzaehlen(request: Request, call_next):
    """Middleware: after a successful write, bump the server's and the writer's group counter."""
    response = await call_next(request)
    path = request.url.path
    if (
        request.method in ("POST", "PUT", "PATCH", "DELETE")
        and response.status_code < 400
        and path.startswith("/api/")
        and not path.startswith(STILL)
    ):
        _stand["server"] += 1
        gid = gruppe_der_sitzung(request.cookies.get(COOKIE))
        if gid is not None:
            _stand[f"g{gid}"] += 1
    return response


@router.get("/live")
def live(
    db: DBSession = Depends(get_session),
    sess: Session | None = Depends(current_session),
    user: User | None = Depends(current_user),
):
    gid = _waehlen(sess, mitgliedschaften(db, user.id)) if user else None
    stand = f"{_START}.{_stand['server']}.{_stand[f'g{gid}'] if gid else 0}.{gid or 0}"
    antwort = {"jetzt": int(time.time() * 1000), "stand": stand, "kiste": None}
    if user and gid is not None:
        admin = ist_gruppen_admin(db, gid, user, user.is_admin)
        gastgeber.melden(gid, user.id)  # this app is open: present
        antwort["kiste"] = kiste.zustand(db, gid, user, admin)
        antwort["gastgeber"] = gastgeber.zustand(db, gid, user, admin)
    return antwort
