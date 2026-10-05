"""The host's baton: who runs the evening, and how it changes hands.

One person per group holds the baton. The host opens the case for everyone and
runs the Kino (sends, sets the programme, ends the show, has a personal OBS key);
group admins can always do the same. The baton moves:

- **Setting a date** while nobody holds it (or the last date is over) picks it up.
- **Handing over:** the host offers it to someone, who accepts or declines
  (``UEBERGABE_FRIST``).
- **Taking over:** with no host, or a host who isn't around (no open app for
  ``ANWESEND``), anyone in the group takes it at once; so do group admins.
  Is the host there, the group votes (``ABSTIMMUNG_FRIST``): everyone present
  but the candidate may vote, the host's vote counts double and their "yes"
  decides at once. More yes than no wins; if nobody objects, silence is consent.
  Who loses a vote waits ``SPERRE`` before asking again.

Presence comes from the live poll (``melden``), which every open app sends.
"""

from __future__ import annotations

import json
import time
from datetime import UTC, datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlmodel import Session as DBSession
from sqlmodel import col, select

from ..db import get_session
from ..gruppen import aktive_gruppe, gruppen_admin, mitglieder
from ..models import Abend, Stabwechsel, User, now
from ..session import require_user

router = APIRouter(prefix="/api/gastgeber", tags=["gastgeber"])

ANWESEND = 60  # seconds without a live poll until someone counts as away
UEBERGABE_FRIST = timedelta(minutes=2)
ABSTIMMUNG_FRIST = timedelta(seconds=60)
SPERRE = timedelta(minutes=5)

_gesehen: dict[tuple[int, int], float] = {}  # (group, user) -> last live poll (monotonic)


def melden(gid: int, uid: int) -> None:
    _gesehen[(gid, uid)] = time.monotonic()


def da(gid: int, uid: int | None) -> bool:
    return uid is not None and time.monotonic() - _gesehen.get((gid, uid), -1e9) < ANWESEND


def anwesend(db: DBSession, gid: int) -> set[int]:
    return {uid for uid in mitglieder(db, gid) if da(gid, uid)}


def _utc(dt: datetime) -> datetime:
    return dt if dt.tzinfo else dt.replace(tzinfo=UTC)


def _abend(db: DBSession, gid: int) -> Abend:
    a = db.get(Abend, gid)
    if a is None:
        a = Abend(id=gid)
        db.add(a)
    return a


def gastgeber(db: DBSession, gid: int) -> int | None:
    a = db.get(Abend, gid)
    return a.gastgeber_id if a else None


def ist_gastgeber(db: DBSession, gid: int, user: User | None) -> bool:
    return user is not None and gastgeber(db, gid) == user.id


def darf_moderieren(db: DBSession, gid: int, user: User | None, admin: bool) -> bool:
    """Run the evening: open the case for everyone, run the Kino."""
    return admin or ist_gastgeber(db, gid, user)


def require_moderation(
    gid: int = Depends(aktive_gruppe),
    user: User = Depends(require_user),
    admin: bool = Depends(gruppen_admin),
    db: DBSession = Depends(get_session),
) -> None:
    if not darf_moderieren(db, gid, user, admin):
        raise HTTPException(403, "Das darf der Gastgeber des Abends (oder ein Admin der Gruppe).")


def uebergeben_an(db: DBSession, gid: int, uid: int | None) -> None:
    """Move the baton (no commit)."""
    a = _abend(db, gid)
    a.gastgeber_id = uid
    db.add(a)


def termin_gesetzt(db: DBSession, a: Abend, user: User, vorher: datetime | None) -> None:
    """Setting a date picks up a baton nobody holds, or one from an evening that is over."""
    vorbei = vorher is None or _utc(vorher) < datetime.now(UTC) - timedelta(hours=6)
    if a.gastgeber_id is None or vorbei:
        a.gastgeber_id = user.id
        db.add(a)


# --- changes of hands ---------------------------------------------------------------


def _offen(db: DBSession, gid: int) -> Stabwechsel | None:
    return db.exec(select(Stabwechsel).where(Stabwechsel.gruppe_id == gid, Stabwechsel.status == "offen")).first()


def _stimmen(w: Stabwechsel) -> dict[int, bool]:
    return {int(k): v for k, v in json.loads(w.stimmen or "{}").items()}


