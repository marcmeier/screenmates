"""The operator's command line (python -m app.cli …), English names and the old German ones."""

import pytest

from app import cli

from .conftest import SETUP, login


def test_setup_names_admin_login_and_invite(client, capsys):
    assert cli.main(["setup"]) == 0
    assert SETUP in capsys.readouterr().out
    login(client, "marc", admin=True)
    login(client, "lena")
    assert cli.main(["einrichtung"]) == 1  # German alias; names exist now
    capsys.readouterr()

    assert cli.main(["names"]) == 0
    out = capsys.readouterr().out
    assert "marc" in out and "lena" in out and "admin" in out
    assert cli.main(["admin", "lena"]) == 0
    assert "“lena” is admin now." in capsys.readouterr().out
    assert cli.main(["admin", "nobody"]) == 1

    assert cli.main(["login", "lena"]) == 0
    code = capsys.readouterr().out.split(": ")[1].split()[0]
    assert client.post("/api/login", json={"code": code}).json()["ich"]["name"] == "lena"

    assert cli.main(["invite"]) == 0
    token = capsys.readouterr().out.rsplit("/", 1)[1].strip()
    assert client.post("/api/zugang", json={"token": token}).status_code == 200
    assert cli.main(["einladung", "1"]) == 0


def test_the_about_page_links_this_installations_source(client, monkeypatch):
    from app.config import settings

    assert client.get("/api/ueber").json()["repo"] == "https://github.com/marcmeier/screenmates"
    monkeypatch.setattr(settings, "source_url", "https://git.example.org/fork")
    assert client.get("/api/ueber").json()["repo"] == "https://git.example.org/fork"


@pytest.mark.parametrize("argv", [[], ["help"], ["admin"], ["names", "x"], ["invite", "1", "2"]])
def test_wrong_use_prints_the_help(argv, capsys):
    assert cli.main(argv) == 2
    assert "python -m app.cli names" in capsys.readouterr().err
