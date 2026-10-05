"""The access question: the group's front door.

An admin sets a question ("Welchen Film haben wir zuerst zusammen gesehen?")
and its answer, a film. Until a browser has clicked that film, the whole API is
closed to it, apart from what the door itself needs and what authenticates on
its own (health check, MediaMTX's callback, OBS with its stream key). Without a
question set, screenmates stays open as before.

Browsers that were logged in before the door existed keep their access.
"""

from __future__ import annotations

import time
from collections import defaultdict, deque

from fastapi import APIRouter, Depends, HTTPException, Query, Request, Response
from pydantic import BaseModel, Field
from sqlmodel import Session as DBSession
from sqlmodel import col, or_, select

from .. import tmdb
from ..db import get_session
from ..models import Movie, Zugang, now
from ..serialize import iso, movie_dict
from ..session import current_session, ensure_session, require_admin

router = APIRouter(prefix="/api", tags=["zugang"])

# Paths that stay reachable without access: the door itself, the health check,
# and the Kino endpoints that authenticate on their own (MediaMTX callback,
# OBS publishing with its stream key).
OFFEN = ("/api/health", "/api/zugang", "/api/kino/mtx-auth", "/api/kino/whip", "/api/kino/sitzung/whip/")

# Wrong answers: per client IP, plus a cap for everyone together against
# guessing from many addresses. A closed door only affects browsers without
# access; everyone already inside carries on.
MAX_PRO_IP, MAX_GESAMT, FENSTER = 5, 60, 900
_fehl_ip: dict[str, deque[float]] = defaultdict(deque)
_fehl_alle: deque[float] = deque()


class Antwort(BaseModel):
    movie_id: int


class ZugangSetzen(BaseModel):
    frage: str = Field("", max_length=200)
    movie_id: int | None = None  # None opens the door again
    titel: str = Field("", max_length=300)  # shown to admins only


def _zugang(db: DBSession) -> Zugang:
    return db.get(Zugang, 1) or Zugang(id=1)


def _aktuell(q: deque[float]) -> deque[float]:
    while q and q[0] < time.monotonic() - FENSTER:
        q.popleft()
    return q


def zugang_pruefen(request: Request, db: DBSession = Depends(get_session)) -> None:
    """App-wide dependency: closes the API to browsers that haven't answered."""
    path = request.url.path
    if not path.startswith("/api/") or path.startswith(OFFEN):
        return
    if _zugang(db).movie_id is None:
        return
    sess = current_session(request, db)
    if sess and (sess.zugang or sess.user_id is not None):
        return
    raise HTTPException(423, "Bitte zuerst die Zugangsfrage beantworten.")


@router.get("/zugang")
def get_zugang(request: Request, db: DBSession = Depends(get_session)):
    z = _zugang(db)
    sess = current_session(request, db)
    offen = z.movie_id is None or bool(sess and (sess.zugang or sess.user_id is not None))
    return {"gesperrt": z.movie_id is not None, "offen": offen, "frage": z.frage if z.movie_id else ""}


@router.post("/zugang")
def answer(body: Antwort, request: Request, response: Response, db: DBSession = Depends(get_session)):
    z = _zugang(db)
    if z.movie_id is None:
        return {"offen": True}
    ip = request.client.host if request.client else "?"
    fehl = _aktuell(_fehl_ip[ip])
    if len(fehl) >= MAX_PRO_IP or len(_aktuell(_fehl_alle)) >= MAX_GESAMT:
        raise HTTPException(429, "Zu viele Fehlversuche – bitte in einer Viertelstunde nochmal.")
    if body.movie_id != z.movie_id:
        fehl.append(time.monotonic())
        _fehl_alle.append(time.monotonic())
        raise HTTPException(403, "Das ist nicht der richtige Film.")
    _fehl_ip.pop(ip, None)
    sess = ensure_session(request, response, db)
    sess.zugang = True
    db.add(sess)
    db.commit()
    return {"offen": True}


@router.get("/zugang/suche")
async def search(q: str = Query("", max_length=100), db: DBSession = Depends(get_session)):
    """Film search for the door: plain films, none of the group's flags."""
    q = q.strip()
    if not q:
        return {"results": []}
    remote = await tmdb.search(q)
    if remote is not None:
        return {"results": [movie_dict(m) for m in remote[:8]]}
    pattern = f"%{q}%"
    rows = db.exec(
        select(Movie)
        .where(or_(col(Movie.title).ilike(pattern), col(Movie.original_title).ilike(pattern)))
        .order_by(col(Movie.popularity).desc())
        .limit(8)
    ).all()
    return {"results": [movie_dict(m) for m in rows]}


@router.get("/admin/zugang", dependencies=[Depends(require_admin)])
def get_admin_zugang(db: DBSession = Depends(get_session)):
    z = _zugang(db)
    return {"frage": z.frage, "movie_id": z.movie_id, "titel": z.titel, "geaendert": iso(z.geaendert)}


@router.put("/admin/zugang", dependencies=[Depends(require_admin)])
def set_admin_zugang(body: ZugangSetzen, db: DBSession = Depends(get_session)):
    frage = " ".join(body.frage.split())
    if body.movie_id is not None and not frage:
        raise HTTPException(422, "Bitte eine Frage stellen.")
    z = _zugang(db)
    z.frage, z.movie_id, z.titel, z.geaendert = frage, body.movie_id, body.titel.strip(), now()
    db.add(z)
    db.commit()
    return get_admin_zugang(db)