def _zaehlung(db: DBSession, w: Stabwechsel) -> tuple[int, int, set[int]]:
    """Yes, no (the host's vote counts double) and who may still vote."""
    host = gastgeber(db, w.gruppe_id)
    stimmen = _stimmen(w)
    ja = sum(2 if uid == host else 1 for uid, v in stimmen.items() if v)
    nein = sum(2 if uid == host else 1 for uid, v in stimmen.items() if not v)
    berechtigt = (anwesend(db, w.gruppe_id) | ({host} if host else set())) - {w.an_id}
    return ja, nein, berechtigt - set(stimmen)


def _abschliessen(db: DBSession, w: Stabwechsel, status: str) -> None:
    w.status = status
    w.erledigt_am = now()
    if status == "angenommen":
        uebergeben_an(db, w.gruppe_id, w.an_id)
    db.add(w)


def pruefen(db: DBSession, gid: int) -> None:
    """Close what's decided or over. Runs with every look at the baton (commits)."""
    w = _offen(db, gid)
    if w is None:
        return
    vorbei = _utc(w.frist) <= datetime.now(UTC)
    if w.art == "uebergabe":
        if vorbei:
            _abschliessen(db, w, "abgelaufen")
    else:
        ja, nein, fehlen = _zaehlung(db, w)
        host = gastgeber(db, gid)
        rest = sum(2 if uid == host else 1 for uid in fehlen)  # what the missing votes could still add
        if vorbei or not fehlen:
            _abschliessen(db, w, "angenommen" if ja > nein or (ja == nein == 0) else "abgelehnt")
        elif ja > nein + rest:
            _abschliessen(db, w, "angenommen")  # decided: the rest cannot turn it
        elif nein > 0 and ja + rest <= nein:
            _abschliessen(db, w, "abgelehnt")
    db.commit()


def _dict(db: DBSession, w: Stabwechsel, user: User) -> dict:
    d = {
        "id": w.id,
        "art": w.art,
        "von": w.von_id,
        "an": w.an_id,
        "frist": int(_utc(w.frist).timestamp() * 1000),
    }
    if w.art == "abstimmung":
        ja, nein, fehlen = _zaehlung(db, w)
        d |= {"ja": ja, "nein": nein, "meine": _stimmen(w).get(user.id), "darf_stimmen": user.id in fehlen}
    return d


def zustand(db: DBSession, gid: int, user: User, admin: bool) -> dict:
    """For the live poll: who hosts, whether they're around, what's going on, what I may do."""
    pruefen(db, gid)
    host = gastgeber(db, gid)
    w = _offen(db, gid)
    ich_bin_es = host == user.id
    return {
        "gastgeber": host,
        "da": da(gid, host),
        "wechsel": _dict(db, w, user) if w else None,
        "darf_moderieren": darf_moderieren(db, gid, user, admin),
        "darf_uebergeben": (ich_bin_es or admin) and w is None,
        # "sofort", "abstimmung" or None (already host, or something is going on)
        "uebernehmen": None if ich_bin_es or w else ("sofort" if admin or not da(gid, host) else "abstimmung"),
    }


@router.get("")
def get_zustand(
    gid: int = Depends(aktive_gruppe),
    user: User = Depends(require_user),
    admin: bool = Depends(gruppen_admin),
    db: DBSession = Depends(get_session),
):
    return zustand(db, gid, user, admin)


class An(BaseModel):
    an: int


@router.post("/uebergeben")
def hand_over(
    body: An,
    gid: int = Depends(aktive_gruppe),
    user: User = Depends(require_user),
    admin: bool = Depends(gruppen_admin),
    db: DBSession = Depends(get_session),
):
    pruefen(db, gid)
    if not darf_moderieren(db, gid, user, admin):
        raise HTTPException(403, "Den Stab gibt der Gastgeber weiter (oder ein Admin der Gruppe).")
    if body.an not in mitglieder(db, gid) or body.an == gastgeber(db, gid):
        raise HTTPException(422, "Den Stab kann nur jemand aus der Gruppe bekommen, der ihn noch nicht hat.")
    if _offen(db, gid):
        raise HTTPException(409, "Gerade läuft schon ein Wechsel.")
    db.add(Stabwechsel(gruppe_id=gid, art="uebergabe", von_id=user.id, an_id=body.an, frist=now() + UEBERGABE_FRIST))
    db.commit()
    return zustand(db, gid, user, admin)


