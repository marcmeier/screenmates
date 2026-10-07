"""The group's wall-clock time: what "20:00" and "today" mean.

A movie night at 20:00 is 20:00 where the group lives, on every device, also for
someone who is travelling. Dates, reminders, "on this day", awards and the year in
review all count in this zone.

The zone is TIMEZONE (or TZ). Without it, a fresh install takes the zone of the
first admin's browser and keeps it in the database; without that, UTC. Databases
from before the setting existed keep Europe/Berlin, where screenmates started
(migration 0015).
"""

from __future__ import annotations

from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from sqlmodel import Session as DBSession

from .config import settings
from .models import AppMeta

_zone = ZoneInfo("UTC")


def zone() -> ZoneInfo:
    return _zone


def _finden(name: str) -> ZoneInfo | None:
    try:
        return ZoneInfo(name)
    except (ZoneInfoNotFoundError, ValueError):
        return None


def laden(db: DBSession) -> None:
    """On startup: TIMEZONE, else the stored zone, else UTC. An unknown TIMEZONE stops the start."""
    global _zone
    meta = db.get(AppMeta, 1)
    name = settings.timezone or (meta.zeitzone if meta else "") or "UTC"
    z = _finden(name)
    if z is None:
        raise RuntimeError(
            f"Unknown time zone {name!r} in TIMEZONE. Use a name like Europe/Berlin or America/New_York."
        )
    _zone = z


def vom_ersten_admin(db: DBSession, name: str) -> None:
    """A fresh install without TIMEZONE takes the first admin's browser zone (no commit)."""
    global _zone
    z = _finden(name) if name and not settings.timezone else None
    if z is None:
        return
    meta = db.get(AppMeta, 1) or AppMeta(id=1)
    meta.zeitzone = z.key
    db.add(meta)
    _zone = z
