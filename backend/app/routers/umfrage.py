"""Finding a date together: propose a few, everyone answers yes / maybe / no, one gets picked.

The group's poll is simply its open proposals (dates still ahead). Anyone with a
name proposes (up to MAX_VORSCHLAEGE at a time) and answers. Picking one sets
the group's date like `PUT /api/termin`, turns everyone's answer for that date
into their reply for the evening (yes = in, maybe, no) and closes the poll.
Picking may the host, a group admin, whoever started the poll, or anyone
while nobody holds the host's baton.
"""

from __future__ import annotations

from collections import defaultdict
from datetime import UTC, datetime, timedelta
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlmodel import Session as DBSession
from sqlmodel import col, select

from .. import erfolge, push
from ..db import get_session
from ..gruppen import aktive_gruppe, gruppen_admin
from ..models import Mitglied, TerminStimme, TerminVorschlag, User
from ..serialize import iso
from ..session import require_user
from ..sprache import tr
from ..util import termin_text, utc
from ..zeitzone import zone
from . import gastgeber
from .abend import _termin_dict, pruefe_termin, termin_setzen
from .users import rueckmelden

router = APIRouter(prefix="/api/termin/umfrage", tags=["umfrage"])

MAX_VORSCHLAEGE = 8
Antwort = Literal["ja", "vielleicht", "nein"]


class Vorschlag(BaseModel):
    termin: datetime
    notiz: str = Field("", max_length=80)


class Stimme(BaseModel):
    antwort: Antwort | None = None  # None takes the answer back


def offene(db: DBSession, gid: int) -> list[TerminVorschlag]:
    """The poll: proposals of this group that are still ahead, earliest first."""
    grenze = datetime.now(UTC)
    alle = db.exec(select(TerminVorschlag).where(TerminVorschlag.gruppe_id == gid)).all()
    return sorted((v for v in alle if utc(v.termin) > grenze), key=lambda v: (utc(v.termin), v.id))


def _starter(vs: list[TerminVorschlag]) -> int | None:
    return min(vs, key=lambda v: (utc(v.am), v.id)).von_id if vs else None


def darf_festlegen(db: DBSession, gid: int, user: User, admin: bool, vs: list[TerminVorschlag]) -> bool:
    return admin or gastgeber.gastgeber(db, gid) in (None, user.id) or _starter(vs) == user.id


def _zustand(db: DBSession, gid: int, user: User, admin: bool) -> dict:
    vs = offene(db, gid)
    stimmen: dict[int, dict[int, str]] = defaultdict(dict)
    if vs:
        for s in db.exec(select(TerminStimme).where(col(TerminStimme.vorschlag_id).in_([v.id for v in vs]))).all():
            stimmen[s.vorschlag_id][s.user_id] = s.antwort
    erlaubt = darf_festlegen(db, gid, user, admin, vs)
    vorschlaege = []
    for v in vs:
        st = stimmen[v.id]
        vorschlaege.append(
            {
                "id": v.id,
                "termin": iso(v.termin),
                "notiz": v.notiz,
                "von": v.von_id,
                "stimmen": {str(uid): a for uid, a in st.items()},
                "ja": sum(a == "ja" for a in st.values()),
                "vielleicht": sum(a == "vielleicht" for a in st.values()),
                "nein": sum(a == "nein" for a in st.values()),
                "meine": st.get(user.id),
                "darf_loeschen": erlaubt or v.von_id == user.id,
            }
        )
    # The favourite: most yes, then most maybe; on a tie the earliest (max keeps the first).
    beste = max(vorschlaege, key=lambda v: (v["ja"], v["vielleicht"]), default=None)
    return {
        "vorschlaege": vorschlaege,
        "favorit": beste["id"] if beste and beste["ja"] else None,
        "darf_festlegen": erlaubt,
        "max": MAX_VORSCHLAEGE,
    }


@router.get("")
def get_umfrage(
    gid: int = Depends(aktive_gruppe),
    user: User = Depends(require_user),
    admin: bool = Depends(gruppen_admin),
    db: DBSession = Depends(get_session),
):
    return _zustand(db, gid, user, admin)


@router.post("", status_code=201)
def propose(
    body: Vorschlag,
    gid: int = Depends(aktive_gruppe),
    user: User = Depends(require_user),
    admin: bool = Depends(gruppen_admin),
    db: DBSession = Depends(get_session),
):
    termin = pruefe_termin(body.termin, vergangenes=timedelta(0))
    vs = offene(db, gid)
    if len(vs) >= MAX_VORSCHLAEGE:
        raise HTTPException(409, tr("Mehr als {n} Vorschläge auf einmal werden unübersichtlich.", n=MAX_VORSCHLAEGE))
    if any(utc(v.termin) == termin for v in vs):
        raise HTTPException(409, "Diesen Termin gibt es schon in der Umfrage.")
    v = TerminVorschlag(gruppe_id=gid, termin=termin, notiz=body.notiz.strip(), von_id=user.id)
    db.add(v)
    db.flush()
    db.add(TerminStimme(vorschlag_id=v.id, user_id=user.id, antwort="ja"))  # who proposes it can make it
    db.commit()
    push.an(
        db,
        push.mitglieder(db, gid, ausser=user.id),
        "umfrage",
        "🗳️ Wann habt ihr Zeit? – {gruppe}",
        "{name} schlägt {wann} vor. Stimm ab!",
        tag=f"umfrage-{gid}",
        werte={"gruppe": push.gruppenname(db, gid), "name": user.name, "wann": lambda: termin_text(termin)},
    )
    return _zustand(db, gid, user, admin)


