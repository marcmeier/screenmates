"""Web Push: notifications on phones and computers, also while screenmates is closed.

A browser that allows notifications hands us a push subscription (an endpoint at
its vendor's push service plus two keys, see routers/push.py). To notify
someone, the server encrypts a small JSON message for each of their devices and
posts it to the endpoint, signed with the server's VAPID key (RFC 8291/8292,
done by pywebpush). The service worker (`frontend/public/sw.js`) shows it.

- The VAPID key pair is made on first use and kept in the database, so there's
  nothing to configure. `PUSH_CONTACT` (or `PUBLIC_URL`) is the contact push services may use.
- Everyone chooses which kinds they want (`ARTEN`); a kind not chosen is on.
- Sending runs in a small thread pool: a slow push service never holds up a
  request. Devices the push service no longer knows (404/410) are dropped.
- Nobody is notified about what they did themselves; for things that happen
  live (the case, the Kino, a baton offer) only people without an open app are.

The reminders on the day of the movie night come from a background task
(`erinnern`): ``ERINNERUNG`` before the date for everyone who hasn't said no, and
just before the start for whoever said yes or maybe but has no screenmates open.
"""

from __future__ import annotations

import asyncio
import base64
import contextlib
import json
import logging
from collections.abc import Iterable
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from urllib.parse import urlsplit

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import ec
from sqlmodel import Session as DBSession
from sqlmodel import col, delete, select

from . import sprache
from .config import settings
from .db import engine
from .models import Abend, AppMeta, Benachrichtigung, Gruppe, Mitglied, PushAbo, User, now
from .util import utc
from .zeitzone import zone

log = logging.getLogger(__name__)

# The kinds of notifications, in the order the settings page lists them.
ARTEN = {
    "termin": "Ein Termin wird festgelegt oder verschoben",
    "umfrage": "Jemand schlägt Termine zur Abstimmung vor",
    "erinnerung": "Erinnerungen am Tag des Filmabends (vorher und kurz vor Beginn)",
    "kiste": "Die Kiste wird für alle geöffnet",
    "kino": "Das Kino geht live",
    "stab": "Dir wird der Gastgeber-Stab angeboten",
    "antwort": "Jemand antwortet auf deinen Kommentar",
    "bewerten": "Am Tag danach: den Film vom Vorabend bewerten",
}
GLOCKE_TAGE = 30
ERINNERUNG = timedelta(hours=3)
PRUEFEN_ALLE = 60  # seconds between two looks for due reminders

_pool = ThreadPoolExecutor(max_workers=4, thread_name_prefix="push")


@dataclass
class Zustellung:
    """One message to one device."""

    endpoint: str
    p256dh: str
    auth: str
    daten: dict
    ttl: int = 3600
    dringend: bool = False
    schluessel: str = field(default="", repr=False)


# --- keys ------------------------------------------------------------------------


def _neuer_schluessel() -> str:
    key = ec.generate_private_key(ec.SECP256R1())
    return key.private_bytes(
        serialization.Encoding.PEM, serialization.PrivateFormat.PKCS8, serialization.NoEncryption()
    ).decode()


def privater_schluessel(db: DBSession) -> str:
    """The server's VAPID private key (PEM); made and stored on first use."""
    meta = db.get(AppMeta, 1) or AppMeta(id=1)
    if not meta.vapid:
        meta.vapid = _neuer_schluessel()
        db.add(meta)
        db.commit()
    return meta.vapid


def oeffentlicher_schluessel(db: DBSession) -> str:
    """The public key as browsers want it (applicationServerKey): base64url, uncompressed point."""
    key = serialization.load_pem_private_key(privater_schluessel(db).encode(), password=None)
    raw = key.public_key().public_bytes(serialization.Encoding.X962, serialization.PublicFormat.UncompressedPoint)
    return base64.urlsafe_b64encode(raw).rstrip(b"=").decode()


def kontakt() -> str:
    """PUSH_CONTACT (else PUBLIC_URL) as the push services want it: mailto:… or an https: origin.

    py_vapid refuses anything else (with a misleading "Missing 'sub'"), so a URL
    like https://github.com/user/repo is cut down to https://github.com. Without
    either setting, the project's address stands in.
    """
    k = (settings.push_contact or settings.public_url or "https://github.com/marcmeier/screenmates").strip()
    if k.lower().startswith("https://"):
        return f"https://{urlsplit(k).hostname}"
    return k


# --- who wants what ------------------------------------------------------------------


def wahl(user: User) -> dict[str, bool]:
    gespeichert = json.loads(user.push or "{}")
    return {art: bool(gespeichert.get(art, True)) for art in ARTEN}


def abwesend(gid: int, uids: Iterable[int]) -> set[int]:
    """Who of them has no screenmates open right now (for things that happen live)."""
    from .routers import gastgeber

    return {uid for uid in uids if not gastgeber.da(gid, uid)}


