"""The movie night in your calendar: one date as a file, or all your groups' dates as a feed.

`GET /api/termin.ics` downloads the active group's next date. The feed
(`/api/kalender/<token>.ics`) is for calendar apps, which can't log in: a
personal secret token in the URL is the key, so the feed is open without a
session (see zugang.OFFEN). It lists the next date of every group the token's
owner belongs to; a date that moves is updated, one that's over drops out.
Making a new token kills the old link.
"""

from __future__ import annotations

import secrets
from datetime import UTC, datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException, Request, Response
from sqlmodel import Session as DBSession
from sqlmodel import col, func, select

from ..db import get_session
from ..gruppen import aktive_gruppe, mitgliedschaften
from ..models import Abend, Gruppe, Kistenoeffnung, Mitglied, Movie, Suggestion, User
from ..session import require_user
from ..sprache import als, tr, von
from ..util import utc

router = APIRouter(prefix="/api", tags=["kalender"])

DAUER = timedelta(hours=3)
VORBEI = timedelta(hours=6)  # like the invitation: a date this long over is gone
ERINNERN = "-PT2H"


def _esc(text: str) -> str:
    return text.replace("\\", "\\\\").replace(";", "\\;").replace(",", "\\,").replace("\r", "").replace("\n", "\\n")


def _falten(zeile: str) -> str:
    """Lines longer than 75 octets continue on the next line after a space (RFC 5545)."""
    teile, aktuell = [], ""
    for zeichen in zeile:
        if len((aktuell + zeichen).encode()) > (75 if not teile else 74):
            teile.append(aktuell)
            aktuell = ""
        aktuell += zeichen
    teile.append(aktuell)
    return "\r\n ".join(teile)


def _zeit(dt: datetime) -> str:
    return utc(dt).strftime("%Y%m%dT%H%M%SZ")


def _basis(request: Request) -> str:
    proto = request.headers.get("x-forwarded-proto", request.url.scheme)
    host = request.headers.get("x-forwarded-host") or request.headers.get("host") or request.url.netloc
    return f"{proto}://{host}"


def _beschreibung(db: DBSession, gid: int) -> list[str]:
    zeilen = []
    k = db.exec(
        select(Kistenoeffnung)
        .where(Kistenoeffnung.gruppe_id == gid, col(Kistenoeffnung.erledigt).is_(False))
        .order_by(col(Kistenoeffnung.id).desc())
    ).first()
    if k and utc(k.start) <= datetime.now(UTC):
        m = db.get(Movie, k.movie_id)
        if m:
            zeilen.append(tr("Film des Abends: {titel}", titel=m.title))
    else:
        top = db.exec(
            select(Movie.title)
            .join(Suggestion, col(Suggestion.movie_id) == Movie.id)
            .where(Suggestion.gruppe_id == gid)
            .group_by(Movie.id)
            .order_by(func.count().desc())
            .limit(5)
        ).all()
        if top:
            zeilen.append(tr("Zur Wahl: {filme}", filme=", ".join(top)))
    dabei = db.exec(
        select(User.name)
        .join(Mitglied, col(Mitglied.user_id) == User.id)
        .where(Mitglied.gruppe_id == gid, col(Mitglied.dabei))
    ).all()
    if dabei:
        zeilen.append(tr("Dabei: {namen}", namen=", ".join(sorted(dabei))))
    return zeilen


def _ereignis(db: DBSession, a: Abend, gruppe: str, basis: str, mit_gruppe: bool) -> list[str]:
    termin = utc(a.termin)
    link = f"{basis}/#/abend"
    text = "\n".join([*_beschreibung(db, a.id), tr("Bist du dabei? {link}", link=link)])
    zeilen = [
        "BEGIN:VEVENT",
        f"UID:filmabend-{a.id}-{termin.date().isoformat()}@screenmates",
        f"DTSTAMP:{_zeit(datetime.now(UTC))}",
        f"SEQUENCE:{int(utc(a.gesetzt_am).timestamp()) if a.gesetzt_am else 0}",
        f"DTSTART:{_zeit(termin)}",
        f"DTEND:{_zeit(termin + DAUER)}",
        f"SUMMARY:{_esc('🎬 ' + tr('Filmabend') + (f' · {gruppe}' if mit_gruppe else ''))}",
        f"DESCRIPTION:{_esc(text)}",
        f"URL:{link}",
    ]
    if a.notiz:
        zeilen.append(f"LOCATION:{_esc(a.notiz)}")
    zeilen += [
        "BEGIN:VALARM",
        "ACTION:DISPLAY",
        f"DESCRIPTION:{_esc(tr('Gleich ist Filmabend'))}",
        f"TRIGGER:{ERINNERN}",
        "END:VALARM",
        "END:VEVENT",
    ]
    return zeilen


