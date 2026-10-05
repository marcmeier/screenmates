"""Profile pictures: upload (owner or admin), fetch, remove.

The upload is the raw image as request body (`Content-Type: image/…`), read
with a hard size limit before anything is decoded.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.concurrency import run_in_threadpool
from fastapi.responses import FileResponse
from sqlmodel import Session as DBSession

from .. import bilder
from ..db import get_session
from ..models import User
from ..serialize import user_dict
from ..session import current_user, is_admin, require_owner_or_admin

router = APIRouter(prefix="/api", tags=["users"])


def _user(db: DBSession, user_id: int) -> User:
    u = db.get(User, user_id)
    if u is None:
        raise HTTPException(404)
    return u


async def _lesen(request: Request) -> bytes:
    if int(request.headers.get("content-length") or 0) > bilder.MAX_BYTES:
        raise HTTPException(413, "Das Bild ist größer als 5 MB.")
    data = bytearray()
    async for chunk in request.stream():
        data += chunk
        if len(data) > bilder.MAX_BYTES:
            raise HTTPException(413, "Das Bild ist größer als 5 MB.")
    if not data:
        raise HTTPException(422, "Kein Bild empfangen.")
    return bytes(data)


@router.put("/users/{user_id}/bild")
async def upload(
    user_id: int,
    request: Request,
    db: DBSession = Depends(get_session),
    user: User | None = Depends(current_user),
    admin: bool = Depends(is_admin),
):
    u = _user(db, user_id)
    require_owner_or_admin(u.id, user, admin)
    data = await _lesen(request)
    try:
        webp = await run_in_threadpool(bilder.verarbeiten, data)
    except bilder.BildFehler as e:
        raise HTTPException(422, str(e)) from None
    alt, u.bild = u.bild, bilder.speichern(u.id, webp)
    db.add(u)
    db.commit()
    bilder.loeschen(u.id, alt)
    db.refresh(u)
    return user_dict(u)


@router.get("/users/{user_id}/bild")
def fetch(user_id: int, db: DBSession = Depends(get_session)):
    u = _user(db, user_id)
    datei = bilder.pfad(u.id, u.bild) if u.bild else None
    if datei is None or not datei.is_file():
        raise HTTPException(404)
    # The URL carries the picture's token (?v=…), so a new picture is a new URL.
    return FileResponse(
        datei, media_type="image/webp", headers={"Cache-Control": "private, max-age=31536000, immutable"}
    )


@router.delete("/users/{user_id}/bild")
def remove(
    user_id: int,
    db: DBSession = Depends(get_session),
    user: User | None = Depends(current_user),
    admin: bool = Depends(is_admin),
):
    u = _user(db, user_id)
    require_owner_or_admin(u.id, user, admin)
    alt, u.bild = u.bild, ""
    db.add(u)
    db.commit()
    bilder.loeschen(u.id, alt)
    return user_dict(u)