@router.post("/uebernehmen")
def take_over(
    gid: int = Depends(aktive_gruppe),
    user: User = Depends(require_user),
    admin: bool = Depends(gruppen_admin),
    db: DBSession = Depends(get_session),
):
    pruefen(db, gid)
    host = gastgeber(db, gid)
    if host == user.id:
        raise HTTPException(409, "Du hast den Stab schon.")
    if _offen(db, gid):
        raise HTTPException(409, "Gerade läuft schon ein Wechsel.")
    if admin or not da(gid, host):
        # Nobody to ask: the baton was lying around (or an admin takes it).
        db.add(
            Stabwechsel(
                gruppe_id=gid,
                art="uebernahme",
                von_id=user.id,
                an_id=user.id,
                frist=now(),
                status="angenommen",
                erledigt_am=now(),
            )
        )
        uebergeben_an(db, gid, user.id)
        db.commit()
        return zustand(db, gid, user, admin)
    zuletzt = db.exec(
        select(Stabwechsel)
        .where(Stabwechsel.gruppe_id == gid, Stabwechsel.an_id == user.id, Stabwechsel.status == "abgelehnt")
        .order_by(col(Stabwechsel.id).desc())
    ).first()
    if zuletzt and zuletzt.erledigt_am and _utc(zuletzt.erledigt_am) + SPERRE > datetime.now(UTC):
        raise HTTPException(
            429, "Die letzte Abstimmung ist gerade erst gescheitert – versuch es in ein paar Minuten noch mal."
        )
    db.add(Stabwechsel(gruppe_id=gid, art="abstimmung", von_id=user.id, an_id=user.id, frist=now() + ABSTIMMUNG_FRIST))
    db.commit()
    return zustand(db, gid, user, admin)


class Antwort(BaseModel):
    ja: bool


@router.post("/wechsel/{wid}")
def answer(
    wid: int,
    body: Antwort,
    gid: int = Depends(aktive_gruppe),
    user: User = Depends(require_user),
    admin: bool = Depends(gruppen_admin),
    db: DBSession = Depends(get_session),
):
    """Accept or decline a handover; vote yes or no in a vote."""
    pruefen(db, gid)
    w = db.get(Stabwechsel, wid)
    if w is None or w.gruppe_id != gid or w.status != "offen":
        raise HTTPException(409, "Dieser Wechsel ist schon entschieden.")
    if w.art == "uebergabe":
        if user.id != w.an_id:
            raise HTTPException(403, "Annehmen kann nur, wer den Stab bekommen soll.")
        _abschliessen(db, w, "angenommen" if body.ja else "abgelehnt")
    else:
        _, _, fehlen = _zaehlung(db, w)
        if user.id not in fehlen:
            raise HTTPException(403, "Du kannst hier nicht (mehr) abstimmen.")
        stimmen = _stimmen(w) | {user.id: body.ja}
        w.stimmen = json.dumps({str(k): v for k, v in stimmen.items()})
        db.add(w)
        if body.ja and user.id == gastgeber(db, gid):
            _abschliessen(db, w, "angenommen")  # the host agrees: done
    db.commit()
    pruefen(db, gid)
    return zustand(db, gid, user, admin)


@router.delete("/wechsel/{wid}")
def withdraw(
    wid: int,
    gid: int = Depends(aktive_gruppe),
    user: User = Depends(require_user),
    admin: bool = Depends(gruppen_admin),
    db: DBSession = Depends(get_session),
):
    w = db.get(Stabwechsel, wid)
    if w is None or w.gruppe_id != gid or w.status != "offen":
        raise HTTPException(409, "Dieser Wechsel ist schon entschieden.")
    if user.id != w.von_id and not admin:
        raise HTTPException(403, "Zurückziehen kann nur, wer ihn gestartet hat.")
    _abschliessen(db, w, "zurueckgezogen")
    db.commit()
    return zustand(db, gid, user, admin)


def feed(db: DBSession, gid: int, limit: int, names: dict[int, str]) -> list[dict]:
    """Changes of hands for the activity feed."""
    out = []
    for w in db.exec(
        select(Stabwechsel)
        .where(Stabwechsel.gruppe_id == gid, Stabwechsel.status == "angenommen")
        .order_by(col(Stabwechsel.id).desc())
        .limit(limit)
    ):
        e = {
            "typ": "gastgeber",
            "at": w.erledigt_am or w.frist,
            "art": w.art,
            "wer": names.get(w.an_id),
            "von": names.get(w.von_id),
        }
        if w.art == "abstimmung":
            st = _stimmen(w)
            e["stand"] = f"{sum(st.values())}:{sum(not v for v in st.values())}"
        out.append(e)
    return out