def mitglieder(db: DBSession, gid: int, ausser: int | None = None) -> set[int]:
    uids = set(db.exec(select(Mitglied.user_id).where(Mitglied.gruppe_id == gid)).all())
    return uids - {ausser}


def gruppenname(db: DBSession, gid: int) -> str:
    g = db.get(Gruppe, gid)
    return g.name if g else ""


# --- sending ---------------------------------------------------------------------------


def an(
    db: DBSession,
    uids: Iterable[int | None],
    art: str,
    titel: str,
    text: str,
    *,
    url: str = "/#/abend",
    tag: str = "",
    ttl: int = 3600,
    dringend: bool = False,
    warten: bool = False,
    werte: dict | None = None,
) -> int:
    """Notify these people on all their devices, if they want this kind. Returns the number of devices.

    `art` is a key of ARTEN, or "test" (always on). Sending happens in the background;
    with `warten` right here, and the number is how many devices really got it.
    `titel` and `text` are German templates; everyone gets them in their own language,
    with `werte` filled in (a callable value is worked out in that language, e.g. a date).
    """
    uids = {u for u in uids if u is not None}
    if not uids:
        return 0
    leute = db.exec(select(User).where(col(User.id).in_(uids), col(User.freigegeben))).all()
    texte = {}
    for s in {sprache.von(u) for u in leute}:
        with sprache.als(s):
            w = {k: v() if callable(v) else v for k, v in (werte or {}).items()}
            texte[s] = (sprache.tr(titel, **w), sprache.tr(text, **w))
    if art != "test":
        for u in leute:
            glocke(db, [u.id], art, *texte[sprache.von(u)], url, aufraeumen=False)
        glocke(db, [], art, "", "", url)
    wollen = {u.id: u for u in leute if art == "test" or wahl(u).get(art, False)}
    if not wollen:
        return 0
    abos = db.exec(select(PushAbo).where(col(PushAbo.user_id).in_(wollen))).all()
    if not abos:
        return 0
    schluessel = privater_schluessel(db)

    def daten(uid: int) -> dict:
        t, x = texte[sprache.von(wollen[uid])]
        return {"titel": t, "text": x, "url": url, "tag": tag or art}

    zustellungen = [Zustellung(a.endpoint, a.p256dh, a.auth, daten(a.user_id), ttl, dringend, schluessel) for a in abos]
    if warten:
        return sum(zustellen(z) for z in zustellungen)
    for z in zustellungen:
        abschicken(z)
    return len(zustellungen)


def glocke(
    db: DBSession, uids: list[int], art: str, titel: str, text: str, url: str, *, aufraeumen: bool = True
) -> None:
    """The same news for the bell in the app: everyone gets it there, push or not (commits when tidying up)."""
    for uid in uids:
        db.add(Benachrichtigung(user_id=uid, art=art, titel=titel, text=text, url=url))
    if aufraeumen:
        db.exec(delete(Benachrichtigung).where(col(Benachrichtigung.am) < now() - timedelta(days=GLOCKE_TAGE)))
        db.commit()


def abschicken(z: Zustellung) -> None:
    """Hand a message to the thread pool (tests replace this)."""
    _pool.submit(zustellen, z)


def zustellen(z: Zustellung) -> bool:
    """Deliver one message; False when the push service refused it (or wasn't reachable)."""
    from py_vapid import Vapid
    from pywebpush import WebPushException, webpush

    try:
        webpush(
            {"endpoint": z.endpoint, "keys": {"p256dh": z.p256dh, "auth": z.auth}},
            json.dumps(z.daten, ensure_ascii=False),
            vapid_private_key=Vapid.from_pem(z.schluessel.encode()),
            vapid_claims={"sub": kontakt()},  # a fresh dict: pywebpush adds the audience to it
            ttl=z.ttl,
            timeout=10,
            headers={"Urgency": "high" if z.dringend else "normal"},
        )
    except WebPushException as e:
        status = e.response.status_code if e.response is not None else None
        if status in (404, 410):  # the browser unsubscribed or the subscription expired
            vergessen(z.endpoint)
        else:
            log.warning("Push an %s… fehlgeschlagen: %s", z.endpoint[:40], status or e)
        return False
    except Exception:
        log.exception("Push an %s… fehlgeschlagen", z.endpoint[:40])
        return False
    return True


def vergessen(endpoint: str) -> None:
    with DBSession(engine) as db:
        for a in db.exec(select(PushAbo).where(PushAbo.endpoint == endpoint)).all():
            db.delete(a)
        db.commit()


# --- the reminder on the day ------------------------------------------------------------


