"""Server-side helpers for the operator, run inside the container.

    python -m app.cli namen                 # all names with their state
    python -m app.cli admin "<Name>"        # make someone admin (and approve the name)
    python -m app.cli einladung [<gruppe>]  # a one-time link that lets you straight in (24 h)
    python -m app.cli login "<Name>"        # a login code for that name on a new device (24 h)
    python -m app.cli einrichtung           # the setup code for the first name of a fresh install

The way in when nobody can administrate any more: an existing database that
predates admins, the last admin who lost their device, or no valid invitation left.
"""

from __future__ import annotations

import secrets
import sys
from datetime import UTC, datetime, timedelta

from sqlmodel import Session, select

from .db import engine, init_db
from .models import Einladung, Gruppe, User


def namen(db: Session) -> int:
    for u in db.exec(select(User).order_by(User.created_at)).all():
        rolle = "Admin" if u.is_admin else "–"
        stand = "aktiv" if u.freigegeben else "beantragt"
        print(f"{u.id:>4}  {u.name:<30} {stand:<10} {rolle}")
    return 0


def admin(db: Session, name: str) -> int:
    u = db.exec(select(User).where(User.name == name)).first()
    if u is None:
        print(f"Keinen Namen „{name}“ gefunden. Vorhanden:", file=sys.stderr)
        namen(db)
        return 1
    u.is_admin, u.freigegeben = True, True
    db.add(u)
    db.commit()
    print(f"„{u.name}“ ist jetzt Admin.")
    return 0


def einladung(db: Session, gruppe: int | None) -> int:
    g = db.get(Gruppe, gruppe) if gruppe else db.exec(select(Gruppe).order_by(Gruppe.id)).first()
    if g is None:
        print("Keine solche Gruppe.", file=sys.stderr)
        return 1
    e = Einladung(
        token=secrets.token_urlsafe(18),
        gruppe_id=g.id,
        direkt=True,
        max_nutzungen=1,
        gueltig_bis=datetime.now(UTC) + timedelta(days=1),
        notiz="Kommandozeile",
    )
    db.add(e)
    db.commit()
    print(f"Einladung in „{g.name}“ (einmal, 24 h): <Adresse>/#/einladung/{e.token}")
    return 0


def login_code(db: Session, name: str) -> int:
    from .routers import login

    u = db.exec(select(User).where(User.name == name)).first()
    if u is None or not u.freigegeben:
        print(f"Keinen freigegebenen Namen „{name}“ gefunden.", file=sys.stderr)
        return 1
    c = login.neuer_code(db, u, None, login.GUELTIG_ADMIN)
    print(f"Anmeldecode für „{u.name}“ (einmal, 24 h): {c['code']}  –  <Adresse>{c['path']}")
    return 0


def setup_code(db: Session) -> int:
    from . import einrichtung

    if not einrichtung.offen(db):
        print("Es gibt schon Namen – der Einrichtungscode wird nicht mehr gebraucht.", file=sys.stderr)
        return 1
    c = einrichtung.code(db)
    print(f"Einrichtungscode für den ersten Namen: {c}  –  <Adresse>/#/setup/{c}")
    return 0


def main(argv: list[str]) -> int:
    init_db()
    with Session(engine) as db:
        if argv[:1] == ["namen"]:
            return namen(db)
        if argv[:1] == ["admin"] and len(argv) == 2:
            return admin(db, argv[1])
        if argv[:1] == ["einladung"] and len(argv) <= 2:
            return einladung(db, int(argv[1]) if len(argv) == 2 else None)
        if argv[:1] == ["login"] and len(argv) == 2:
            return login_code(db, argv[1])
        if argv == ["einrichtung"]:
            return setup_code(db)
    print(__doc__, file=sys.stderr)
    return 2


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
