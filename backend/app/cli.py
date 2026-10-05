"""Server-side helpers for the operator, run inside the container.

    python -m app.cli namen                 # all names with their state
    python -m app.cli admin "<Name>"        # make someone admin (and approve the name)
    python -m app.cli zugang-aus            # open the door again (drop the access question)

The way in when nobody can administrate any more: an existing database that
predates admins, or the last admin who forgot their film.
"""

from __future__ import annotations

import sys

from sqlmodel import Session, select

from .db import engine, init_db
from .models import User, Zugang


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


def zugang_aus(db: Session) -> int:
    z = db.get(Zugang, 1)
    if z is not None:
        z.movie_id = None
        db.add(z)
        db.commit()
    print("Zugangsfrage aufgehoben – screenmates ist wieder offen.")
    return 0


def main(argv: list[str]) -> int:
    init_db()
    with Session(engine) as db:
        if argv[:1] == ["namen"]:
            return namen(db)
        if argv[:1] == ["admin"] and len(argv) == 2:
            return admin(db, argv[1])
        if argv[:1] == ["zugang-aus"]:
            return zugang_aus(db)
    print(__doc__, file=sys.stderr)
    return 2


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
