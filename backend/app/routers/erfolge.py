"""Achievements: catalogue, everyone's level and showcase, own progress, unlock pop-ups."""

from __future__ import annotations

import json

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlmodel import Session as DBSession
from sqlmodel import col, select

from .. import erfolge
from ..db import get_session
from ..models import Erfolg, User
from ..serialize import iso
from ..session import current_user, require_admin, require_user
from ..sprache import tr

router = APIRouter(prefix="/api", tags=["erfolge"])


class Vitrine(BaseModel):
    keys: list[str] = Field(max_length=3)


class Entziehen(BaseModel):
    entzogen: bool


def _def(d: erfolge.Def, sichtbar: bool, selten: float | None = None) -> dict:
    """Secret achievements stay "???" until you have them yourself."""
    verdeckt = d.geheim and not sichtbar
    return {
        "key": d.key,
        "familie": d.familie,
        "name": "???" if verdeckt else d.anzeige_name,
        "text": tr("Geheimer Erfolg – wird beim Freischalten enthüllt.") if verdeckt else d.anzeige_text,
        "emoji": "❔" if verdeckt else d.emoji,
        "stufe": d.stufe,
        "punkte": d.punkte,
        "ziel": d.ziel,
        "geheim": d.geheim,
        "kategorie": d.kategorie,
        "selten": selten,
    }


def _vitrine(u: User, meine: dict[str, Erfolg]) -> list[str]:
    try:
        keys = json.loads(u.vitrine or "[]")
    except ValueError:
        return []
    return [k for k in keys if k in meine][:3]


def _profil(u: User, meine: dict[str, Erfolg]) -> dict:
    lvl = erfolge.level(erfolge.punkte(meine))
    return {"user_id": u.id, "level": lvl, "titel": erfolge.titel(lvl), "vitrine": _vitrine(u, meine)}


@router.get("/erfolge")
def overview(db: DBSession = Depends(get_session), me: User | None = Depends(current_user)):
    erfolge.pruefen(db)
    alle = erfolge.freigeschaltet(db)
    users = db.exec(select(User).where(col(User.freigegeben)).order_by(User.name)).all()
    anzahl = max(1, len(users))
    haben: dict[str, int] = {}
    for e in alle.values():
        for k in e:
            haben[k] = haben.get(k, 0) + 1
    meine = alle.get(me.id, {}) if me else {}
    katalog = [_def(d, d.key in meine, round(100 * haben.get(d.key, 0) / anzahl)) for d in erfolge.KATALOG]
    neueste = db.exec(
        select(Erfolg)
        .where(col(Erfolg.entzogen).is_(False), col(Erfolg.rueckwirkend).is_(False))
        .order_by(col(Erfolg.am).desc())
        .limit(15)
    ).all()
    ich = None
    if me:
        p = erfolge.punkte(meine)
        lvl = erfolge.level(p)
        stand = erfolge.stand(db).get(me.id, {})
        ich = _profil(me, meine) | {
            "punkte": p,
            "level_ab": erfolge.level_ab(lvl),
            "naechstes_ab": erfolge.level_ab(lvl + 1),
            "freigeschaltet": {k: iso(e.am) for k, e in meine.items()},
            # Steam-style progress, own only: how far towards the next tier of each family.
            "fortschritt": {d.familie: stand.get(d.familie, 0) for d in erfolge.KATALOG if not d.geheim},
        }
    return {
        "katalog": katalog,
        "gruppe": [_profil(u, alle.get(u.id, {})) for u in users],
        "neueste": [
            {"user_id": e.user_id, "key": e.schluessel, "am": iso(e.am)}
            for e in neueste
            if e.schluessel in erfolge.NACH_KEY
        ],
        "ich": ich,
    }


@router.get("/erfolge/{user_id}")
def profile(user_id: int, db: DBSession = Depends(get_session), me: User | None = Depends(current_user)):
    u = db.get(User, user_id)
    if u is None or not u.freigegeben:
        raise HTTPException(404)
    erfolge.pruefen(db)
    alle = erfolge.freigeschaltet(db)
    seine = alle.get(u.id, {})
    meine = alle.get(me.id, {}) if me else {}
    return _profil(u, seine) | {
        # Secret ones the viewer doesn't have yet stay "???" even on someone else's profile.
        "freigeschaltet": [
            _def(erfolge.NACH_KEY[k], k in meine) | {"am": iso(e.am)}
            for k, e in sorted(seine.items(), key=lambda kv: kv[1].am, reverse=True)
        ],
    }


@router.post("/erfolge/neu")
def new_unlocks(db: DBSession = Depends(get_session), me: User = Depends(require_user)):
    """My unlocks not shown yet, for the pop-up. Marks them as shown."""
    erfolge.pruefen(db, sofort=True)
    rows = db.exec(
        select(Erfolg).where(Erfolg.user_id == me.id, col(Erfolg.gesehen).is_(False), col(Erfolg.entzogen).is_(False))
    ).all()
    out = []
    for e in sorted(
        rows, key=lambda e: erfolge.NACH_KEY[e.schluessel].stufe if e.schluessel in erfolge.NACH_KEY else 0
    ):
        e.gesehen = True
        db.add(e)
        if e.schluessel in erfolge.NACH_KEY:
            out.append(_def(erfolge.NACH_KEY[e.schluessel], True) | {"rueckwirkend": e.rueckwirkend})
    db.commit()
    meine = erfolge.freigeschaltet(db).get(me.id, {})
    return {"neu": out, "level": erfolge.level(erfolge.punkte(meine))}


@router.put("/erfolge/vitrine")
def set_showcase(body: Vitrine, db: DBSession = Depends(get_session), me: User = Depends(require_user)):
    meine = erfolge.freigeschaltet(db).get(me.id, {})
    keys = list(dict.fromkeys(body.keys))
    if any(k not in meine for k in keys):
        raise HTTPException(422, "Nur eigene, freigeschaltete Erfolge können in die Vitrine.")
    me.vitrine = json.dumps(keys)
    db.add(me)
    db.commit()
    return {"vitrine": keys}


@router.patch("/admin/erfolge/{user_id}/{key}", dependencies=[Depends(require_admin)])
def withdraw(user_id: int, key: str, body: Entziehen, db: DBSession = Depends(get_session)):
    """Withdraw an achievement (it stays withdrawn) or give it back."""
    if key not in erfolge.NACH_KEY or db.get(User, user_id) is None:
        raise HTTPException(404)
    e = db.exec(select(Erfolg).where(Erfolg.user_id == user_id, Erfolg.schluessel == key)).first()
    if body.entzogen:
        e = e or Erfolg(user_id=user_id, schluessel=key, gesehen=True)
        e.entzogen = True
        db.add(e)
    elif e is not None:
        db.delete(e)  # unlocks again with the next check, if still reached
    db.commit()
    erfolge.pruefen(db, sofort=True)
    return {"ok": True}
