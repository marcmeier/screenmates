"""Kino: a group admin shares a screen (browser) or an OBS output, the group watches live.

Media flows over WebRTC through MediaMTX, which fans one upload out to all
viewers. screenmates only relays the WHIP (publish) and WHEP (watch) signalling
and decides who may do what:

- every group has its own Kino: MediaMTX path `kino-<group id>`, its own secret,
  stream key, programme and audience, so several groups can be live at once,
- publishing: an admin of the group (browser) or the group's OBS stream key,
- watching: members of the group.

Every relayed request carries the group's server-side secret; MediaMTX asks
`/api/kino/mtx-auth` to verify it, so its own HTTP port never has to be public.
"""

from __future__ import annotations

import re
import secrets
import time
from collections import defaultdict
from dataclasses import dataclass, field

import httpx
from fastapi import APIRouter, Depends, HTTPException, Request, Response
from pydantic import BaseModel, Field
from sqlmodel import Session as DBSession
from sqlmodel import select

from .. import erfolge, push
from ..config import settings
from ..db import freigeben, get_session
from ..gruppen import _waehlen, aktive_gruppe, gruppen_admin, ist_gruppen_admin, mitgliedschaften
from ..models import Abend, KinoState, Movie, Session, User, now
from ..serialize import iso, movie_dict
from ..session import current_session, current_user, is_admin, require_user
from .gastgeber import darf_moderieren, require_moderation

router = APIRouter(prefix="/api/kino", tags=["kino"])

PFAD = re.compile(r"kino-(\d+)")
PRESENCE_TTL = 25  # seconds without a heartbeat until a viewer counts as gone
MIN_SCHAUEN = 300  # achievements: seconds of watching until a show counts
PUSH_PAUSE = 600  # seconds: a sender reconnecting doesn't notify everyone again


@dataclass
class Saal:
    """What a group's Kino keeps in memory while a show runs."""

    presence: dict[int, float] = field(default_factory=dict)
    audience: set[int] = field(default_factory=set)  # everyone who watched during the current show
    sender: int | None = None  # admin whose browser sends, or who set the programme (OBS)
    quelle: str = ""  # "browser" (someone's logged-in browser) or "obs" (stream key), for the current show
    seit: dict[int, float] = field(default_factory=dict)  # viewer -> first heartbeat of this show
    gezaehlt: set[int] = field(default_factory=set)  # viewers of this show already recorded


_saele: dict[int, Saal] = defaultdict(Saal)
_gemeldet: dict[int, float] = {}  # group -> when "the Kino is live" was last pushed (monotonic)
_pause: dict[int, int] = {}  # group -> since when (ms) the host called a break


def pfad(gid: int) -> str:
    return f"kino-{gid}"


class Programm(BaseModel):
    titel: str = Field("", max_length=120)
    movie_id: int | None = None


def _state(db: DBSession, gid: int) -> KinoState:
    st = db.get(KinoState, gid)
    if st is None:
        st = KinoState(id=gid, secret=secrets.token_urlsafe(32), obs_key=secrets.token_urlsafe(24))
        db.add(st)
        db.commit()
        db.refresh(st)
    return st


def _gruppe_optional(
    sess: Session | None = Depends(current_session),
    user: User | None = Depends(current_user),
    db: DBSession = Depends(get_session),
) -> int | None:
    return _waehlen(sess, mitgliedschaften(db, user.id)) if user else None


def _require_enabled() -> None:
    if not settings.kino_enabled:
        raise HTTPException(503, "Das Kino ist nicht eingerichtet (MEDIAMTX_WEBRTC_URL fehlt).")


async def _mtx_path(gid: int) -> dict | None:
    """The stream's state from the MediaMTX API, or None when nothing is published.

    Asks for the list, not for the one path: `/v3/paths/get/<name>` answers 404
    while nothing is on air, and MediaMTX logs every one of those polls as an
    error: thousands a day, burying the warnings that matter (lost packets).
    """
    try:
        async with httpx.AsyncClient(timeout=3) as c:
            r = await c.get(f"{settings.mediamtx_api_url}/v3/paths/list", params={"itemsPerPage": 1000})
    except httpx.HTTPError:
        return None
    if r.status_code != 200:
        return None
    return next((p for p in r.json().get("items") or [] if p.get("name") == pfad(gid)), None)


