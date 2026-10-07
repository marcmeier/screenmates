"""Server-side helpers for the operator, run inside the container.

    python -m app.cli names               # all names with their state
    python -m app.cli admin "<name>"      # make someone admin (and approve the name)
    python -m app.cli invite [<group id>] # a one-time link that lets you straight in (24 h)
    python -m app.cli login "<name>"      # a login code for that name on a new device (24 h)
    python -m app.cli setup               # the setup code for the first name of a fresh install

The way in when nobody can administrate any more: an existing database that
predates admins, the last admin who lost their device, or no valid invitation
left. The German command names of older versions (namen, einladung,
einrichtung) still work.
"""

from __future__ import annotations

import secrets
import sys
from datetime import UTC, datetime, timedelta

from sqlmodel import Session, select

from .db import engine, init_db
from .models import Einladung, Gruppe, User


def names(db: Session) -> int:
    for u in db.exec(select(User).order_by(User.created_at)).all():
        rolle = "admin" if u.is_admin else "–"
        stand = "active" if u.freigegeben else "requested"
        print(f"{u.id:>4}  {u.name:<30} {stand:<10} {rolle}")
    return 0


def admin(db: Session, name: str) -> int:
    u = db.exec(select(User).where(User.name == name)).first()
    if u is None:
        print(f"No name “{name}”. These exist:", file=sys.stderr)
        names(db)
        return 1
    u.is_admin, u.freigegeben = True, True
    db.add(u)
    db.commit()
    print(f"“{u.name}” is admin now.")
    return 0


def invite(db: Session, gruppe: int | None) -> int:
    g = db.get(Gruppe, gruppe) if gruppe else db.exec(select(Gruppe).order_by(Gruppe.id)).first()
    if g is None:
        print("No such group.", file=sys.stderr)
        return 1
    e = Einladung(
        token=secrets.token_urlsafe(18),
        gruppe_id=g.id,
        direkt=True,
        max_nutzungen=1,
        gueltig_bis=datetime.now(UTC) + timedelta(days=1),
        notiz="Command line",
    )
    db.add(e)
    db.commit()
    print(f"Invitation to “{g.name}” (once, 24 h): <your address>/#/einladung/{e.token}")
    return 0


def login_code(db: Session, name: str) -> int:
    from .routers import login

    u = db.exec(select(User).where(User.name == name)).first()
    if u is None or not u.freigegeben:
        print(f"No approved name “{name}”.", file=sys.stderr)
        return 1
    c = login.neuer_code(db, u, None, login.GUELTIG_ADMIN)
    print(f"Login code for “{u.name}” (once, 24 h): {c['code']}  –  <your address>{c['path']}")
    return 0


def setup_code(db: Session) -> int:
    from . import einrichtung

    if not einrichtung.offen(db):
        print("Names exist already: the setup code isn't needed any more.", file=sys.stderr)
        return 1
    c = einrichtung.code(db)
    print(f"Setup code for the first name: {c}  –  <your address>/#/setup/{c}")
    return 0


COMMANDS = {
    "names": (names, 0),
    "namen": (names, 0),
    "admin": (admin, 1),
    "invite": (invite, None),
    "einladung": (invite, None),
    "login": (login_code, 1),
    "setup": (setup_code, 0),
    "einrichtung": (setup_code, 0),
}


def main(argv: list[str]) -> int:
    befehl, args = (argv[0], argv[1:]) if argv else ("", [])
    fn, n = COMMANDS.get(befehl, (None, 0))
    if fn is None or (n is not None and len(args) != n) or (n is None and len(args) > 1):
        print(__doc__, file=sys.stderr)
        return 2
    init_db()
    with Session(engine) as db:
        if fn is invite:
            return invite(db, int(args[0]) if args else None)
        return fn(db, *args)


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
