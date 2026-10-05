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

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402
from sqlmodel import Session, select  # noqa: E402

from app import erfolge, tmdb  # noqa: E402
from app.config import settings  # noqa: E402
from app.db import engine  # noqa: E402
from app.main import app  # noqa: E402
from app.models import User  # noqa: E402
from app.routers import kino, users, zugang  # noqa: E402


@pytest.fixture
def client():
    """A fresh database (seeded by the lifespan) and an anonymous browser."""
    # A fresh file per test: the lifespan migrates it from scratch, like a new install.
    engine.dispose()
    for suffix in ("", "-wal", "-shm"):
        Path(f"{_tmp}/test.db{suffix}").unlink(missing_ok=True)
    shutil.rmtree(f"{_tmp}/media", ignore_errors=True)
    users._fails.clear()
    zugang._fehl_ip.clear()
    zugang._fehl_alle.clear()
    kino._presence.clear()
    tmdb._cache.clear()
    kino._audience.clear()
    kino._seit.clear()
    kino._gezaehlt.clear()
    kino._sender = None
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


def login(c: TestClient, name: str, *, admin: bool = False) -> dict:
    """Create (or reuse) an approved name and use it in this browser.

    The first name of a fresh database becomes admin by itself; tests say
    explicitly who is admin instead (`admin=True` or `become_admin`).
    """
    r = c.post("/api/users", json={"name": name})
    assert r.status_code in (201, 409), r.text
    if r.status_code == 201:
        _set(name, freigegeben=True, is_admin=admin)
    elif admin:
        _set(name, is_admin=True)
    uid = next(u["id"] for u in c.get("/api/users").json()["users"] if u["name"] == name)
    r = c.post("/api/users/waehlen", json={"user_id": uid})
    assert r.status_code == 200, r.text
    return r.json()["ich"]


def become_admin(c: TestClient) -> None:
    me = c.get("/api/users").json()["ich"]
    assert me is not None, "become_admin needs a logged-in browser"
    _set(me["name"], is_admin=True)
    assert c.get("/api/users").json()["admin"] is True


def set_door(c: TestClient, film: int = 948, frage: str = "Unser erster Film?") -> None:
    """Set the access question (c must be an admin)."""
    r = c.put("/api/admin/zugang", json={"frage": frage, "movie_id": film, "titel": "x"})
    assert r.status_code == 200, r.text
