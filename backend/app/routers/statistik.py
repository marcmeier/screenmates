"""Little facts about screenmates for the sidebar ("1.234 Herzen verteilt").

Only totals over the whole server, never anything about one person. The Kino's
traffic and lost packets come from MediaMTX: a background task adds up what its
WebRTC sessions report, because MediaMTX forgets a session once it ends.
"""

from __future__ import annotations

import asyncio
import logging
import time

import httpx
from fastapi import APIRouter, Depends
from sqlmodel import Session as DBSession
from sqlmodel import col, func, select

from ..config import settings
from ..db import engine, get_session
from ..models import (
    Erfolg,
    Gruppe,
    KiAnfrage,
    Kistenoeffnung,
    Movie,
    NoteHeart,
    Suggestion,
    User,
    Watched,
    WatchedNote,
    WatchedRating,
    Wishlist,
    Zaehler,
)
from ..sprache import aktuell, tr

router = APIRouter(prefix="/api", tags=["statistik"])
log = logging.getLogger(__name__)

INTERVALL = 15  # seconds between two looks at MediaMTX
_zuletzt: dict[str, tuple[int, int, int]] = {}  # session id -> (bytes, packets, lost) already counted
_cache: dict[str, tuple[float, list[dict]]] = {}


def _anzahl(db: DBSession, modell, *bedingungen) -> int:
    return db.exec(select(func.count()).select_from(modell).where(*bedingungen)).one()


def zaehler(db: DBSession, key: str) -> int:
    z = db.get(Zaehler, key)
    return z.wert if z else 0


def verbuchen(db: DBSession, sitzungen: list[dict]) -> None:
    """Add what MediaMTX's sessions did since the last look (sessions only ever grow)."""
    plus = {"kino_bytes": 0, "kino_pakete": 0, "kino_verloren": 0}
    offen = set()
    for s in sitzungen:
        sid = str(s.get("id") or "")
        if not sid:
            continue
        offen.add(sid)
        jetzt = (
            int(s.get("bytesReceived") or 0) + int(s.get("bytesSent") or 0),
            int(s.get("rtpPacketsReceived") or 0) + int(s.get("rtpPacketsSent") or 0),
            int(s.get("rtpPacketsLost") or 0),
        )
        vorher = _zuletzt.get(sid, (0, 0, 0))
        for key, a, b in zip(plus, jetzt, vorher, strict=True):
            plus[key] += max(0, a - b)
        _zuletzt[sid] = jetzt
    for sid in set(_zuletzt) - offen:
        del _zuletzt[sid]
    for key, wert in plus.items():
        if wert:
            z = db.get(Zaehler, key) or Zaehler(key=key)
            z.wert += wert
            db.add(z)
    db.commit()


async def kino_mitzaehlen() -> None:
    """Background task (started with the app when the Kino is set up)."""
    async with httpx.AsyncClient(timeout=5) as c:
        while True:
            try:
                r = await c.get(f"{settings.mediamtx_api_url}/v3/webrtcsessions/list", params={"itemsPerPage": 1000})
                r.raise_for_status()
                with DBSession(engine) as db:
                    verbuchen(db, r.json().get("items") or [])
            except httpx.HTTPError:
                pass  # MediaMTX down or restarting: try again later
            except Exception:
                log.exception("Counting the Kino's traffic failed")
            await asyncio.sleep(INTERVALL)


def _de(n: float, stellen: int = 0) -> str:
    """1234.5 -> "1.234,5" (German) or "1,234.5" (English)."""
    text = f"{n:,.{stellen}f}"
    if aktuell() == "en":
        return text
    return text.replace(",", "X").replace(".", ",").replace("X", ".")


def _bytes(n: int) -> str:
    for einheit, groesse in (("TB", 1e12), ("GB", 1e9), ("MB", 1e6)):
        if n >= groesse:
            return f"{_de(n / groesse, 1)} {einheit}"
    return f"{_de(n / 1e3)} kB"


def fakten(db: DBSession) -> list[dict]:
    sterne = db.exec(select(func.avg(WatchedRating.stars))).one()
    kino_bytes = zaehler(db, "kino_bytes")
    pakete, verloren = zaehler(db, "kino_pakete"), zaehler(db, "kino_verloren")
    eintraege = [  # (count, singular, plural)
        (_anzahl(db, Watched), "Film gemeinsam geschaut", "Filme gemeinsam geschaut"),
        (_anzahl(db, User, col(User.freigegeben)), "Person dabei", "Leute dabei"),
        (_anzahl(db, Gruppe), "Gruppe", "Gruppen"),
        (_anzahl(db, NoteHeart), "Herz verteilt", "Herzen verteilt"),
        (_anzahl(db, WatchedNote, WatchedNote.geloescht == ""), "Kommentar im Gästebuch", "Kommentare im Gästebuch"),
        (_anzahl(db, WatchedRating), "Bewertung abgegeben", "Bewertungen abgegeben"),
        (_anzahl(db, Wishlist), "Film auf Merklisten", "Filme auf Merklisten"),
        (_anzahl(db, Suggestion), "Film in den Kisten", "Filme in den Kisten"),
        (_anzahl(db, Kistenoeffnung), "Kiste für alle geöffnet", "Kisten für alle geöffnet"),
        (_anzahl(db, KiAnfrage, col(KiAnfrage.ok)), "Frage an die KI", "Fragen an die KI"),
        (_anzahl(db, Erfolg, col(Erfolg.entzogen).is_(False)), "Erfolg freigeschaltet", "Erfolge freigeschaltet"),
        (_anzahl(db, Movie), "Film im Katalog", "Filme im Katalog"),
    ]
    liste = [{"wert": _de(n), "text": tr(eins if n == 1 else viele)} for n, eins, viele in eintraege if n]
    if sterne:
        liste.append({"wert": f"{_de(sterne, 1)} ★", "text": tr("Durchschnitt aller Bewertungen")})
    for key, eins, viele in (
        ("kino_chat", "Nachricht im Kino-Chat", "Nachrichten im Kino-Chat"),
        ("kino_reaktionen", "Reaktion im Kino", "Reaktionen im Kino"),
    ):
        if n := zaehler(db, key):
            liste.append({"wert": _de(n), "text": tr(eins if n == 1 else viele)})
    if kino_bytes:
        liste.append({"wert": _bytes(kino_bytes), "text": tr("im Kino gestreamt")})
    if pakete:
        quote = 100 * verloren / (pakete + verloren)
        text = tr("Pakete beim Streamen verloren ({quote} %)", quote=_de(quote, 2))
        liste.append({"wert": _de(verloren), "text": text})
    return liste


@router.get("/statistik")
def statistik(db: DBSession = Depends(get_session)):
    # One cache per language: the facts are written out in words.
    alt = _cache.get(aktuell())
    if alt is None or time.monotonic() - alt[0] > 60:
        _cache[aktuell()] = alt = (time.monotonic(), fakten(db))
    return {"fakten": alt[1]}
