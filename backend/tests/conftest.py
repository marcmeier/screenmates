import os
import tempfile
from pathlib import Path

# Configure an isolated database and disable external services *before* the app
# (and its cached settings) is imported. Real env vars beat backend/.env.
_tmp = tempfile.mkdtemp(prefix="screenmates-test-")
os.environ["DATABASE_URL"] = f"sqlite:///{_tmp}/test.db"
os.environ["TMDB_API_KEY"] = ""
os.environ["LLM_API_KEY"] = ""

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402
from sqlmodel import Session  # noqa: E402

from app import tmdb  # noqa: E402
from app.config import settings  # noqa: E402
from app.db import engine  # noqa: E402
from app.main import app  # noqa: E402
from app.routers import kino, misc, users  # noqa: E402


@pytest.fixture
def client():
    """A fresh database (seeded by the lifespan) and an anonymous browser."""
    # A fresh file per test: the lifespan migrates it from scratch, like a new install.
    engine.dispose()
    for suffix in ("", "-wal", "-shm"):
        Path(f"{_tmp}/test.db{suffix}").unlink(missing_ok=True)
    users._fails.clear()
    misc._host_fails.clear()
    kino._presence.clear()
    tmdb._cache.clear()
    kino._audience.clear()
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


def login(c: TestClient, name: str) -> dict:
    r = c.post("/api/users", json={"name": name})
    assert r.status_code in (201, 409), r.text
    uid = next(u["id"] for u in c.get("/api/users").json()["users"] if u["name"] == name)
    r = c.post("/api/users/waehlen", json={"user_id": uid})
    assert r.status_code == 200, r.text
    return r.json()["ich"]


def become_host(c: TestClient, film: int = 694) -> None:
    r = c.post("/api/host", json={"an": True, "movie_id": film})
    assert r.status_code == 200, r.text
    assert r.json()["host"] is True
