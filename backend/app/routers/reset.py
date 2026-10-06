"""The danger zone: server admins clear out what testing left behind.

Each area can be emptied on its own (for every group); "neustart" empties all of
them and also removes every other name, invitation and request: screenmates as
fresh as a new install, only the admin who does it stays (with the groups, the
film catalogue, the about page and the push keys).

Before anything is deleted, the database is copied next to itself
(`backup-vor-reset-<time>.db`, the newest ``BACKUPS_BEHALTEN`` are kept), and the
request must carry the word ``BESTAETIGUNG``.
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
from ..models import (
    Abend,
    AppMeta,
    Beitrittsanfrage,
    Einladung,
    Ereignis,
    Erfolg,
    Feature,
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
from ..session import current_user, require_admin
from ..sprache import tr
from . import kinochat

router = APIRouter(prefix="/api/admin/reset", tags=["admin"], dependencies=[Depends(require_admin)])

BESTAETIGUNG = "LÖSCHEN"
BACKUPS_BEHALTEN = 5

BEREICHE = {
    "chronik": ("Chronik", "Gesehene Filme mit Bewertungen, Teilnehmenden, Gästebuch und Herzen"),
    "filmabend": ("Filmabend", "Vorschläge, Vetos, Merkliste, Kisten-Öffnungen, Termine, Umfragen, Zusagen, Gastgeber"),
    "kino": ("Kino", "Chat-Nachrichten und das Programm"),
    "wuensche": ("Wünsche & Ideen", "Alle Wünsche mit Stimmen und Anmerkungen"),
    "erfolge": ("Erfolge", "Freigeschaltete Erfolge und ihr Protokoll – was noch da ist, wird neu vergeben"),
    "statistik": (
        "Statistik & KI-Protokoll",
        "Zähler der Seitenleiste (Kino-Traffic, Chat …) und das KI-Nutzungsprotokoll",
    ),
}
NEUSTART = "neustart"


class Auftrag(BaseModel):
    bereiche: list[str]
    bestaetigung: str


def _anzahl(db: DBSession, modell, *bedingungen) -> int:
    return db.exec(select(func.count()).select_from(modell).where(*bedingungen)).one()


def zaehlen(db: DBSession, ich: User) -> dict[str, int]:
    return {
        "chronik": _anzahl(db, Watched),
        "filmabend": _anzahl(db, Suggestion)
        + _anzahl(db, Veto)
        + _anzahl(db, Wishlist)
        + _anzahl(db, Kistenoeffnung)
        + _anzahl(db, TerminVorschlag)
        + _anzahl(db, Abend, col(Abend.termin).is_not(None)),
        "kino": _anzahl(db, KinoNachricht),
        "wuensche": _anzahl(db, Feature),
        "erfolge": _anzahl(db, Erfolg),
        "statistik": _anzahl(db, KiAnfrage) + _anzahl(db, Zaehler),
        NEUSTART: _anzahl(db, User, User.id != ich.id) + _anzahl(db, Einladung),
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


def _leeren(db: DBSession, bereich: str) -> None:
    """Delete one area (no commit). Children go with their parents (ON DELETE CASCADE)."""
    if bereich == "chronik":
        db.exec(delete(Watched))
        db.exec(delete(Ereignis).where(Ereignis.typ == "treffer"))
    elif bereich == "filmabend":
        for modell in (Suggestion, Veto, Wishlist, Kistenoeffnung, TerminVorschlag, Stabwechsel):
            db.exec(delete(modell))
        for a in db.exec(select(Abend)).all():
            a.termin, a.notiz, a.gesetzt_von, a.gesetzt_am = None, "", None, None
            a.gastgeber_id, a.erinnert = None, None
            db.add(a)
        for m in db.exec(select(Mitglied)).all():
            m.dabei, m.rueckmeldung = False, ""
            db.add(m)
    elif bereich == "kino":
        db.exec(delete(KinoNachricht))
        kinochat._reaktionen.clear()
        for st in db.exec(select(KinoState)).all():
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


def _alle_anderen_weg(db: DBSession, ich: User) -> None:
    """Every other name (with all that is theirs), every invitation and request, foreign sessions."""
    for u in db.exec(select(User).where(User.id != ich.id)).all():
        bilder.loeschen(u.id, u.bild)
        db.delete(u)
    db.exec(delete(Einladung))
    db.exec(delete(Beitrittsanfrage))
    db.exec(delete(Session).where((col(Session.user_id).is_(None)) | (Session.user_id != ich.id)))
    ich.is_admin, ich.freigegeben = True, True
    db.add(ich)


@router.get("")
def overview(db: DBSession = Depends(get_session), ich: User = Depends(current_user)):
    zahlen = zaehlen(db, ich)
    return {
        "bereiche": [{"key": k, "titel": tr(t), "text": tr(x), "anzahl": zahlen[k]} for k, (t, x) in BEREICHE.items()],
        "neustart": zahlen[NEUSTART],
        "bestaetigung": tr(BESTAETIGUNG),
        "backups": [p.name for p in backups()],
    }


@router.post("")
def clear(body: Auftrag, db: DBSession = Depends(get_session), ich: User = Depends(current_user)):
    if body.bestaetigung.strip().upper() not in (BESTAETIGUNG, "DELETE"):
        raise HTTPException(422, tr("Zum Bestätigen „{wort}“ eintippen.", wort=tr(BESTAETIGUNG)))
    bereiche = list(BEREICHE) if NEUSTART in body.bereiche else body.bereiche
    unbekannt = set(bereiche) - set(BEREICHE)
    if not bereiche or unbekannt:
        raise HTTPException(422, "Unbekannter oder kein Bereich gewählt.")
    vorher = zaehlen(db, ich)
    backup = sichern()
    for b in bereiche:
        _leeren(db, b)
    if NEUSTART in body.bereiche:
        _alle_anderen_weg(db, ich)
    db.commit()
    geleert = {b: vorher[b] for b in bereiche}
    if NEUSTART in body.bereiche:
        geleert[NEUSTART] = vorher[NEUSTART]
    return {"geleert": geleert, "backup": backup}