def _viewers(gid: int) -> list[int]:
    cutoff = time.monotonic() - PRESENCE_TTL
    return sorted(uid for uid, seen in _saele[gid].presence.items() if seen >= cutoff)


# --- status & programme -------------------------------------------------------


@router.get("")
async def status(gid: int | None = Depends(_gruppe_optional), db: DBSession = Depends(get_session)):
    if not settings.kino_enabled:
        return {"enabled": False, "live": False}
    if gid is None:  # no name or no group yet: nothing to show, but no error either (it's polled)
        return {"enabled": True, "live": False, "zuschauer": [], "publikum": []}
    st = _state(db, gid)
    freigeben(db)
    path = await _mtx_path(gid)
    live = bool(path and path.get("ready"))
    movie = db.get(Movie, st.movie_id) if st.movie_id else None
    seit = path.get("readyTime") if live else None
    return {
        "enabled": True,
        "live": live,
        "seit": seit or (iso(st.gestartet) if live else None),
        "titel": st.titel,
        "movie": movie_dict(movie) if movie else None,
        "zuschauer": _viewers(gid) if live else [],
        "publikum": sorted(_saele[gid].audience),
        "pause": _pause.get(gid) if live else None,
        # Where the show comes from, so a host on another device isn't told "über OBS".
        "quelle": _saele[gid].quelle or None if live else None,
        "sender": _saele[gid].sender if live else None,
    }


class Pause(BaseModel):
    an: bool


@router.post("/pause", dependencies=[Depends(require_moderation)])
def set_pause(body: Pause, gid: int = Depends(aktive_gruppe)):
    """ "Kurze Pause": everyone sees it over the picture until the host goes on."""
    if body.an:
        _pause.setdefault(gid, int(time.time() * 1000))
    else:
        _pause.pop(gid, None)
    return {"pause": _pause.get(gid)}


@router.post("/programm", dependencies=[Depends(require_moderation)])
def set_programm(
    body: Programm,
    gid: int = Depends(aktive_gruppe),
    db: DBSession = Depends(get_session),
    user: User | None = Depends(current_user),
):
    saal = _saele[gid]
    saal.sender = user.id if user else saal.sender  # OBS sends without a session: credit whoever set the programme
    st = _state(db, gid)
    if body.movie_id is not None and db.get(Movie, body.movie_id) is None:
        raise HTTPException(422, "Film nicht im Katalog.")
    st.titel, st.movie_id = body.titel.strip(), body.movie_id
    db.add(st)
    db.commit()
    return {"ok": True}


@router.post("/da")
def heartbeat(
    user: User = Depends(require_user), gid: int = Depends(aktive_gruppe), db: DBSession = Depends(get_session)
):
    """Viewers ping while the player is open; that's the live audience."""
    saal = _saele[gid]
    saal.presence[user.id] = time.monotonic()
    saal.audience.add(user.id)
    _zaehlen(db, gid, user.id)
    return {"zuschauer": _viewers(gid)}


def _zaehlen(db: DBSession, gid: int, uid: int) -> None:
    """Record a viewer after MIN_SCHAUEN, and the sender once two others watched that long."""
    saal = _saele[gid]
    st = _state(db, gid)
    if st.gestartet is None or uid == saal.sender or uid in saal.gezaehlt:
        return
    start = saal.seit.setdefault(uid, time.monotonic())
    if time.monotonic() - start < MIN_SCHAUEN:
        return
    show = iso(st.gestartet)
    saal.gezaehlt.add(uid)
    erfolge.protokoll(db, "kino_geschaut", uid, show)
    if len(saal.gezaehlt) == 2:
        erfolge.protokoll(db, "kino_gesendet", saal.sender, show)
    db.commit()


@router.delete("/da")
def leave(user: User = Depends(require_user), gid: int = Depends(aktive_gruppe)):
    _saele[gid].presence.pop(user.id, None)
    return {"ok": True}


