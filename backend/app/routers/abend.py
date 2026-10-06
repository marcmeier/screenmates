"""Around the movie night: who'll like a film, the next date, and memories."""

from __future__ import annotations

import asyncio
from collections import defaultdict
from datetime import UTC, date, datetime, timedelta
from zoneinfo import ZoneInfo

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlmodel import Session as DBSession
from sqlmodel import col, func, select

from .. import erfolge, push, tmdb
from ..config import settings
from ..db import freigeben, get_session
from ..gruppen import aktive_gruppe
from ..models import Abend, Mitglied, Movie, User, Watched, WatchedRating, now
from ..prognose import MIN_BEWERTUNGEN, Film, Modell, vorhersage
from ..serialize import iso
from ..session import require_user
from ..util import ensure_movie, termin_text, upsert_movie
from . import gastgeber
from .watched import _payload

router = APIRouter(prefix="/api", tags=["abend"])

BERLIN = ZoneInfo("Europe/Berlin")
# Rated films without keywords are completed from TMDB, at most this many per request.
STICHWORTE_PRO_ANFRAGE = 30


def _utc(dt: datetime | None) -> datetime | None:
    """SQLite hands back naive datetimes; they are UTC by contract."""
    if dt is None:
        return None
    return dt.replace(tzinfo=UTC) if dt.tzinfo is None else dt.astimezone(UTC)


# --- Wem gefällt's? -----------------------------------------------------------


async def _stichworte(db: DBSession, filme: list[Movie]) -> None:
    """Fill in TMDB keywords for films that lack them (best effort, bounded)."""
    fehlen = [m.id for m in filme if m.keywords == ""][:STICHWORTE_PRO_ANFRAGE]
    if not fehlen or not settings.tmdb_enabled:
        return
    gate = asyncio.Semaphore(5)

    async def laden(mid: int):
        async with gate:
            try:
                return await tmdb.details(mid)
            except tmdb.TMDBError:
                return None

    for data in await asyncio.gather(*(laden(mid) for mid in fehlen)):
        if data is not None:
            upsert_movie(db, data)
    db.commit()


def _sterne(db: DBSession) -> tuple[dict[int, dict[int, list[int]]], dict[int, Movie]]:
    """Everyone's stars per film (oldest film first) and those films."""
    rows = db.exec(
        select(WatchedRating.user_id, Watched.movie_id, WatchedRating.stars)
        .join(Watched, col(Watched.id) == WatchedRating.watched_id)
        .where(col(Watched.hidden).is_(False))
        .order_by(Watched.watched_at)
    ).all()
    sterne: dict[int, dict[int, list[int]]] = defaultdict(lambda: defaultdict(list))
    for uid, mid, s in rows:
        sterne[uid][mid].append(s)
    filme = {m.id: m for m in db.exec(select(Movie).where(col(Movie.id).in_({mid for _, mid, _ in rows}))).all()}
    return sterne, filme


_gruppen_cache: dict[tuple, dict] = {}


async def gruppen_prognose(db: DBSession, movie_ids: list[int], leute: list[int]) -> dict[int, dict]:
    """For each film: what these people will think: their real stars if they rated it,
    otherwise their forecast. The group value needs at least two people with a value."""
    sterne, filme = _sterne(db)
    ziele = {m.id: m for m in db.exec(select(Movie).where(col(Movie.id).in_(movie_ids))).all()}
    await _stichworte(db, [*ziele.values(), *filme.values()])
    stand = db.exec(select(func.count(), func.max(WatchedRating.id), func.sum(WatchedRating.stars))).one()
    schluessel = (tuple(sorted(leute)), tuple(sorted(ziele)), tuple(stand))
    if schluessel in _gruppen_cache:
        return _gruppen_cache[schluessel]
    film = {mid: Film.aus(m) for mid, m in filme.items()}
    ziel = {mid: Film.aus(m) for mid, m in ziele.items()}

    def rechnen() -> dict[int, dict]:
        modelle = {
            uid: Modell.lernen([(film[mid], sum(v) / len(v)) for mid, v in sterne.get(uid, {}).items() if mid in film])
            for uid in leute
        }
        out = {}
        for mid, z in ziel.items():
            personen = []
            for uid in leute:
                echt = sterne.get(uid, {}).get(mid)
                if echt:
                    personen.append({"user_id": uid, "sterne": round(sum(echt) / len(echt), 1), "echt": True})
                elif modelle[uid] is not None:
                    geschaetzt = round(modelle[uid].vorhersage(z).wert, 1)
                    personen.append({"user_id": uid, "sterne": geschaetzt, "echt": False})
            if len(personen) >= 2:
                wert = sum(p["sterne"] for p in personen) / len(personen)
                out[mid] = {"wert": round(wert * 2) / 2, "genau": round(wert, 2), "personen": personen}
        return out

    freigeben(db)  # the maths needs no database
    ergebnis = await asyncio.to_thread(rechnen)
    if len(_gruppen_cache) > 50:
        _gruppen_cache.clear()
    _gruppen_cache[schluessel] = ergebnis
    return ergebnis


