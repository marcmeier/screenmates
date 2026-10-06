"""The shared case opening: the host opens the movie night's case, everyone watches.

The server draws the winner (weighted like the practice spin) and stores an
opening with a seed and a start time a few seconds ahead. Every member's
browser polls `GET /api/kiste`, counts down to the same moment and builds the
very same strip from the seed, so the whole group sees the same posters race
past and stop on the same film. Who arrives late joins mid-way or sees the
result. The winner stays up as "Film des Abends" until it's watched.

May open: the evening's host (who holds the baton, see gastgeber.py) and the
group's admins. Everyone can still spin on their own (`POST /api/spin`), as practice.
"""

from __future__ import annotations

import json
import random
import secrets
from datetime import UTC, datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session as DBSession
from sqlmodel import col, select

from .. import push
from ..db import get_session
from ..gruppen import aktive_gruppe, gruppen_admin
from ..models import Kistenoeffnung, Movie, User
from ..serialize import iso, movie_dict
from ..session import require_user
from . import gastgeber
from .misc import _pool

router = APIRouter(prefix="/api/kiste", tags=["kiste"])

COUNTDOWN = timedelta(seconds=4)  # covers polling delay: everyone starts together
LAEUFT = timedelta(seconds=14)  # countdown + animation + reveal; no second opening meanwhile


def _ms(dt: datetime) -> int:
    dt = dt if dt.tzinfo else dt.replace(tzinfo=UTC)
    return int(dt.timestamp() * 1000)


def _aktuell(db: DBSession, gid: int) -> Kistenoeffnung | None:
    return db.exec(
        select(Kistenoeffnung)
        .where(Kistenoeffnung.gruppe_id == gid, col(Kistenoeffnung.erledigt).is_(False))
        .order_by(col(Kistenoeffnung.id).desc())
    ).first()


def darf_oeffnen(db: DBSession, gid: int, user: User, admin: bool) -> bool:
    """The host (whoever holds the baton) and the group's admins."""
    return gastgeber.darf_moderieren(db, gid, user, admin)


def _dict(db: DBSession, k: Kistenoeffnung) -> dict:
    eintraege = json.loads(k.pool)  # [{"id": movie id, "gewicht": n}, …] as it was when opened
    filme = {m.id: m for m in db.exec(select(Movie).where(col(Movie.id).in_([e["id"] for e in eintraege]))).all()}
    pool = [movie_dict(filme[e["id"]]) | {"gewicht": e["gewicht"]} for e in eintraege if e["id"] in filme]
    sieger = next((m for m in pool if m["id"] == k.movie_id), None)
    return {
        "id": k.id,
        "start": _ms(k.start),
        "seed": k.seed,
        "von": k.user_id,
        "pool": pool,
        "gewinner": sieger,
        "am": iso(k.start),
    }


def zustand(db: DBSession, gid: int, user: User, admin: bool) -> dict:
    """The group's current opening (or its result), also part of every live poll."""
    k = _aktuell(db, gid)
    return {"aktuell": _dict(db, k) if k else None, "darf_oeffnen": darf_oeffnen(db, gid, user, admin)}


@router.get("")
def current(
    gid: int = Depends(aktive_gruppe),
    user: User = Depends(require_user),
    admin: bool = Depends(gruppen_admin),
    db: DBSession = Depends(get_session),
):
    return {"jetzt": _ms(datetime.now(UTC))} | zustand(db, gid, user, admin)


@router.post("", status_code=201)
def open_for_everyone(
    gid: int = Depends(aktive_gruppe),
    user: User = Depends(require_user),
    admin: bool = Depends(gruppen_admin),
    db: DBSession = Depends(get_session),
):
    if not darf_oeffnen(db, gid, user, admin):
        raise HTTPException(403, "Die Kiste für alle öffnet der Gastgeber des Abends (oder ein Admin der Gruppe).")
    letzte = db.exec(
        select(Kistenoeffnung).where(Kistenoeffnung.gruppe_id == gid).order_by(col(Kistenoeffnung.id).desc())
    ).first()
    jetzt = datetime.now(UTC)
    if letzte and (letzte.start if letzte.start.tzinfo else letzte.start.replace(tzinfo=UTC)) + LAEUFT > jetzt:
        raise HTTPException(409, "Die Kiste wird gerade schon geöffnet.")
    pool = _pool(db, gid)
    if not pool:
        raise HTTPException(422, "Die Kiste ist leer – erst Filme vorschlagen.")
    sieger = random.choices(pool, weights=[m["gewicht"] for m in pool])[0]
    # Earlier results make way: there's one film of the evening.
    for alt in db.exec(
        select(Kistenoeffnung).where(Kistenoeffnung.gruppe_id == gid, col(Kistenoeffnung.erledigt).is_(False))
    ).all():
        alt.erledigt = True
        db.add(alt)
    k = Kistenoeffnung(
        gruppe_id=gid,
        user_id=user.id,
        movie_id=sieger["id"],
        seed=secrets.randbits(31),
        pool=json.dumps([{"id": m["id"], "gewicht": m["gewicht"]} for m in pool]),
        start=jetzt + COUNTDOWN,
    )
    db.add(k)
    db.commit()
    db.refresh(k)
    push.an(
        db,
        push.abwesend(gid, push.mitglieder(db, gid, ausser=user.id)),
        "kiste",
        f"🎁 Die Kiste geht auf! – {push.gruppenname(db, gid)}",
        f"{user.name} öffnet die Filmabend-Kiste für alle. Schnell rein!",
        tag=f"kiste-{gid}",
        ttl=120,
        dringend=True,
    )
    return {"jetzt": _ms(jetzt), "aktuell": _dict(db, k)}


@router.delete("/{kid}")
def dismiss(
    kid: int,
    gid: int = Depends(aktive_gruppe),
    user: User = Depends(require_user),
    admin: bool = Depends(gruppen_admin),
    db: DBSession = Depends(get_session),
):
    """Take down the film of the evening (e.g. the plans changed)."""
    k = db.get(Kistenoeffnung, kid)
    if k is None or k.gruppe_id != gid:
        raise HTTPException(404)
    if not darf_oeffnen(db, gid, user, admin):
        raise HTTPException(403, "Das darf der Gastgeber oder ein Admin der Gruppe.")
    k.erledigt = True
    db.add(k)
    db.commit()
    return {"ok": True}


def gesehen(db: DBSession, gid: int, movie_id: int) -> None:
    """Watching the film of the evening closes it (no commit)."""
    for k in db.exec(
        select(Kistenoeffnung).where(
            Kistenoeffnung.gruppe_id == gid,
            Kistenoeffnung.movie_id == movie_id,
            col(Kistenoeffnung.erledigt).is_(False),
        )
    ).all():
        k.erledigt = True
        db.add(k)
