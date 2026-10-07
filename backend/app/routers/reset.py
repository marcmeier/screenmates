"""The danger zone: clearing out what testing left behind.

In the app, a server admin clears areas of the active group: its history, its
movie night (suggestions, vetoes, watchlist, case, dates, polls, replies, host)
or its Kino (chat and programme). Other groups stay as they are.

What belongs to the whole server (wishes, awards, statistics) and the fresh start
(every other name and invitation gone) are for the operator, on the command line:
`python -m app.cli reset …` (see cli.py).

Before anything is deleted, the database is copied next to itself
(`backup-vor-reset-<time>.db`, the newest ``BACKUPS_BEHALTEN`` are kept), and a
request from the app must carry the word ``BESTAETIGUNG``.
"""

from __future__ import annotations

import sqlite3
from datetime import UTC, datetime
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlmodel import Session as DBSession
from sqlmodel import col, delete, func, select

from .. import bilder
from ..db import engine, get_session
from ..gruppen import aktive_gruppe
from ..models import (
    Abend,
    AppMeta,
    Beitrittsanfrage,
    Einladung,
    Ereignis,
    Erfolg,
    Feature,
    Gruppe,
    KiAnfrage,
    KinoNachricht,
    KinoState,
    Kistenoeffnung,
    Mitglied,
    Session,
    Stabwechsel,
    Suggestion,
    TerminVorschlag,
    User,
    Veto,
    Watched,
    Wishlist,
    Zaehler,
    now,
)
from ..session import require_admin
from ..sprache import tr
from . import kinochat

router = APIRouter(prefix="/api/admin/reset", tags=["admin"], dependencies=[Depends(require_admin)])

BESTAETIGUNG = "LÖSCHEN"
BACKUPS_BEHALTEN = 5

# Per group, in the app.
GRUPPEN_BEREICHE = {
    "chronik": ("Chronik", "Gesehene Filme mit Bewertungen, Teilnehmenden, Gästebuch und Herzen"),
    "filmabend": ("Filmabend", "Vorschläge, Vetos, Merkliste, Kisten-Öffnungen, Termine, Umfragen, Zusagen, Gastgeber"),
    "kino": ("Kino", "Chat-Nachrichten und das Programm"),
}
# For the whole server, on the command line only.
SERVER_BEREICHE = ("wuensche", "erfolge", "statistik")


class Auftrag(BaseModel):
    bereiche: list[str]
    bestaetigung: str


def _anzahl(db: DBSession, modell, *bedingungen) -> int:
    return db.exec(select(func.count()).select_from(modell).where(*bedingungen)).one()


def zaehlen(db: DBSession, gid: int | None) -> dict[str, int]:
    """How much each area holds, for one group (or all of them with None)."""

    def g(modell):
        return [] if gid is None else [modell.gruppe_id == gid]

    abend = [col(Abend.termin).is_not(None)] + ([Abend.id == gid] if gid is not None else [])
    return {
        "chronik": _anzahl(db, Watched, *g(Watched)),
        "filmabend": _anzahl(db, Suggestion, *g(Suggestion))
        + _anzahl(db, Veto, *g(Veto))
        + _anzahl(db, Wishlist, *g(Wishlist))
        + _anzahl(db, Kistenoeffnung, *g(Kistenoeffnung))
        + _anzahl(db, TerminVorschlag, *g(TerminVorschlag))
        + _anzahl(db, Abend, *abend),
        "kino": _anzahl(db, KinoNachricht, *g(KinoNachricht)),
        "wuensche": _anzahl(db, Feature),
        "erfolge": _anzahl(db, Erfolg),
        "statistik": _anzahl(db, KiAnfrage) + _anzahl(db, Zaehler),
    }


def _datei() -> Path | None:
    url = engine.url
    return Path(url.database) if url.get_backend_name() == "sqlite" and url.database else None


def backups() -> list[Path]:
    db = _datei()
    return sorted(db.parent.glob("backup-vor-reset-*.db"), reverse=True) if db else []


def sichern() -> str | None:
    """Copy the database next to itself; keep the newest few of these copies."""
    db = _datei()
    if db is None or not db.exists():
        return None
    ziel = db.parent / f"backup-vor-reset-{datetime.now(UTC):%Y%m%d-%H%M%S}.db"
    with sqlite3.connect(db) as quelle, sqlite3.connect(ziel) as kopie:
        quelle.backup(kopie)
    for alt in backups()[BACKUPS_BEHALTEN:]:
        alt.unlink(missing_ok=True)
    return ziel.name