@router.get("/movies/{movie_id}/prognose")
async def prognose(movie_id: int, db: DBSession = Depends(get_session)):
    ziel = await ensure_movie(db, movie_id)
    rows = db.exec(
        select(WatchedRating.user_id, Watched.movie_id, WatchedRating.stars)
        .join(Watched, col(Watched.id) == WatchedRating.watched_id)
        .where(col(Watched.hidden).is_(False))
        .order_by(Watched.watched_at)
    ).all()
    sterne: dict[int, dict[int, list[int]]] = defaultdict(lambda: defaultdict(list))
    for uid, mid, s in rows:
        sterne[uid][mid].append(s)  # dicts keep insertion order: oldest film first

    filme = {m.id: m for m in db.exec(select(Movie).where(col(Movie.id).in_({mid for _, mid, _ in rows}))).all()}
    await _stichworte(db, [ziel, *filme.values()])
    zf = Film.aus(ziel)
    film = {mid: Film.aus(m) for mid, m in filme.items()}

    prognosen, zu_wenig = [], []
    for u in db.exec(select(User).order_by(User.name)).all():
        meine = sterne.get(u.id, {})
        if movie_id in meine:
            continue  # rated it already: the real stars are shown, no guess needed
        # Seen twice, rated twice: the average counts.
        p = vorhersage(zf, [(film[mid], sum(v) / len(v)) for mid, v in meine.items() if mid in film])
        if p is None:
            zu_wenig.append({"user_id": u.id, "bewertungen": len(meine)})
            continue
        prognosen.append(
            {
                "user_id": u.id,
                "sterne": round(p.wert * 2) / 2,
                "wert": round(p.wert, 2),
                "sicherheit": p.sicherheit,
                "weil": {"movie_id": p.weil[0].id, "titel": p.weil[0].titel, "sterne": p.weil[1]} if p.weil else None,
            }
        )
    prognosen.sort(key=lambda x: -x["wert"])
    return {"prognosen": prognosen, "zu_wenig": zu_wenig, "min": MIN_BEWERTUNGEN}


# --- Termin (for the invitation) ---------------------------------------------


class TerminSetzen(BaseModel):
    termin: datetime
    notiz: str = Field("", max_length=80)


def _abend(db: DBSession, gid: int) -> Abend:
    return db.get(Abend, gid) or Abend(id=gid)


def _termin_dict(a: Abend) -> dict:
    termin = _utc(a.termin)
    # A date that is long over doesn't belong on the next invitation.
    if termin is None or termin < datetime.now(UTC) - timedelta(hours=6):
        return {"termin": None, "notiz": "", "gesetzt_von": None}
    return {"termin": iso(termin), "notiz": a.notiz, "gesetzt_von": a.gesetzt_von}


@router.get("/termin")
def get_termin(gid: int = Depends(aktive_gruppe), db: DBSession = Depends(get_session)):
    return _termin_dict(_abend(db, gid))


