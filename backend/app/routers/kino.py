"""Kino: an admin shares a screen (browser) or an OBS output, everyone watches live.

Media flows over WebRTC through MediaMTX, which fans one upload out to all
viewers. screenmates only relays the WHIP (publish) and WHEP (watch) signalling
and decides who may do what:

- publishing: an admin's session (browser) or the OBS stream key,
- watching: anyone who picked a name.

Every relayed request carries a server-side secret; MediaMTX asks
`/api/kino/mtx-auth` to verify it, so its own HTTP port never has to be public.
"""

from __future__ import annotations

import secrets
import time

import httpx
from fastapi import APIRouter, Depends, HTTPException, Request, Response
from pydantic import BaseModel, Field
from sqlmodel import Session as DBSession

from .. import erfolge
from ..config import settings
from ..db import get_session
from ..models import KinoState, Movie, User, now
from ..serialize import iso, movie_dict
from ..session import current_user, is_admin, require_admin, require_user

router = APIRouter(prefix="/api/kino", tags=["kino"])

PATH = "kino"
PRESENCE_TTL = 25  # seconds without a heartbeat until a viewer counts as gone

_presence: dict[int, float] = {}
_audience: set[int] = set()  # everyone who watched during the current show

# Achievements: who sent the current show, and who watched it for long enough.
MIN_SCHAUEN = 300  # seconds of watching until a show counts
_sender: int | None = None  # admin whose browser sends, or who set the programme (OBS)
_seit: dict[int, float] = {}  # viewer -> first heartbeat of this show
_gezaehlt: set[int] = set()  # viewers of this show already recorded


class Programm(BaseModel):
    titel: str = Field("", max_length=120)
    movie_id: int | None = None


def _state(db: DBSession) -> KinoState:
    st = db.get(KinoState, 1)
    if st is None:
        st = KinoState(id=1, secret=secrets.token_urlsafe(32), obs_key=secrets.token_urlsafe(24))
        db.add(st)
        db.commit()
        db.refresh(st)
    return st


def _require_enabled() -> None:
    if not settings.kino_enabled:
        raise HTTPException(503, "Das Kino ist nicht eingerichtet (MEDIAMTX_WEBRTC_URL fehlt).")


async def _mtx_path() -> dict | None:
    """The stream's state from the MediaMTX API, or None when nothing is published."""
    try:
        async with httpx.AsyncClient(timeout=3) as c:
            r = await c.get(f"{settings.mediamtx_api_url}/v3/paths/get/{PATH}")
    except httpx.HTTPError:
        return None
    return r.json() if r.status_code == 200 else None


def _viewers() -> list[int]:
    cutoff = time.monotonic() - PRESENCE_TTL
    return sorted(uid for uid, seen in _presence.items() if seen >= cutoff)


# --- status & programme -------------------------------------------------------


@router.get("")
async def status(db: DBSession = Depends(get_session)):
    if not settings.kino_enabled:
        return {"enabled": False, "live": False}
    st = _state(db)
    path = await _mtx_path()
    live = bool(path and path.get("ready"))
    movie = db.get(Movie, st.movie_id) if st.movie_id else None
    seit = path.get("readyTime") if live else None
    return {
        "enabled": True,
        "live": live,
        "seit": seit or (iso(st.gestartet) if live else None),
        "titel": st.titel,
        "movie": movie_dict(movie) if movie else None,
        "zuschauer": _viewers() if live else [],
        "publikum": sorted(_audience),
    }


@router.post("/programm", dependencies=[Depends(require_admin)])
def set_programm(body: Programm, db: DBSession = Depends(get_session), user: User | None = Depends(current_user)):
    global _sender
    _sender = user.id if user else _sender  # OBS sends without a session: credit whoever set the programme
    st = _state(db)
    if body.movie_id is not None and db.get(Movie, body.movie_id) is None:
        raise HTTPException(422, "Film nicht im Katalog.")
    st.titel, st.movie_id = body.titel.strip(), body.movie_id
    db.add(st)
    db.commit()
    return {"ok": True}


@router.post("/da")
def heartbeat(user: User = Depends(require_user), db: DBSession = Depends(get_session)):
    """Viewers ping while the player is open; that's the live audience."""
    _presence[user.id] = time.monotonic()
    _audience.add(user.id)
    _zaehlen(db, user.id)
    return {"zuschauer": _viewers()}


def _zaehlen(db: DBSession, uid: int) -> None:
    """Record a viewer after MIN_SCHAUEN, and the sender once two others watched that long."""
    st = _state(db)
    if st.gestartet is None or uid == _sender or uid in _gezaehlt:
        return
    start = _seit.setdefault(uid, time.monotonic())
    if time.monotonic() - start < MIN_SCHAUEN:
        return
    show = iso(st.gestartet)
    _gezaehlt.add(uid)
    erfolge.protokoll(db, "kino_geschaut", uid, show)
    if len(_gezaehlt) == 2:
        erfolge.protokoll(db, "kino_gesendet", _sender, show)
    db.commit()


@router.delete("/da")
def leave(user: User = Depends(require_user)):
    _presence.pop(user.id, None)
    return {"ok": True}


@router.get("/obs", dependencies=[Depends(require_admin)])
def obs_settings(request: Request, db: DBSession = Depends(get_session)):
    _require_enabled()
    base = str(request.base_url).rstrip("/")
    return {"server": f"{base}/api/kino/whip", "key": _state(db).obs_key}


@router.post("/obs/neu", dependencies=[Depends(require_admin)])
def rotate_obs_key(db: DBSession = Depends(get_session)):
    st = _state(db)
    st.obs_key = secrets.token_urlsafe(24)
    db.add(st)
    db.commit()
    return {"key": st.obs_key}