def _vorschlag(db: DBSession, vid: int, gid: int) -> TerminVorschlag:
    v = db.get(TerminVorschlag, vid)
    if v is None or v.gruppe_id != gid or utc(v.termin) <= datetime.now(UTC):
        raise HTTPException(404, "Diesen Vorschlag gibt es nicht (mehr).")
    return v


@router.put("/{vid}/stimme")
def vote(
    vid: int,
    body: Stimme,
    gid: int = Depends(aktive_gruppe),
    user: User = Depends(require_user),
    admin: bool = Depends(gruppen_admin),
    db: DBSession = Depends(get_session),
):
    _vorschlag(db, vid, gid)
    s = db.exec(select(TerminStimme).where(TerminStimme.vorschlag_id == vid, TerminStimme.user_id == user.id)).first()
    if body.antwort is None:
        if s:
            db.delete(s)
    else:
        s = s or TerminStimme(vorschlag_id=vid, user_id=user.id, antwort=body.antwort)
        s.antwort = body.antwort
        db.add(s)
    db.commit()
    return _zustand(db, gid, user, admin)


@router.delete("/{vid}")
def withdraw(
    vid: int,
    gid: int = Depends(aktive_gruppe),
    user: User = Depends(require_user),
    admin: bool = Depends(gruppen_admin),
    db: DBSession = Depends(get_session),
):
    v = _vorschlag(db, vid, gid)
    if v.von_id != user.id and not darf_festlegen(db, gid, user, admin, offene(db, gid)):
        raise HTTPException(403, "Den Vorschlag nimmt zurück, wer ihn gemacht hat (oder wer festlegen darf).")
    db.delete(v)
    db.commit()
    return _zustand(db, gid, user, admin)


def _schliessen(db: DBSession, gid: int) -> None:
    """Drop the whole poll, also proposals that are already over (no commit)."""
    for v in db.exec(select(TerminVorschlag).where(TerminVorschlag.gruppe_id == gid)).all():
        db.delete(v)


@router.delete("")
def close(
    gid: int = Depends(aktive_gruppe),
    user: User = Depends(require_user),
    admin: bool = Depends(gruppen_admin),
    db: DBSession = Depends(get_session),
):
    if not darf_festlegen(db, gid, user, admin, offene(db, gid)):
        raise HTTPException(403, "Die Umfrage beendet, wer sie gestartet hat, der Gastgeber oder ein Admin.")
    _schliessen(db, gid)
    db.commit()
    return _zustand(db, gid, user, admin)


@router.post("/{vid}/festlegen")
def pick(
    vid: int,
    gid: int = Depends(aktive_gruppe),
    user: User = Depends(require_user),
    admin: bool = Depends(gruppen_admin),
    db: DBSession = Depends(get_session),
):
    """This one it is: set the date, carry everyone's answer over, close the poll."""
    v = _vorschlag(db, vid, gid)
    if not darf_festlegen(db, gid, user, admin, offene(db, gid)):
        raise HTTPException(403, "Festlegen darf, wer die Umfrage gestartet hat, der Gastgeber oder ein Admin.")
    termin, notiz, von = utc(v.termin), v.notiz, v.von_id
    antworten = {
        s.user_id: s.antwort for s in db.exec(select(TerminStimme).where(TerminStimme.vorschlag_id == vid)).all()
    }
    a = termin_setzen(db, gid, user, termin, notiz)  # commits (and clears replies to an evening that is over)
    for m in db.exec(select(Mitglied).where(Mitglied.gruppe_id == gid)).all():
        if m.user_id in antworten:
            rueckmelden(db, m, antworten[m.user_id], termin)
    # The proposer found the date (counts once the evening took place).
    erfolge.protokoll(db, "umfrage", von, termin.astimezone(zone()).date().isoformat())
    _schliessen(db, gid)
    db.commit()
    return {"termin": _termin_dict(a, db), "umfrage": _zustand(db, gid, user, admin)}


def feed(db: DBSession, gid: int, limit: int, names: dict[int, str]) -> list[dict]:
    """Open proposals for the activity feed."""
    return [
        {"typ": "umfrage", "at": v.am, "wer": names.get(v.von_id), "termin": iso(v.termin)}
        for v in sorted(offene(db, gid), key=lambda v: utc(v.am), reverse=True)[:limit]
    ]
