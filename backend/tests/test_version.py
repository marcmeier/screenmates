"""One version, written in one place, and a changelog section for it."""

import json
import re
from pathlib import Path

from app.version import __version__

ROOT = Path(__file__).resolve().parents[2]


def test_the_version_is_semver_and_has_its_changelog_section():
    assert re.fullmatch(r"\d+\.\d+\.\d+", __version__)
    neueste = re.search(r"^## (\d+\.\d+\.\d+) – \d{4}-\d{2}-\d{2}$", (ROOT / "CHANGELOG.md").read_text(), re.M)
    assert neueste and neueste.group(1) == __version__, "new version: add its section to CHANGELOG.md"


def test_nothing_else_carries_its_own_version_number():
    assert "version" not in json.loads((ROOT / "frontend/package.json").read_text())
    assert 'dynamic = ["version"]' in (ROOT / "backend/pyproject.toml").read_text()


def test_the_api_reports_it(client):
    assert client.get("/api/ueber").json()["version"] == __version__
    assert client.get("/openapi.json").json()["info"]["version"] == __version__