@router.delete("", dependencies=[Depends(require_admin)])
async def stop(db: DBSession = Depends(get_session)):
    """End the show, whoever is sending (also an OBS the admin can't reach)."""
    _require_enabled()
    path = await _mtx_path()
    source = (path or {}).get("source") or {}
    if source.get("type") == "webRTCSession" and source.get("id"):
        async with httpx.AsyncClient(timeout=3) as c:
            await c.post(f"{settings.mediamtx_api_url}/v3/webrtcsessions/kick/{source['id']}")
    _presence.clear()
    return {"ok": True}


# --- MediaMTX auth hook -----------------------------------------------------------


@router.post("/mtx-auth", include_in_schema=False)
async def mtx_auth(request: Request, db: DBSession = Depends(get_session)):
    """Called by MediaMTX for every action. Only our own relayed requests pass."""
    try:
        req = await request.json()
    except ValueError:
        raise HTTPException(400) from None
    st = _state(db)
    ok = (
        req.get("action") in ("publish", "read")
        and req.get("path") == PATH
        and secrets.compare_digest(str(req.get("token") or req.get("password") or ""), st.secret)
    )
    if not ok:
        raise HTTPException(401)
    if req.get("action") == "publish":
        st.gestartet = now()
        db.add(st)
        db.commit()
        _audience.clear()
        _seit.clear()
        _gezaehlt.clear()
    return Response(status_code=200)


# --- WHIP / WHEP relay ------------------------------------------------------------


def _bearer(request: Request) -> str:
    auth = request.headers.get("authorization", "")
    return auth[7:].strip() if auth.lower().startswith("bearer ") else ""


async def _may_publish(request: Request, db: DBSession, admin: bool) -> None:
    key = _bearer(request)
    if admin or (key and secrets.compare_digest(key, _state(db).obs_key)):
        return
    raise HTTPException(403, "Senden darf nur ein Admin (oder OBS mit dem Stream-Key).")


def _without_tcp_candidates(sdp: bytes) -> bytes:
    """Drop ICE-TCP candidates from an SDP answer.

    OBS (libjuice) only does UDP anyway, and FFmpeg's WHIP muxer aborts with
    "Protocol tcp is not supported by RTC" when MediaMTX happens to list a TCP
    candidate first; the order varies, so it failed only sometimes.
    """
    lines = sdp.split(b"\r\n")
    keep = [ln for ln in lines if not (ln.startswith(b"a=candidate:") and b" tcp " in ln)]
    return b"\r\n".join(keep)


async def _relay(method: str, upstream: str, request: Request, db: DBSession, *, udp_only: bool = False) -> Response:
    _require_enabled()
    headers = {"Authorization": f"Bearer {_state(db).secret}"}
    for h in ("content-type", "if-match"):
        if h in request.headers:
            headers[h] = request.headers[h]
    try:
        async with httpx.AsyncClient(timeout=10) as c:
            r = await c.request(
                method, f"{settings.mediamtx_webrtc_url}/{upstream}", content=await request.body(), headers=headers
            )
    except httpx.HTTPError:
        raise HTTPException(503, "Der Kino-Server ist nicht erreichbar.") from None

    if r.status_code == 404:
        if method == "DELETE":
            return Response(status_code=200)  # already gone (show ended): deleting is idempotent
        if upstream.endswith("/whep"):
            raise HTTPException(404, "Gerade wird nichts übertragen.")
    body = _without_tcp_candidates(r.content) if udp_only and r.status_code == 201 else r.content
    out = Response(content=body, status_code=r.status_code, media_type=r.headers.get("content-type"))
    for h in ("etag", "accept-patch"):
        if h in r.headers:
            out.headers[h] = r.headers[h]
    for link in r.headers.get_list("link"):
        out.headers.append("link", link)
    if loc := r.headers.get("location"):
        # MediaMTX answers with /kino/whip/<id>; keep the session behind our proxy.
        kind, rid = loc.rstrip("/").split("/")[-2:]
        out.headers["location"] = f"/api/kino/sitzung/{kind}/{rid}"
    return out


@router.post("/whip")
async def whip(
    request: Request,
    db: DBSession = Depends(get_session),
    admin: bool = Depends(is_admin),
    user: User | None = Depends(current_user),
):
    global _sender
    await _may_publish(request, db, admin)
    if admin and user:
        _sender = user.id
    # Browsers handle every candidate (and benefit from the TCP fallback); OBS-style
    # clients that authenticate with the stream key get UDP candidates only.
    return await _relay("POST", f"{PATH}/whip", request, db, udp_only=not admin)


@router.post("/whep", dependencies=[Depends(require_user)])
async def whep(request: Request, db: DBSession = Depends(get_session)):
    return await _relay("POST", f"{PATH}/whep", request, db)


@router.api_route("/sitzung/{kind}/{rid}", methods=["PATCH", "DELETE"])
async def session_resource(
    kind: str,
    rid: str,
    request: Request,
    db: DBSession = Depends(get_session),
    user: User | None = Depends(current_user),
    admin: bool = Depends(is_admin),
):
    if kind == "whip":
        await _may_publish(request, db, admin)
    elif kind == "whep":
        if user is None:
            raise HTTPException(401, "Bitte zuerst einen Namen wählen.")
    else:
        raise HTTPException(404)
    if not rid.replace("-", "").isalnum():
        raise HTTPException(404)
    return await _relay(request.method, f"{PATH}/{kind}/{rid}", request, db)