def _kalender(ereignisse: list[list[str]], name: str) -> Response:
    zeilen = [
        "BEGIN:VCALENDAR",
        "VERSION:2.0",
        "PRODID:-//screenmates//Filmabend//DE",
        "CALSCALE:GREGORIAN",
        "METHOD:PUBLISH",
        f"X-WR-CALNAME:{_esc(name)}",
        "REFRESH-INTERVAL;VALUE=DURATION:PT1H",
        "X-PUBLISHED-TTL:PT1H",
        *[z for e in ereignisse for z in e],
        "END:VCALENDAR",
    ]
    return Response(
        "\r\n".join(_falten(z) for z in zeilen) + "\r\n",
        media_type="text/calendar; charset=utf-8",
        headers={"Cache-Control": "no-store"},
    )


def _naechster(db: DBSession, gid: int) -> Abend | None:
    a = db.get(Abend, gid)
    if a is None or a.termin is None or utc(a.termin) < datetime.now(UTC) - VORBEI:
        return None
    return a


@router.get("/termin.ics")
def termin_datei(
    request: Request,
    gid: int = Depends(aktive_gruppe),
    user: User = Depends(require_user),
    db: DBSession = Depends(get_session),
):
    a = _naechster(db, gid)
    if a is None:
        raise HTTPException(404, "Es gibt noch keinen Termin.")
    g = db.get(Gruppe, gid)
    mehrere = len(mitgliedschaften(db, user.id)) > 1
    with als(von(user)):
        antwort = _kalender([_ereignis(db, a, g.name if g else "", _basis(request), mehrere)], tr("Filmabend"))
    antwort.headers["Content-Disposition"] = 'attachment; filename="filmabend.ics"'
    return antwort


@router.get("/kalender/{datei}")
def feed(datei: str, request: Request, db: DBSession = Depends(get_session)):
    token = datei.removesuffix(".ics")
    user = db.exec(select(User).where(User.kalender == token, col(User.freigegeben))).first() if token else None
    if user is None or len(token) < 20:
        raise HTTPException(404, "Diesen Kalender gibt es nicht (mehr).")
    gruppen = mitgliedschaften(db, user.id)
    namen = {g.id: g.name for g in db.exec(select(Gruppe).where(col(Gruppe.id).in_(gruppen))).all()}
    with als(von(user)):  # a calendar app asks without the app's language: the owner's choice
        ereignisse = [
            _ereignis(db, a, namen.get(gid, ""), _basis(request), len(gruppen) > 1)
            for gid in sorted(gruppen)
            if (a := _naechster(db, gid)) is not None
        ]
    return _kalender(ereignisse, "screenmates")


def _link(user: User) -> dict:
    return {"pfad": f"/api/kalender/{user.kalender}.ics" if user.kalender else None}


@router.get("/kalender")
def get_link(user: User = Depends(require_user)):
    return _link(user)


@router.post("/kalender")
def new_link(user: User = Depends(require_user), db: DBSession = Depends(get_session)):
    """Make the personal feed link (a new one replaces the old: it stops working)."""
    user.kalender = secrets.token_urlsafe(24)
    db.add(user)
    db.commit()
    return _link(user)


@router.delete("/kalender")
def drop_link(user: User = Depends(require_user), db: DBSession = Depends(get_session)):
    user.kalender = ""
    db.add(user)
    db.commit()
    return _link(user)
