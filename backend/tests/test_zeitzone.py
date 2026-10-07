"""The group's time zone: a setting, the first admin's browser, or UTC, and what depends on it."""

from datetime import datetime

import pytest

from app import zeitzone
from app.config import settings
from app.models import AppMeta
from app.util import termin_text

from .conftest import SETUP, login


def test_the_app_learns_the_zone_from_the_status(client):
    login(client, "marc")
    assert client.get("/api/status").json()["zeitzone"] == "Europe/Berlin"  # TIMEZONE in conftest


def test_without_setting_the_first_admins_browser_decides(client, db, monkeypatch):
    monkeypatch.setattr(settings, "timezone", "")
    zeitzone.laden(db)
    assert zeitzone.zone().key == "UTC"
    r = client.post("/api/users", json={"name": "Marc", "setup": SETUP, "zeitzone": "America/New_York"})
    assert r.status_code == 201
    db.expire_all()
    assert db.get(AppMeta, 1).zeitzone == "America/New_York"
    assert zeitzone.zone().key == "America/New_York"
    # 20:00 at the group's place, also in what the server writes.
    assert termin_text(datetime.fromisoformat("2026-10-10T00:00:00+00:00")).endswith("20:00 Uhr")
    zeitzone.laden(db)  # after a restart
    assert zeitzone.zone().key == "America/New_York"


def test_the_setting_wins_and_nonsense_from_a_browser_is_ignored(client, db, monkeypatch):
    zeitzone.vom_ersten_admin(db, "Asia/Tokyo")  # TIMEZONE is set: no effect
    assert zeitzone.zone().key == "Europe/Berlin"
    monkeypatch.setattr(settings, "timezone", "")
    zeitzone.laden(db)
    zeitzone.vom_ersten_admin(db, "../../etc/passwd")
    zeitzone.vom_ersten_admin(db, "Mars/Olympus")
    assert zeitzone.zone().key == "UTC"


def test_an_unknown_timezone_setting_stops_the_start(db, monkeypatch):
    monkeypatch.setattr(settings, "timezone", "Europe/Atlantis")
    with pytest.raises(RuntimeError, match="Europe/Atlantis"):
        zeitzone.laden(db)


def test_a_date_without_zone_is_the_groups_time(client, monkeypatch):
    login(client, "marc")
    monkeypatch.setattr(zeitzone, "_zone", zeitzone.ZoneInfo("America/New_York"))
    jahr = datetime.now().year + 1
    r = client.put("/api/termin", json={"termin": f"{jahr}-01-15T20:00:00"}).json()
    assert r["termin"] == f"{jahr}-01-16T01:00:00Z"  # 20:00 in New York (EST) is 01:00 UTC
