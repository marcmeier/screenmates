"""Users, name selection (the lightweight login), name requests, film-as-PIN, attendance."""

from __future__ import annotations

import json
import time
from collections import defaultdict, deque
from datetime import UTC, datetime, timedelta
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Request, Response
from pydantic import BaseModel, Field
from sqlalchemy.exc import IntegrityError
from sqlmodel import Session as DBSession
from sqlmodel import col, func, select

from .. import bilder, erfolge
from ..db import get_session
from ..gruppen import aktive_gruppe, aufnehmen, gruppen_admin, mitgliedschaften
from ..models import Abend, Abo, Ereignis, Gruppe, Mitglied, Session, User
from ..serialize import user_dict
from ..session import (
    current_session,
    current_user,
    ensure_session,
    is_admin,
    require_admin,
    require_owner_or_admin,
    require_user,
)
from ..util import BERLIN, utc

router = APIRouter(prefix="/api", tags=["users"])

PALETTE = ["#e50914", "#f5a623", "#7ed321", "#4a90e2", "#bd10e0", "#50e3c2", "#ff6b6b", "#d4a017"]

# Film-as-PIN guesses: at most MAX_TRIES wrong films per user per WINDOW seconds.
MAX_TRIES, WINDOW = 8, 600
_fails: dict[int, deque[float]] = defaultdict(deque)

# Open name requests at a time, so the list an admin has to go through stays short.
MAX_ANTRAEGE = 20


def _throttled(user_id: int) -> bool:
    q = _fails[user_id]
    while q and q[0] < time.monotonic() - WINDOW:
        q.popleft()
    return len(q) >= MAX_TRIES


def admin_count(db: DBSession) -> int:
    return db.exec(select(func.count()).select_from(User).where(col(User.is_admin), col(User.freigegeben))).one()


def ensure_not_last_admin(db: DBSession, u: User) -> None:
    if u.is_admin and u.freigegeben and admin_count(db) <= 1:
        raise HTTPException(409, "Es muss mindestens einen Admin geben.")


def clean_name(raw: str) -> str:
    name = " ".join(raw.split())
    if not name:
        raise HTTPException(422, "Name fehlt.")
    return name


def in_einzige_gruppe(db: DBSession, u: User, *, admin: bool = False) -> None:
    """With exactly one group on the server, approved names join it right away (no commit)."""
    gruppen = db.exec(select(Gruppe.id)).all()
    if len(gruppen) == 1 and not db.exec(select(Mitglied).where(Mitglied.user_id == u.id)).first():
        db.add(Mitglied(gruppe_id=gruppen[0], user_id=u.id, ist_admin=admin))


def new_user(db: DBSession, name: str, *, freigegeben: bool, admin: bool = False, ohne_gruppe: bool = False) -> User:
    count = db.exec(select(func.count()).select_from(User)).one()
    u = User(name=name, color=PALETTE[count % len(PALETTE)], freigegeben=freigegeben, is_admin=admin)
    db.add(u)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(409, f"„{name}“ gibt es schon.") from None
    db.refresh(u)
    if freigegeben and not ohne_gruppe:
        in_einzige_gruppe(db, u, admin=admin)
        db.commit()
    return u


class NameAnlegen(BaseModel):
    name: str = Field(min_length=1, max_length=30)


class NameWaehlen(BaseModel):
    user_id: int | None = None
    movie_id: int | None = None  # the protection film, when the user is guarded


class AbosSetzen(BaseModel):
    anbieter: list[int] = Field(max_length=60)  # TMDB provider ids


class SchutzSetzen(BaseModel):
    movie_id: int | None = None  # None removes the protection