@router.get("/obs", dependencies=[Depends(require_moderation)])
def obs_settings(
    request: Request,
    gid: int = Depends(aktive_gruppe),
    db: DBSession = Depends(get_session),
    user: User = Depends(require_user),
    admin: bool = Depends(gruppen_admin),
):
    _require_enabled()
    base = str(request.base_url).rstrip("/")
    # One URL for every group: the stream key says which Kino it is. Admins get the group's
    # key; a host their personal one, which stops working when the baton moves on.
    return {"server": f"{base}/api/kino/whip", "key": _obs_key(db, gid, user, admin), "persoenlich": not admin}


def _obs_key(db: DBSession, gid: int, user: User, admin: bool, neu: bool = False) -> str:
    if admin:
        st = _state(db, gid)
        if neu:
            st.obs_key = secrets.token_urlsafe(24)
            db.add(st)
            db.commit()
        return st.obs_key
    if neu or not user.obs_key:
        user.obs_key = secrets.token_urlsafe(24)
        db.add(user)
        db.commit()
    return user.obs_key


@router.post("/obs/neu", dependencies=[Depends(require_moderation)])
def rotate_obs_key(
    gid: int = Depends(aktive_gruppe),
    db: DBSession = Depends(get_session),
    user: User = Depends(require_user),
    admin: bool = Depends(gruppen_admin),
):
    return {"key": _obs_key(db, gid, user, admin, neu=True)}


@router.delete("", dependencies=[Depends(require_moderation)])
async def stop(gid: int = Depends(aktive_gruppe)):
    """End the show, whoever is sending (also an OBS the admin can't reach)."""
    _require_enabled()
    path = await _mtx_path(gid)
    source = (path or {}).get("source") or {}
    if source.get("type") == "webRTCSession" and source.get("id"):
        async with httpx.AsyncClient(timeout=3) as c:
            await c.post(f"{settings.mediamtx_api_url}/v3/webrtcsessions/kick/{source['id']}")
    _saele[gid].presence.clear()
    _pause.pop(gid, None)
    return {"ok": True}


# --- MediaMTX auth hook -----------------------------------------------------------


@router.post("/mtx-auth", include_in_schema=False)
async def mtx_auth(request: Request, db: DBSession = Depends(get_session)):
    """Called by MediaMTX for every action. Only our own relayed requests pass."""
    try:
        req = await request.json()
    except ValueError:
        raise HTTPException(400) from None
    m = PFAD.fullmatch(str(req.get("path") or ""))
    st = db.get(KinoState, int(m.group(1))) if m else None
    ok = (
        st is not None
        and req.get("action") in ("publish", "read")
        and secrets.compare_digest(str(req.get("token") or req.get("password") or ""), st.secret)
    )
    if not ok:
        raise HTTPException(401)
    if req.get("action") == "publish":
        st.gestartet = now()
        db.add(st)
        db.commit()
        saal = _saele[st.id]
        saal.audience.clear()
        saal.seit.clear()
        saal.gezaehlt.clear()
        _live_melden(db, st)
    return Response(status_code=200)


def _live_melden(db: DBSession, st: KinoState) -> None:
    """Tell the group (who isn't in the app anyway) that the Kino went live."""
    gid = st.id
    if gid is None or time.monotonic() - _gemeldet.get(gid, -1e9) < PUSH_PAUSE:
        return
    _gemeldet[gid] = time.monotonic()
    sender = _saele[gid].sender
    wer = db.get(User, sender) if sender else None
    push.an(
        db,
        push.abwesend(gid, push.mitglieder(db, gid, ausser=sender)),
        "kino",
        "🎬 Das Kino ist live – {gruppe}",
        "{name} sendet „{titel}“. Komm dazu!" if st.titel else "{name} sendet gerade. Komm dazu!",
        url="/#/kino",
        tag=f"kino-{gid}",
        ttl=1800,
        dringend=True,
        werte={"gruppe": push.gruppenname(db, gid), "name": wer.name if wer else "?", "titel": st.titel},
    )


# --- WHIP / WHEP relay ------------------------------------------------------------


def _bearer(request: Request) -> str:
    auth = request.headers.get("authorization", "")
    return auth[7:].strip() if auth.lower().startswith("bearer ") else ""


