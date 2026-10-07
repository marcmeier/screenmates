import os
import shutil
import tempfile
from pathlib import Path

# Configure an isolated database and disable external services *before* the app
# (and its cached settings) is imported. Real env vars beat backend/.env.
_tmp = tempfile.mkdtemp(prefix="screenmates-test-")
os.environ["DATABASE_URL"] = f"sqlite:///{_tmp}/test.db"
os.environ["MEDIA_DIR"] = f"{_tmp}/media"
os.environ["TMDB_API_KEY"] = ""
os.environ["LLM_API_KEY"] = ""
SETUP = os.environ["SETUP_TOKEN"] = "TEST-SETUP-CODE"  # the first name of every fresh test database needs it
os.environ["TIMEZONE"] = "Europe/Berlin"  # the tests' dates and times are German ones,
os.environ["TMDB_LANGUAGE"] = "de-DE"  # and so is their film data
os.environ["TMDB_REGION"] = "DE"

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402
from sqlmodel import Session, select  # noqa: E402

from app import erfolge, push, tmdb  # noqa: E402
from app.config import settings  # noqa: E402
from app.db import engine  # noqa: E402
from app.main import app  # noqa: E402
from app.models import Einladung, Mitglied, SessionName, User  # noqa: E402
from app.routers import gastgeber, kino, kinochat, live, zugang  # noqa: E402

# Push messages the app wanted to send in this test (nothing leaves the machine).
gesendet: list[push.Zustellung] = []


@pytest.fixture(autouse=True)
def _kein_push(monkeypatch):
    gesendet.clear()
    monkeypatch.setattr(push, "abschicken", gesendet.append)


@pytest.fixture
def client():
    """A fresh database (seeded by the lifespan) and an anonymous browser."""
    # A fresh file per test: the lifespan migrates it from scratch, like a new install.
    engine.dispose()
    for suffix in ("", "-wal", "-shm"):
        Path(f"{_tmp}/test.db{suffix}").unlink(missing_ok=True)
    shutil.rmtree(f"{_tmp}/media", ignore_errors=True)
    for backup in Path(_tmp).glob("backup-vor-reset-*.db"):
        backup.unlink()
    zugang._fehl_ip.clear()
    zugang._fehl_alle.clear()
    kino._saele.clear()
    kino._gemeldet.clear()
    kinochat._reaktionen.clear()
    kinochat._takt.clear()
    kinochat._mitgeredet.clear()
    live._stand.clear()
    gastgeber._gesehen.clear()
    tmdb._cache.clear()
    erfolge._zuletzt = 0.0
    with TestClient(app) as c:
        yield c


@pytest.fixture
def browser(client):
    """Factory for additional browsers with their own cookie jar."""
    return lambda: TestClient(app)


@pytest.fixture
def db(client):
    with Session(engine) as s:
        yield s


@pytest.fixture
def wuensche(client):
    """The wishes & ideas board switched on (it's off on a fresh install)."""
    from app.models import AppMeta

    with Session(engine) as s:
        meta = s.get(AppMeta, 1) or AppMeta(id=1)
        meta.wuensche = True
        s.add(meta)
        s.commit()


@pytest.fixture
def kino_on(monkeypatch):
    monkeypatch.setattr(settings, "mediamtx_webrtc_url", "http://mtx:8889")
    monkeypatch.setattr(settings, "mediamtx_api_url", "http://mtx:9997")


@pytest.fixture
def tmdb_on(monkeypatch):
    monkeypatch.setattr(settings, "tmdb_api_key", "test-key")


def _set(name: str, **fields) -> None:
    with Session(engine) as s:
        u = s.exec(select(User).where(User.name == name)).one()
        for k, v in fields.items():
            setattr(u, k, v)
        s.add(u)
        s.commit()


def _mitglied(name: str, gruppe: int = 1, admin: bool = False) -> None:
    with Session(engine) as s:
        u = s.exec(select(User).where(User.name == name)).one()
        m = s.exec(select(Mitglied).where(Mitglied.user_id == u.id, Mitglied.gruppe_id == gruppe)).first()
        m = m or Mitglied(gruppe_id=gruppe, user_id=u.id)
        m.ist_admin = admin
        s.add(m)
        s.commit()


def rein(c: TestClient, gruppe: int = 1, *, direkt: bool = False) -> str:
    """Let this browser in with a fresh invitation (as if someone sent it a link)."""
    import secrets

    token = secrets.token_urlsafe(18)
    with Session(engine) as s:
        s.add(Einladung(token=token, gruppe_id=gruppe, direkt=direkt))
        s.commit()
    r = c.post("/api/zugang", json={"token": token})
    assert r.status_code == 200, r.text
    return token


def binden(c: TestClient, user_id: int) -> None:
    """Give this browser an existing name, as a redeemed login code would."""
    sid = c.cookies.get(settings.session_cookie)
    assert sid, "binden needs a browser with a session"
    with Session(engine) as s:
        if not s.exec(select(SessionName).where(SessionName.sid == sid, SessionName.user_id == user_id)).first():
            s.add(SessionName(sid=sid, user_id=user_id))
            s.commit()


def login(c: TestClient, name: str, *, admin: bool = False) -> dict:
    """Create (or reuse) an approved name in the first group and use it in this browser.

    The first name of a fresh database becomes admin (and group admin) by itself;
    tests say explicitly who is admin instead (`admin=True` or `become_admin`).
    Reusing a name on another browser connects it like a login code would.
    """
    if not c.get("/api/zugang").json()["offen"]:  # invite-only once someone exists: come in like a friend would
        rein(c)
    r = c.post("/api/users", json={"name": name, "setup": SETUP})
    assert r.status_code in (201, 409), r.text
    if r.status_code == 201:
        _set(name, freigegeben=True, is_admin=admin)
        _mitglied(name)
    elif admin:
        _set(name, is_admin=True)
    uid = next(u["id"] for u in c.get("/api/users").json()["users"] if u["name"] == name)
    binden(c, uid)
    r = c.post("/api/users/waehlen", json={"user_id": uid})
    assert r.status_code == 200, r.text
    return r.json()["ich"]


def become_admin(c: TestClient) -> None:
    me = c.get("/api/users").json()["ich"]
    assert me is not None, "become_admin needs a logged-in browser"
    _set(me["name"], is_admin=True)
    assert c.get("/api/users").json()["admin"] is True