def leeren(db: DBSession, bereich: str, gid: int | None) -> None:
    """Delete one area of one group, or of all groups with None (no commit).

    Children go with their parents (ON DELETE CASCADE). Server areas ignore the group.
    """

    def g(modell):
        return [] if gid is None else [modell.gruppe_id == gid]

    if bereich == "chronik":
        ids = [str(i) for i in db.exec(select(Watched.id).where(*g(Watched))).all()]
        db.exec(delete(Watched).where(*g(Watched)))
        db.exec(delete(Ereignis).where(Ereignis.typ == "treffer", col(Ereignis.bezug).in_(ids)))
    elif bereich == "filmabend":
        for modell in (Suggestion, Veto, Wishlist, Kistenoeffnung, TerminVorschlag, Stabwechsel):
            db.exec(delete(modell).where(*g(modell)))
        for a in db.exec(select(Abend).where(*([Abend.id == gid] if gid is not None else []))).all():
            a.termin, a.notiz, a.gesetzt_von, a.gesetzt_am = None, "", None, None
            a.gastgeber_id, a.erinnert = None, None
            db.add(a)
        for m in db.exec(select(Mitglied).where(*g(Mitglied))).all():
            m.dabei, m.rueckmeldung = False, ""
            db.add(m)
    elif bereich == "kino":
        db.exec(delete(KinoNachricht).where(*g(KinoNachricht)))
        if gid is None:
            kinochat._reaktionen.clear()
        else:
            kinochat._reaktionen.pop(gid, None)
        for st in db.exec(select(KinoState).where(*([KinoState.id == gid] if gid is not None else []))).all():
            st.titel, st.movie_id = "", None
            db.add(st)
    elif bereich == "wuensche":
        db.exec(delete(Feature))
    elif bereich == "erfolge":
        db.exec(delete(Erfolg))
        db.exec(delete(Ereignis))
        # From now on everything counts afresh; the next check hands out what the data still
        # holds quietly (retroactive, no pop-ups, nothing in the feed).
        meta = db.get(AppMeta, 1) or AppMeta(id=1)
        meta.erfolge_seit, meta.erfolge_geprueft = now(), False
        db.add(meta)
    elif bereich == "statistik":
        db.exec(delete(KiAnfrage))
        db.exec(delete(Zaehler))
    else:
        raise ValueError(bereich)


def alle_anderen_weg(db: DBSession, bleibt: User) -> int:
    """Every other name (with all that is theirs), every invitation and request, foreign sessions (no commit)."""
    andere = db.exec(select(User).where(User.id != bleibt.id)).all()
    weg = len(andere) + _anzahl(db, Einladung)
    for u in andere:
        bilder.loeschen(u.id, u.bild)
        db.delete(u)
    db.exec(delete(Einladung))
    db.exec(delete(Beitrittsanfrage))
    db.exec(delete(Session).where((col(Session.user_id).is_(None)) | (Session.user_id != bleibt.id)))
    bleibt.is_admin, bleibt.freigegeben = True, True
    db.add(bleibt)
    return weg


@router.get("")
def overview(gid: int = Depends(aktive_gruppe), db: DBSession = Depends(get_session)):
    zahlen = zaehlen(db, gid)
    g = db.get(Gruppe, gid)
    return {
        "gruppe": {"id": gid, "name": g.name if g else ""},
        "bereiche": [
            {"key": k, "titel": tr(t), "text": tr(x), "anzahl": zahlen[k]} for k, (t, x) in GRUPPEN_BEREICHE.items()
        ],
        "bestaetigung": tr(BESTAETIGUNG),
        "backups": [p.name for p in backups()],
    }


@router.post("")
def clear(body: Auftrag, gid: int = Depends(aktive_gruppe), db: DBSession = Depends(get_session)):
    if body.bestaetigung.strip().upper() not in (BESTAETIGUNG, "DELETE"):
        raise HTTPException(422, tr("Zum Bestätigen „{wort}“ eintippen.", wort=tr(BESTAETIGUNG)))
    if not body.bereiche or set(body.bereiche) - set(GRUPPEN_BEREICHE):
        raise HTTPException(422, "Unbekannter oder kein Bereich gewählt.")
    vorher = zaehlen(db, gid)
    backup = sichern()
    for b in body.bereiche:
        leeren(db, b, gid)
    db.commit()
    return {"geleert": {b: vorher[b] for b in body.bereiche}, "backup": backup}
