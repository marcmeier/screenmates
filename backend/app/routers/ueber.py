"""About screenmates: legal notice, privacy and donations, maintained by admins.

Public (also without an invitation): an imprint has to be reachable for everyone.
The texts are Markdown; an empty text means the section isn't shown. Next to the
donation text, admins can name a Ko-fi and a PayPal.me account: only the name is
stored, the link is always built here, so nothing but those two sites is linked.
"""

from __future__ import annotations

import re

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlmodel import Session as DBSession

from ..config import settings
from ..db import get_session
from ..models import Seitentext, now
from ..session import require_admin
from ..sprache import tr

router = APIRouter(prefix="/api", tags=["ueber"])

SEITEN = ("impressum", "datenschutz", "spenden")

# key -> (label, link prefix, what may precede the name when someone pastes a whole link)
KONTEN = {
    "kofi": ("Ko-fi", "https://ko-fi.com/", r"(https?://)?(www\.)?ko-fi\.com/"),
    "paypal": ("PayPal", "https://paypal.me/", r"(https?://)?(www\.)?(paypal\.me/|paypal\.com/paypalme/)"),
}
NAME = re.compile(r"[A-Za-z0-9_.-]{1,64}")


class Text(BaseModel):
    text: str = Field(max_length=20_000)


def texte(db: DBSession) -> dict[str, str]:
    return {k: (t.text if (t := db.get(Seitentext, k)) else "") for k in SEITEN}


def konten(db: DBSession) -> dict[str, dict]:
    out = {}
    for k, (label, prefix, _) in KONTEN.items():
        if (t := db.get(Seitentext, k)) and t.text:
            out[k] = {"label": label, "name": t.text, "url": prefix + t.text}
    return out


def kontoname(key: str, eingabe: str) -> str:
    """'marc', '@marc' or a pasted link -> 'marc'; anything else is refused."""
    name = re.sub(rf"^{KONTEN[key][2]}", "", eingabe.strip(), flags=re.I).strip("/@ ")
    if name and not NAME.fullmatch(name):
        raise HTTPException(422, tr("Das sieht nicht nach einem {konto}-Namen aus.", konto=KONTEN[key][0]))
    return name


@router.get("/ueber")
def ueber(db: DBSession = Depends(get_session)):
    from ..main import __version__

    # The source of this installation (AGPL-3.0 §13): SOURCE_URL, so a modified version links its own.
    return {"version": __version__, "repo": settings.source_url, "texte": texte(db), "konten": konten(db)}


@router.put("/admin/seiten/{key}", dependencies=[Depends(require_admin)])
def set_text(key: str, body: Text, db: DBSession = Depends(get_session)):
    if key not in SEITEN and key not in KONTEN:
        raise HTTPException(404)
    t = db.get(Seitentext, key) or Seitentext(key=key)
    t.text = kontoname(key, body.text) if key in KONTEN else body.text.strip()
    t.geaendert_am = now()
    db.add(t)
    db.commit()
    return {"ok": True}