def faellige_erinnerungen(db: DBSession, jetzt: datetime | None = None) -> int:
    """Remind everyone who hasn't said no of every movie night starting within ERINNERUNG (commits)."""
    jetzt = jetzt or datetime.now(UTC)
    n = 0
    for a in db.exec(select(Abend).where(col(Abend.termin).is_not(None))).all():
        termin = utc(a.termin)
        if not jetzt < termin <= jetzt + ERINNERUNG or (a.erinnert and utc(a.erinnert) == termin):
            continue
        a.erinnert = termin
        db.add(a)
        db.commit()
        nein = set(
            db.exec(select(Mitglied.user_id).where(Mitglied.gruppe_id == a.id, Mitglied.rueckmeldung == "nein")).all()
        )
        n += an(
            db,
            mitglieder(db, a.id) - nein,
            "erinnerung",
            "🍿 Heute ist Filmabend – {gruppe}",
            "Um {zeit} Uhr{wo} – bist du dabei?",
            tag=f"erinnerung-{a.id}",
            ttl=int(ERINNERUNG.total_seconds()),
            werte={
                "gruppe": gruppenname(db, a.id),
                "zeit": f"{termin.astimezone(zone()):%H:%M}",
                "wo": f" · {a.notiz}" if a.notiz else "",
            },
        )
    return n


LOS_VORHER = timedelta(minutes=5)  # "it's starting" this long before the date …
LOS_NACHHER = timedelta(minutes=30)  # … and not later than this after it (server was down)


def los_meldungen(db: DBSession, jetzt: datetime | None = None) -> int:
    """Just before the start: whoever said yes or maybe and has no screenmates open hears it's on (commits)."""
    from .models import Ereignis

    jetzt = jetzt or datetime.now(UTC)
    n = 0
    for a in db.exec(select(Abend).where(col(Abend.termin).is_not(None))).all():
        termin = utc(a.termin)
        if not termin - LOS_VORHER <= jetzt <= termin + LOS_NACHHER:
            continue
        bezug = f"{a.id}@{termin.isoformat()}"
        if db.exec(select(Ereignis).where(Ereignis.typ == "los_gemeldet", Ereignis.bezug == bezug)).first():
            continue
        db.add(Ereignis(typ="los_gemeldet", bezug=bezug))
        db.commit()
        kommen = set(
            db.exec(
                select(Mitglied.user_id).where(
                    Mitglied.gruppe_id == a.id,
                    col(Mitglied.dabei) | (Mitglied.rueckmeldung == "vielleicht"),
                )
            ).all()
        )
        n += an(
            db,
            abwesend(a.id, kommen),
            "erinnerung",
            "🎬 Gleich geht’s los – {gruppe}",
            "Der Filmabend beginnt um {zeit} Uhr{wo}. Komm dazu!",
            url="/#/abend",
            tag=f"los-{a.id}",
            ttl=int(LOS_NACHHER.total_seconds()),
            dringend=True,
            werte={
                "gruppe": gruppenname(db, a.id),
                "zeit": f"{termin.astimezone(zone()):%H:%M}",
                "wo": f" · {a.notiz}" if a.notiz else "",
            },
        )
    return n


BEWERTEN_AB, BEWERTEN_BIS = 10, 20  # hours (the group's time) for "how was it?"


def bewertungs_erinnerungen(db: DBSession, jetzt: datetime | None = None) -> int:
    """The day after: ask everyone who watched along but gave no stars yet, once per film (commits)."""
    from .models import Ereignis, Movie, Watched, WatchedParticipant, WatchedRating

    jetzt = jetzt or datetime.now(UTC)
    if not BEWERTEN_AB <= jetzt.astimezone(zone()).hour < BEWERTEN_BIS:
        return 0
    n = 0
    for w in db.exec(select(Watched).where(col(Watched.hidden).is_(False))).all():
        if not jetzt - timedelta(hours=36) <= utc(w.watched_at) <= jetzt - timedelta(hours=8):
            continue
        dabei = set(db.exec(select(WatchedParticipant.user_id).where(WatchedParticipant.watched_id == w.id)).all())
        bewertet = set(db.exec(select(WatchedRating.user_id).where(WatchedRating.watched_id == w.id)).all())
        schon = set(
            db.exec(
                select(Ereignis.user_id).where(Ereignis.typ == "bewerten_gefragt", Ereignis.bezug == str(w.id))
            ).all()
        )
        offen = dabei - bewertet - schon
        if not offen:
            continue
        for uid in offen:
            db.add(Ereignis(typ="bewerten_gefragt", user_id=uid, bezug=str(w.id)))
        db.commit()
        film = db.get(Movie, w.movie_id)
        n += an(
            db,
            offen,
            "bewerten",
            "⭐ Wie war „{titel}“?",
            "Gib dem Film von gestern deine Sterne – dauert zwei Sekunden.",
            tag=f"bewerten-{w.id}",
            ttl=12 * 3600,
            werte={"titel": film.title if film else "?"},
        )
    return n


async def erinnern() -> None:
    """Background task: look for due reminders every minute."""

    def einmal() -> None:
        with DBSession(engine) as db:
            faellige_erinnerungen(db)
            los_meldungen(db)
            bewertungs_erinnerungen(db)

    while True:
        with contextlib.suppress(Exception):
            await asyncio.to_thread(einmal)
        await asyncio.sleep(PRUEFEN_ALLE)