@router.get("/users")
def list_users(
    db: DBSession = Depends(get_session),
    user: User | None = Depends(current_user),
    admin: bool = Depends(is_admin),
    sess: Session | None = Depends(current_session),
):
    """Everyone on the server (for names and avatars), and the caller's active group."""
    rows = db.exec(select(User).where(col(User.freigegeben)).order_by(User.created_at)).all()
    abos: dict[int, list[int]] = defaultdict(list)
    for uid, pid in db.exec(select(Abo.user_id, Abo.provider_id).order_by(Abo.provider_id)).all():
        abos[uid].append(pid)
    lv = erfolge.levels(db)
    gruppe = None
    dabei: set[int] = set()
    antworten: dict[int, str] = {}
    if user:
        ms = mitgliedschaften(db, user.id)
        gid = sess.gruppe_id if sess and sess.gruppe_id in ms else (min(ms) if ms else None)
        if gid is not None:
            g = db.get(Gruppe, gid)
            mit = db.exec(select(Mitglied).where(Mitglied.gruppe_id == gid)).all()
            dabei = {m.user_id for m in mit if m.dabei}
            antworten = {m.user_id: m.rueckmeldung for m in mit if m.rueckmeldung}
            gruppe = {
                "id": gid,
                "name": g.name if g else "",
                "admin": admin or ms[gid].ist_admin,
                "mitglieder": sorted(m.user_id for m in mit),
            }
    me = user_dict(user, abos[user.id], lv.get(user.id, 1), user.id in dabei, antworten.get(user.id)) if user else None
    if me is not None and user is not None:
        me["design"] = json.loads(user.design) if user.design else {}
    antraege = (
        db.exec(select(func.count()).select_from(User).where(col(User.freigegeben).is_(False))).one() if admin else 0
    )
    return {
        "users": [user_dict(u, abos[u.id], lv.get(u.id, 1), u.id in dabei, antworten.get(u.id)) for u in rows],
        "ich": me,
        "admin": admin,
        "antraege": antraege,
        "gruppe": gruppe,
    }


@router.post("/users", status_code=201)
def create_user(
    body: NameAnlegen,
    request: Request,
    response: Response,
    db: DBSession = Depends(get_session),
    admin: bool = Depends(is_admin),
    sess: Session | None = Depends(current_session),
):
    """Create a name. The very first one becomes admin; afterwards the invitation decides:
    a "direkt" link lets you in, otherwise it's a request for an admin of the link's group."""
    name = clean_name(body.name)
    if db.exec(select(func.count()).select_from(User)).one() == 0:
        u = new_user(db, name, freigegeben=True, admin=True)
        # The door closes with the first name: its browser stays inside.
        eigene = ensure_session(request, response, db)
        eigene.zugang = True
        db.add(eigene)
        db.commit()
        if not db.exec(select(Mitglied).where(Mitglied.user_id == u.id)).first():
            # A fresh install: the first name runs the first group.
            gid = db.exec(select(Gruppe.id).order_by(Gruppe.id)).first()
            if gid is None:
                g = Gruppe(name="Unsere Gruppe")
                db.add(g)
                db.flush()
                gid = g.id
            db.add(Mitglied(gruppe_id=gid, user_id=u.id, ist_admin=True))
            db.commit()
        return user_dict(u)
    if admin:
        return user_dict(new_user(db, name, freigegeben=True))
    from .zugang import einladung_der_sitzung

    e = einladung_der_sitzung(db, sess)
    if e is not None and e.direkt:
        e.nutzungen += 1
        db.add(e)
        u = new_user(db, name, freigegeben=True, ohne_gruppe=True)
        aufnehmen(db, e.gruppe_id, u.id)
        db.commit()
        return user_dict(u)
    offen = db.exec(select(func.count()).select_from(User).where(col(User.freigegeben).is_(False))).one()
    if offen >= MAX_ANTRAEGE:
        raise HTTPException(429, "Gerade warten schon viele Anträge – bitte später nochmal.")
    u = new_user(db, name, freigegeben=False)
    if e is not None:
        e.nutzungen += 1
        u.antrag_gruppe_id = e.gruppe_id
        db.add_all([e, u])
        db.commit()
        db.refresh(u)
    return user_dict(u)


@router.post("/users/waehlen")
def choose_user(body: NameWaehlen, request: Request, response: Response, db: DBSession = Depends(get_session)):
    sess = ensure_session(request, response, db)
    if body.user_id is None:  # logout; the browser keeps its access
        sess.user_id = None
        db.add(sess)
        db.commit()
        return {"ich": None, "admin": False}
    u = db.get(User, body.user_id)
    if u is None:
        raise HTTPException(404, "Diesen Namen gibt es nicht.")
    if not u.freigegeben:
        raise HTTPException(403, f"„{u.name}“ wartet noch auf die Freigabe durch einen Admin.")
    if u.schutz_movie_id is not None:
        if _throttled(u.id):
            raise HTTPException(429, "Zu viele Fehlversuche – bitte später nochmal.")
        if body.movie_id != u.schutz_movie_id:
            _fails[u.id].append(time.monotonic())
            raise HTTPException(403, "Das ist nicht der richtige Film.")
        _fails.pop(u.id, None)
    sess.user_id = u.id
    sess.zugang = True  # whoever holds a name is inside, also after logging out
    db.add(sess)
    db.commit()
    return {"ich": user_dict(u), "admin": u.is_admin}


