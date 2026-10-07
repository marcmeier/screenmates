"""The first name of a fresh install, and who may create it.

The first name becomes admin. That must not be whoever happens to reach a new
server first, so it needs the setup code. Only the operator sees it: in the
server log on every start while there is no name yet, or with
`python -m app.cli einrichtung`. `SETUP_TOKEN` sets it in advance (scripted
installs, tests). Once the first name exists, the code is gone.
"""

from __future__ import annotations

import logging
import secrets

from sqlmodel import Session as DBSession
from sqlmodel import func, select

from .config import settings
from .models import AppMeta, User

log = logging.getLogger("screenmates")

ALPHABET = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"  # like login codes: nothing to mix up


def offen(db: DBSession) -> bool:
    """No name yet: the first one still needs to be set up."""
    return db.exec(select(func.count()).select_from(User)).one() == 0


def code(db: DBSession) -> str:
    """The current setup code (made once and kept until the first name exists; commits)."""
    if settings.setup_token:
        return settings.setup_token
    meta = db.get(AppMeta, 1) or AppMeta(id=1)
    if not meta.einrichtung:
        roh = "".join(secrets.choice(ALPHABET) for _ in range(12))
        meta.einrichtung = f"{roh[:4]}-{roh[4:8]}-{roh[8:]}"
        db.add(meta)
        db.commit()
    return meta.einrichtung


def stimmt(db: DBSession, eingabe: str) -> bool:
    """Case, spaces and dashes don't matter, like with login codes."""
    norm = lambda s: "".join(c for c in s.upper() if c.isalnum())  # noqa: E731
    return bool(eingabe) and secrets.compare_digest(norm(eingabe), norm(code(db)))


def erledigt(db: DBSession) -> None:
    """The first name exists: the code is no longer needed (no commit)."""
    meta = db.get(AppMeta, 1)
    if meta and meta.einrichtung:
        meta.einrichtung = ""
        db.add(meta)


def ankuendigen(db: DBSession) -> None:
    """On startup: tell the operator how to create the first name."""
    if not offen(db):
        return
    c = code(db)
    log.warning(
        "screenmates has no names yet. The first name becomes admin and needs this setup code: %s  "
        "(or open <your address>/#/setup/%s)",
        c,
        c,
    )
