"""Push notifications: subscribe devices, choose what to get, send a test (see push.py)."""

from __future__ import annotations

import json
from urllib.parse import urlsplit

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlmodel import Session as DBSession
from sqlmodel import func, select

from .. import push
from ..db import get_session
from ..models import PushAbo, User
from ..session import require_user

router = APIRouter(prefix="/api/push", tags=["push"])

MAX_GERAETE = 10  # per person; the oldest goes when an eleventh arrives
# The browsers' push services. The server posts to the endpoint a browser hands in, so
# only these are accepted: no member can make it call anything else.
DIENSTE = (
    "fcm.googleapis.com",  # Chrome, Edge on Android, Opera, Brave …
    "android.googleapis.com",
    "push.services.mozilla.com",  # Firefox
    "push.apple.com",  # Safari, iPhone and iPad (web.push.apple.com)
    "notify.windows.com",  # Edge on Windows
)


def bekannter_dienst(endpoint: str) -> bool:
    teile = urlsplit(endpoint)
    host = (teile.hostname or "").lower()
    return (
        teile.scheme == "https"
        and teile.port in (None, 443)
        and any(host == d or host.endswith(f".{d}") for d in DIENSTE)
    )


class Schluessel(BaseModel):
    p256dh: str = Field(min_length=20, max_length=200)
    auth: str = Field(min_length=8, max_length=100)


class Abo(BaseModel):
    endpoint: str = Field(min_length=20, max_length=1000)
    keys: Schluessel
    geraet: str = Field("", max_length=80)


class Abmelden(BaseModel):
    endpoint: str = Field(max_length=1000)


class Wahl(BaseModel):
    arten: dict[str, bool]


def _geraete(db: DBSession, user: User) -> int:
    return db.exec(select(func.count()).select_from(PushAbo).where(PushAbo.user_id == user.id)).one()


def _zustand(db: DBSession, user: User) -> dict:
    wahl = push.wahl(user)
    return {
        "schluessel": push.oeffentlicher_schluessel(db),
        "arten": [{"key": k, "text": t, "an": wahl[k]} for k, t in push.ARTEN.items()],
        "geraete": _geraete(db, user),
    }


@router.get("")
def get_push(user: User = Depends(require_user), db: DBSession = Depends(get_session)):
    return _zustand(db, user)


@router.post("/abo")
def subscribe(body: Abo, user: User = Depends(require_user), db: DBSession = Depends(get_session)):
    """This device wants notifications for whoever is logged in on it (one device, one person)."""
    if not bekannter_dienst(body.endpoint):
        raise HTTPException(422, "Das ist keine Push-Adresse eines bekannten Browsers.")
    a = db.exec(select(PushAbo).where(PushAbo.endpoint == body.endpoint)).first() or PushAbo(
        endpoint=body.endpoint, user_id=user.id, p256dh="", auth=""
    )
    a.user_id, a.p256dh, a.auth, a.geraet = user.id, body.keys.p256dh, body.keys.auth, body.geraet.strip()
    db.add(a)
    db.commit()
    alte = db.exec(select(PushAbo).where(PushAbo.user_id == user.id).order_by(PushAbo.am, PushAbo.id)).all()
    for weg in alte[: max(0, len(alte) - MAX_GERAETE)]:
        db.delete(weg)
    db.commit()
    return _zustand(db, user)


@router.post("/abmelden")
def unsubscribe(body: Abmelden, user: User = Depends(require_user), db: DBSession = Depends(get_session)):
    for a in db.exec(select(PushAbo).where(PushAbo.endpoint == body.endpoint, PushAbo.user_id == user.id)).all():
        db.delete(a)
    db.commit()
    return _zustand(db, user)


@router.put("/arten")
def choose(body: Wahl, user: User = Depends(require_user), db: DBSession = Depends(get_session)):
    unbekannt = set(body.arten) - set(push.ARTEN)
    if unbekannt:
        raise HTTPException(422, f"Unbekannte Benachrichtigung: {', '.join(sorted(unbekannt))}")
    user.push = json.dumps(push.wahl(user) | body.arten)
    db.add(user)
    db.commit()
    return _zustand(db, user)


@router.post("/test")
def test(user: User = Depends(require_user), db: DBSession = Depends(get_session)):
    n = push.an(
        db,
        [user.id],
        "test",
        "🎬 screenmates",
        "So sehen Benachrichtigungen aus. Viel Spaß beim nächsten Filmabend!",
        url="/#/profil/einstellungen",
    )
    if not n:
        raise HTTPException(409, "Auf keinem Gerät sind Benachrichtigungen eingeschaltet.")
    return {"geraete": n}