@router.delete("/users/{user_id}", dependencies=[Depends(require_admin)])
def delete_user(user_id: int, db: DBSession = Depends(get_session)):
    """Delete a name - also how an admin turns down a request."""
    u = db.get(User, user_id)
    if u is None:
        raise HTTPException(404)
    ensure_not_last_admin(db, u)
    bild = u.bild
    db.delete(u)
    db.commit()
    bilder.loeschen(user_id, bild)
    return {"ok": True}


@router.get("/users/{user_id}/schutz")
def get_schutz(user_id: int, db: DBSession = Depends(get_session)):
    u = db.get(User, user_id)
    if u is None:
        raise HTTPException(404)
    return {"hat_schutz": u.schutz_movie_id is not None}


@router.post("/users/{user_id}/schutz")
def set_schutz(
    user_id: int,
    body: SchutzSetzen,
    db: DBSession = Depends(get_session),
    user: User | None = Depends(current_user),
    admin: bool = Depends(is_admin),
):
    u = db.get(User, user_id)
    if u is None:
        raise HTTPException(404)
    require_owner_or_admin(u.id, user, admin)
    u.schutz_movie_id = body.movie_id
    db.add(u)
    db.commit()
    return {"hat_schutz": u.schutz_movie_id is not None}


@router.post("/abos")
def set_abos(body: AbosSetzen, user: User = Depends(require_user), db: DBSession = Depends(get_session)):
    """Replace my streaming subscriptions."""
    for a in db.exec(select(Abo).where(Abo.user_id == user.id)).all():
        db.delete(a)
    db.flush()
    for pid in sorted(set(body.anbieter)):
        db.add(Abo(user_id=user.id, provider_id=pid))
    db.commit()
    return {"abos": sorted(set(body.anbieter))}


def rueckmelden(db: DBSession, m: Mitglied, antwort: str | None, termin: datetime | None) -> None:
    """In, maybe, no, or no answer (None). No commit.

    A yes to an upcoming date is remembered for the "Wort gehalten" achievement:
    it counts once that evening took place with this person there.
    """
    m.dabei = antwort == "ja"
    m.rueckmeldung = antwort if antwort in ("vielleicht", "nein") else ""
    db.add(m)
    if antwort == "ja" and termin is not None and utc(termin) > datetime.now(UTC) - timedelta(hours=6):
        tag = utc(termin).astimezone(BERLIN).date().isoformat()
        schon = db.exec(
            select(Ereignis).where(Ereignis.typ == "zusage", Ereignis.user_id == m.user_id, Ereignis.bezug == tag)
        ).first()
        if not schon:
            erfolge.protokoll(db, "zusage", m.user_id, tag)


def _mitglied(db: DBSession, gid: int, user: User) -> Mitglied:
    return db.exec(select(Mitglied).where(Mitglied.gruppe_id == gid, Mitglied.user_id == user.id)).one()


def _termin(db: DBSession, gid: int) -> datetime | None:
    a = db.get(Abend, gid)
    return a.termin if a else None


def _antwort(m: Mitglied) -> dict:
    return {"dabei": m.dabei, "rueckmeldung": "ja" if m.dabei else (m.rueckmeldung or None)}


@router.post("/dabei")
def toggle_dabei(
    user: User = Depends(require_user), gid: int = Depends(aktive_gruppe), db: DBSession = Depends(get_session)
):
    m = _mitglied(db, gid, user)
    rueckmelden(db, m, None if m.dabei else "ja", _termin(db, gid))
    db.commit()
    return _antwort(m)


class Rueckmeldung(BaseModel):
    antwort: Literal["ja", "vielleicht", "nein"] | None = None


@router.put("/dabei")
def reply(
    body: Rueckmeldung,
    user: User = Depends(require_user),
    gid: int = Depends(aktive_gruppe),
    db: DBSession = Depends(get_session),
):
    """Answer for the next movie night: in, maybe, no (None takes the answer back)."""
    m = _mitglied(db, gid, user)
    rueckmelden(db, m, body.antwort, _termin(db, gid))
    db.commit()
    return _antwort(m)


