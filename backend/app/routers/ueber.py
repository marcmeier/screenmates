"""About screenmates: legal notice, privacy and donations, maintained by admins.

Public (also without an invitation): an imprint has to be reachable for everyone.
The texts are Markdown; an empty text means the section isn't shown.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlmodel import Session as DBSession

from ..db import get_session
from ..models import Seitentext, now
from ..session import require_admin

router = APIRouter(prefix="/api", tags=["ueber"])

SEITEN = ("impressum", "datenschutz", "spenden")
REPO = "https://github.com/marcmeier/screenmates"


class Text(BaseModel):
    text: str = Field(max_length=20_000)


def texte(db: DBSession) -> dict[str, str]:
    return {k: (t.text if (t := db.get(Seitentext, k)) else "") for k in SEITEN}


@router.get("/ueber")
def ueber(db: DBSession = Depends(get_session)):
    from ..main import __version__

    return {"version": __version__, "repo": REPO, "texte": texte(db)}


@router.put("/admin/seiten/{key}", dependencies=[Depends(require_admin)])
def set_text(key: str, body: Text, db: DBSession = Depends(get_session)):
    if key not in SEITEN:
        raise HTTPException(404)
    t = db.get(Seitentext, key) or Seitentext(key=key)
    t.text = body.text.strip()
    t.geaendert_am = now()
    db.add(t)
    db.commit()
    return {"ok": True}