def _sender_gruppe(request: Request, db: DBSession, gid: int | None, user: User | None, admin: bool) -> int:
    """Which group's Kino this publisher may send to: the host's or an admin's active group,
    or the OBS key's (a group's key, or a host's personal key while they hold the baton)."""
    if gid is not None and darf_moderieren(db, gid, user, ist_gruppen_admin(db, gid, user, admin)):
        return gid
    key = _bearer(request)
    if key:
        for st in db.exec(select(KinoState)).all():
            if st.obs_key and secrets.compare_digest(key, st.obs_key):
                return st.id
        for u in db.exec(select(User).where(User.obs_key != "")).all():
            if secrets.compare_digest(key, u.obs_key):
                a = db.exec(select(Abend).where(Abend.gastgeber_id == u.id).order_by(Abend.id)).first()
                if a is not None and a.id is not None:
                    _saele[a.id].sender = u.id
                    return a.id
    raise HTTPException(403, "Senden darf der Gastgeber oder ein Admin der Gruppe (oder OBS mit dem Stream-Key).")


def _without_tcp_candidates(sdp: bytes) -> bytes:
    """Drop ICE-TCP candidates from an SDP answer.

    OBS (libjuice) only does UDP anyway, and FFmpeg's WHIP muxer aborts with
    "Protocol tcp is not supported by RTC" when MediaMTX happens to list a TCP
    candidate first; the order varies, so it failed only sometimes.
    """
    lines = sdp.split(b"\r\n")
    keep = [ln for ln in lines if not (ln.startswith(b"a=candidate:") and b" tcp " in ln)]
    return b"\r\n".join(keep)


async def _relay(
    method: str, upstream: str, request: Request, db: DBSession, gid: int, *, udp_only: bool = False
) -> Response:
    _require_enabled()
    headers = {"Authorization": f"Bearer {_state(db, gid).secret}"}
    freigeben(db)
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
        # MediaMTX answers with /kino-<gid>/whip/<id>; keep the session behind our proxy.
        kind, rid = loc.rstrip("/").split("/")[-2:]
        out.headers["location"] = f"/api/kino/sitzung/{kind}/{rid}"
    return out


@router.post("/whip")
async def whip(
    request: Request,
    db: DBSession = Depends(get_session),
    gid: int | None = Depends(_gruppe_optional),
    user: User | None = Depends(current_user),
    admin: bool = Depends(is_admin),
):
    ziel = _sender_gruppe(request, db, gid, user, admin)
    browser = (
        ziel == gid and user is not None and darf_moderieren(db, gid, user, ist_gruppen_admin(db, gid, user, admin))
    )
    if browser:
        _saele[ziel].sender = user.id
    # Who sends is known only here: a browser with a session, or OBS with the stream key.
    _saele[ziel].quelle = "browser" if browser else "obs"
    # Browsers handle every candidate (and benefit from the TCP fallback); OBS-style
    # clients that authenticate with the stream key get UDP candidates only.
    return await _relay("POST", f"{pfad(ziel)}/whip", request, db, ziel, udp_only=not browser)


@router.post("/whep")
async def whep(request: Request, gid: int = Depends(aktive_gruppe), db: DBSession = Depends(get_session)):
    return await _relay("POST", f"{pfad(gid)}/whep", request, db, gid)


@router.api_route("/sitzung/{kind}/{rid}", methods=["PATCH", "DELETE"])
async def session_resource(
    kind: str,
    rid: str,
    request: Request,
    db: DBSession = Depends(get_session),
    gid: int | None = Depends(_gruppe_optional),
    user: User | None = Depends(current_user),
    admin: bool = Depends(is_admin),
):
    if kind == "whip":
        ziel = _sender_gruppe(request, db, gid, user, admin)
    elif kind == "whep":
        if user is None:
            raise HTTPException(401, "Bitte zuerst einen Namen wählen.")
        if gid is None:
            raise HTTPException(409, "Du bist noch in keiner Gruppe – ein Admin nimmt dich auf.")
        ziel = gid
    else:
        raise HTTPException(404)
    if not rid.replace("-", "").isalnum():
        raise HTTPException(404)
    return await _relay(request.method, f"{pfad(ziel)}/{kind}/{rid}", request, db, ziel)