@router.delete("/dabei")
def reset_dabei(
    gid: int = Depends(aktive_gruppe), ok: bool = Depends(gruppen_admin), db: DBSession = Depends(get_session)
):
    if not ok:
        raise HTTPException(403, "Das darf nur ein Admin dieser Gruppe.")
    for m in db.exec(select(Mitglied).where(Mitglied.gruppe_id == gid)).all():
        if m.dabei or m.rueckmeldung:
            m.dabei, m.rueckmeldung = False, ""
            db.add(m)
    db.commit()
    return {"ok": True}


GEMEINSAM_MIN = 3  # films both rated before a taste match is shown


@router.get("/users/{user_id}/geschmack")
def taste(
    user_id: int,
    ich: User = Depends(require_user),
    db: DBSession = Depends(get_session),
):
    """ "Lena tickt zu 87 % wie du": how close this person's stars are to everyone's they share a group with.

    100 % means the same stars on every film both rated, 0 % two stars apart on average
    (ratings rarely differ by more, so a scale up to four stars would put everyone at 80 %).
    Only people who share a group with the asker are compared.
    """
    from ..models import Watched, WatchedRating

    meine_gruppen = set(mitgliedschaften(db, ich.id))
    leute = set(db.exec(select(Mitglied.user_id).where(col(Mitglied.gruppe_id).in_(meine_gruppen))).all())
    if user_id not in leute | {ich.id}:
        raise HTTPException(404)
    nachbarn = leute - {user_id}
    sterne: dict[int, dict[int, list[int]]] = defaultdict(lambda: defaultdict(list))
    for uid, mid, s in db.exec(
        select(WatchedRating.user_id, Watched.movie_id, WatchedRating.stars)
        .join(Watched, col(Watched.id) == WatchedRating.watched_id)
        .where(col(Watched.hidden).is_(False))
    ).all():
        sterne[uid][mid].append(s)
    mittel = {uid: {mid: sum(v) / len(v) for mid, v in filme.items()} for uid, filme in sterne.items()}
    meine = mittel.get(user_id, {})
    out = []
    for uid in nachbarn:
        deine = mittel.get(uid, {})
        gemeinsam = set(meine) & set(deine)
        if len(gemeinsam) < GEMEINSAM_MIN:
            continue
        abstand = sum(abs(meine[m] - deine[m]) for m in gemeinsam) / len(gemeinsam)
        out.append({"user_id": uid, "prozent": max(0, round(100 * (1 - abstand / 2))), "gemeinsam": len(gemeinsam)})
    out.sort(key=lambda v: (-v["prozent"], -v["gemeinsam"]))
    return {"vergleiche": out, "min": GEMEINSAM_MIN}


THEMES = ("kino", "nacht", "neon", "wald", "bernstein", "violett", "oled")
SCHRIFTEN = ("inter", "grotesk", "lesbar", "serif", "mono", "rund", "system")


class Design(BaseModel):
    theme: str = "kino"
    schrift: str = "inter"


@router.put("/users/me/design")
def set_design(body: Design, user: User = Depends(require_user), db: DBSession = Depends(get_session)):
    """How screenmates looks for you: colour theme and font (stays dark either way)."""
    if body.theme not in THEMES or body.schrift not in SCHRIFTEN:
        raise HTTPException(422, "Unbekanntes Farbschema oder Schrift.")
    user.design = json.dumps(json.loads(user.design or "{}") | {"theme": body.theme, "schrift": body.schrift})
    db.add(user)
    db.commit()
    return {"design": json.loads(user.design)}


SPRACHEN = ("de", "en")


class Sprache(BaseModel):
    sprache: str


@router.put("/users/me/sprache")
def set_language(body: Sprache, user: User = Depends(require_user), db: DBSession = Depends(get_session)):
    """The language screenmates speaks to you, on all your devices (film data stays German)."""
    if body.sprache not in SPRACHEN:
        raise HTTPException(422, "Unbekannte Sprache.")
    user.design = json.dumps(json.loads(user.design or "{}") | {"sprache": body.sprache})
    db.add(user)
    db.commit()
    return {"design": json.loads(user.design)}


@router.post("/users/me/willkommen")
def welcomed(user: User = Depends(require_user), db: DBSession = Depends(get_session)):
    """The welcome cards were seen: not again, on no device."""
    user.design = json.dumps(json.loads(user.design or "{}") | {"willkommen": True})
    db.add(user)
    db.commit()
    return {"design": json.loads(user.design)}