def pruefe_termin(termin: datetime, *, vergangenes: timedelta = timedelta(hours=6)) -> datetime:
    """A date without zone is German time; it must lie ahead (a little in the past is fine), within a year."""
    termin = termin if termin.tzinfo else termin.replace(tzinfo=BERLIN)
    jetzt = datetime.now(UTC)
    if not jetzt - vergangenes <= termin <= jetzt + timedelta(days=366):
        raise HTTPException(422, "Der Termin muss in der Zukunft liegen (höchstens ein Jahr).")
    return termin.astimezone(UTC)


def termin_setzen(db: DBSession, gid: int, user: User, termin: datetime, notiz: str) -> Abend:
    """Set the group's date (commits) and tell the others."""
    termin = pruefe_termin(termin)
    a = _abend(db, gid)
    vorher = _utc(a.termin)
    if vorher is not None and vorher < datetime.now(UTC) - timedelta(hours=6):
        # The last evening is over: who was in back then hasn't answered for this one yet.
        for m in db.exec(select(Mitglied).where(Mitglied.gruppe_id == gid)).all():
            if m.dabei or m.rueckmeldung:
                m.dabei, m.rueckmeldung = False, ""
                db.add(m)
    gastgeber.termin_gesetzt(db, a, user, a.termin)
    a.termin, a.notiz, a.gesetzt_von, a.gesetzt_am = termin, notiz.strip(), user.id, now()
    # A date this close needs no reminder on top of the news.
    a.erinnert = termin if termin - datetime.now(UTC) <= push.ERINNERUNG else None
    db.add(a)
    erfolge.protokoll(db, "termin", user.id, termin.astimezone(BERLIN).date().isoformat())
    db.commit()
    if vorher != termin:
        verschoben = vorher is not None and vorher > datetime.now(UTC) - timedelta(hours=6)
        push.an(
            db,
            push.mitglieder(db, gid, ausser=user.id),
            "termin",
            "📅 Filmabend verschoben – {gruppe}" if verschoben else "📅 Filmabend steht – {gruppe}",
            "{name}: {wann}{notiz}",
            tag=f"termin-{gid}",
            werte={
                "gruppe": push.gruppenname(db, gid),
                "name": user.name,
                "wann": lambda: termin_text(termin),
                "notiz": f" · {a.notiz}" if a.notiz else "",
            },
        )
    return a


@router.put("/termin")
def set_termin(
    body: TerminSetzen,
    user: User = Depends(require_user),
    gid: int = Depends(aktive_gruppe),
    db: DBSession = Depends(get_session),
):
    return _termin_dict(termin_setzen(db, gid, user, body.termin, body.notiz))


@router.delete("/termin")
def clear_termin(gid: int = Depends(aktive_gruppe), db: DBSession = Depends(get_session)):
    a = _abend(db, gid)
    a.termin, a.notiz, a.gesetzt_am = None, "", None
    db.add(a)
    db.commit()
    return _termin_dict(a)


# --- Heute vor einem Jahr -----------------------------------------------------

FENSTER_TAGE = 3


def _gleicher_tag(d: date, jahr: int) -> date:
    try:
        return d.replace(year=jahr)
    except ValueError:  # 29 February in a normal year
        return d.replace(year=jahr, day=28)


@router.get("/erinnerungen")
def erinnerungen(
    heute: date | None = Query(None), gid: int = Depends(aktive_gruppe), db: DBSession = Depends(get_session)
):
    """Films watched around today's date in earlier years (±3 days)."""
    heute = heute or datetime.now(BERLIN).date()
    treffer = []
    for w in db.exec(select(Watched).where(col(Watched.hidden).is_(False), Watched.gruppe_id == gid)).all():
        tag = _utc(w.watched_at).astimezone(BERLIN).date()
        jahre = heute.year - tag.year
        if jahre < 1:
            continue
        abstand = (_gleicher_tag(tag, heute.year) - heute).days
        if abs(abstand) <= FENSTER_TAGE:
            treffer.append((w, jahre, abstand))
    treffer.sort(key=lambda t: (abs(t[2]), t[1]))
    eintraege = {e["id"]: e for e in _payload(db, [w for w, _, _ in treffer])}
    return {
        "erinnerungen": [{"jahre": j, "tage": a, "eintrag": eintraege[w.id]} for w, j, a in treffer],
    }
