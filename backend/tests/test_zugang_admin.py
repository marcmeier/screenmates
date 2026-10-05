"""The access question, name requests and admin rights per person."""

import sqlite3

import pytest
from alembic import command
from sqlmodel import select

from app import migrate
from app.models import Session, User

from .conftest import login, set_door


def users(c):
    return [u["name"] for u in c.get("/api/users").json()["users"]]


# --- admins ---------------------------------------------------------------------------


def test_the_first_name_of_a_fresh_install_becomes_admin(client):
    r = client.post("/api/users", json={"name": "Marc"}).json()
    assert r["admin"] is True and r["freigegeben"] is True
    client.post("/api/users/waehlen", json={"user_id": r["id"]})
    assert client.get("/api/users").json()["admin"] is True


def test_later_names_are_requests_until_an_admin_approves(client, browser):
    login(client, "marc", admin=True)
    neu = browser()
    r = neu.post("/api/users", json={"name": "Lena"})
    assert r.status_code == 201
    lena = r.json()
    assert lena["freigegeben"] is False and lena["admin"] is False
    # Not listed, can't be used yet.
    assert users(neu) == ["marc"]
    r = neu.post("/api/users/waehlen", json={"user_id": lena["id"]})
    assert r.status_code == 403
    assert "Freigabe" in r.json()["detail"]
    # The admin sees the request, with a count for the navigation.
    assert client.get("/api/users").json()["antraege"] == 1
    alle = client.get("/api/admin/users").json()["users"]
    assert [(u["name"], u["freigegeben"]) for u in alle] == [("Lena", False), ("marc", True)]
    # Approve: now it works.
    assert client.patch(f"/api/admin/users/{lena['id']}", json={"freigegeben": True}).json()["freigegeben"] is True
    assert neu.post("/api/users/waehlen", json={"user_id": lena["id"]}).status_code == 200
    assert client.get("/api/users").json()["antraege"] == 0


def test_a_request_can_be_turned_down(client, browser):
    login(client, "marc", admin=True)
    lena = browser().post("/api/users", json={"name": "Lena"}).json()
    assert client.delete(f"/api/users/{lena['id']}").status_code == 200
    assert [u["name"] for u in client.get("/api/admin/users").json()["users"]] == ["marc"]


def test_open_requests_are_capped(client, browser, monkeypatch):
    from app.routers import users as users_router

    monkeypatch.setattr(users_router, "MAX_ANTRAEGE", 2)
    login(client, "marc", admin=True)
    b = browser()
    assert b.post("/api/users", json={"name": "a"}).status_code == 201
    assert b.post("/api/users", json={"name": "b"}).status_code == 201
    assert b.post("/api/users", json={"name": "c"}).status_code == 429


def test_names_an_admin_creates_are_active_right_away(client):
    login(client, "marc", admin=True)
    r = client.post("/api/admin/users", json={"name": "Lena"})
    assert r.status_code == 201 and r.json()["freigegeben"] is True
    assert client.post("/api/users", json={"name": "Kim"}).json()["freigegeben"] is True
    assert users(client) == ["marc", "Lena", "Kim"]


def test_admins_can_rename_recolour_and_appoint(client, browser):
    login(client, "marc", admin=True)
    lena = login(browser(), "lena")
    r = client.patch(f"/api/admin/users/{lena['id']}", json={"name": "  Lena  M. ", "color": "#ABCDEF", "admin": True})
    assert r.status_code == 200
    assert (r.json()["name"], r.json()["color"], r.json()["admin"]) == ("Lena M.", "#abcdef", True)
    assert client.patch(f"/api/admin/users/{lena['id']}", json={"color": "rot"}).status_code == 422
    assert client.patch(f"/api/admin/users/{lena['id']}", json={"name": "marc"}).status_code == 409


def test_there_is_always_an_admin(client, browser):
    marc = login(client, "marc", admin=True)
    assert client.patch(f"/api/admin/users/{marc['id']}", json={"admin": False}).status_code == 409
    assert client.patch(f"/api/admin/users/{marc['id']}", json={"freigegeben": False}).status_code == 409
    assert client.delete(f"/api/users/{marc['id']}").status_code == 409
    # With a second admin, stepping down is fine.
    lena = login(browser(), "lena", admin=True)
    assert client.patch(f"/api/admin/users/{marc['id']}", json={"admin": False}).status_code == 200
    assert client.get("/api/users").json()["admin"] is False
    assert client.patch(f"/api/admin/users/{lena['id']}", json={"admin": False}).status_code == 403


def test_a_request_must_be_approved_before_becoming_admin(client, browser):
    login(client, "marc", admin=True)
    lena = browser().post("/api/users", json={"name": "Lena"}).json()
    assert client.patch(f"/api/admin/users/{lena['id']}", json={"admin": True}).status_code == 409


def test_logout_everywhere_ends_all_sessions_of_a_person(client, browser, db):
    login(client, "marc", admin=True)
    handy, laptop = browser(), browser()
    lena = login(handy, "lena")
    login(laptop, "lena")
    assert {u["name"]: u["sitzungen"] for u in client.get("/api/admin/users").json()["users"]}["lena"] == 2
    assert client.post(f"/api/admin/users/{lena['id']}/abmelden").json() == {"beendet": 2}
    assert handy.get("/api/users").json()["ich"] is None
    assert laptop.get("/api/users").json()["ich"] is None
    assert db.exec(select(Session).where(Session.user_id == lena["id"])).all() == []


def test_admins_reset_someones_film_password(client, browser):
    login(client, "marc", admin=True)
    lena_b = browser()
    lena = login(lena_b, "lena")
    lena_b.post(f"/api/users/{lena['id']}/schutz", json={"movie_id": 694})
    assert client.post(f"/api/users/{lena['id']}/schutz", json={"movie_id": None}).json() == {"hat_schutz": False}


def test_rights_follow_the_person_not_the_browser(client):
    login(client, "marc", admin=True)
    login(client, "lena")
    assert client.get("/api/users").json()["admin"] is False
    login(client, "marc")
    assert client.get("/api/users").json()["admin"] is True


# --- the access question ---------------------------------------------------------------


def test_without_a_question_screenmates_stays_open(client):
    assert client.get("/api/zugang").json() == {"gesperrt": False, "offen": True, "frage": ""}
    assert client.get("/api/users").status_code == 200


def test_the_door_closes_everything_for_new_browsers(client, browser):
    login(client, "marc", admin=True)
    set_door(client, film=948, frage="Welchen Film haben wir zuerst gesehen?")
    fremd = browser()
    assert fremd.get("/api/zugang").json() == {
        "gesperrt": True,
        "offen": False,
        "frage": "Welchen Film haben wir zuerst gesehen?",
    }
    for path in ("/api/users", "/api/watched", "/api/movies", "/api/search?q=alien", "/api/status", "/api/kino"):
        assert fremd.get(path).status_code == 423, path
    assert fremd.post("/api/users", json={"name": "x"}).status_code == 423
    # What the door itself needs stays open; the answer never leaves the server.
    assert fremd.get("/api/health").status_code == 200
    treffer = fremd.get("/api/zugang/suche", params={"q": "hallo"}).json()["results"]
    assert treffer and "gesehen" not in treffer[0]
    assert "948" not in fremd.get("/api/zugang").text
    # Whoever is logged in carries on.
    assert client.get("/api/users").status_code == 200


def test_the_right_film_opens_the_door(client, browser):
    login(client, "marc", admin=True)
    set_door(client, film=948)
    b = browser()
    r = b.post("/api/zugang", json={"movie_id": 694})
    assert r.status_code == 403
    assert b.post("/api/zugang", json={"movie_id": 948}).json() == {"offen": True}
    assert b.get("/api/zugang").json()["offen"] is True
    assert b.get("/api/users").status_code == 200
    # Requesting a name is the next step behind the door.
    assert b.post("/api/users", json={"name": "Lena"}).json()["freigegeben"] is False


def test_guessing_the_door_is_throttled(client, browser):
    login(client, "marc", admin=True)
    set_door(client, film=948)
    b = browser()
    for _ in range(5):
        assert b.post("/api/zugang", json={"movie_id": 1}).status_code == 403
    assert b.post("/api/zugang", json={"movie_id": 948}).status_code == 429


def test_logging_out_keeps_the_access(client):
    login(client, "marc", admin=True)
    set_door(client)
    client.post("/api/users/waehlen", json={"user_id": None})
    assert client.get("/api/users").status_code == 200


def test_admins_see_and_lift_the_door(client):
    login(client, "marc", admin=True)
    set_door(client, film=948, frage="  Unser   erster Film? ")
    z = client.get("/api/admin/zugang").json()
    assert (z["frage"], z["movie_id"]) == ("Unser erster Film?", 948)
    assert client.put("/api/admin/zugang", json={"frage": "", "movie_id": 948}).status_code == 422
    client.put("/api/admin/zugang", json={"frage": "", "movie_id": None})
    assert client.get("/api/zugang").json()["gesperrt"] is False


def test_obs_and_mediamtx_get_through_the_door(client, kino_on):
    login(client, "marc", admin=True)
    set_door(client)
    from fastapi.testclient import TestClient

    from app.main import app

    obs = TestClient(app)
    # Rejected by the Kino's own check (wrong key), not by the door.
    assert obs.post("/api/kino/whip", headers={"authorization": "Bearer falsch"}).status_code == 403
    assert obs.post("/api/kino/mtx-auth", json={"action": "read", "path": "kino"}).status_code != 423


# --- operator command and migration -----------------------------------------------------


def test_cli_appoints_an_admin(client, db, capsys):
    from app import cli

    login(client, "marc")
    assert cli.main(["admin", "marc"]) == 0
    db.expire_all()
    assert db.exec(select(User).where(User.name == "marc")).one().is_admin is True
    assert cli.main(["admin", "niemand"]) == 1
    assert cli.main(["zugang-aus"]) == 0
    assert "offen" in capsys.readouterr().out


def test_migration_keeps_logged_in_browsers_inside(tmp_path):
    u = f"sqlite:///{tmp_path / 'db.sqlite'}"
    cfg = migrate.alembic_config(u)
    command.upgrade(cfg, "0002")
    con = sqlite3.connect(tmp_path / "db.sqlite")
    con.execute("insert into user (id, name, color, dabei, created_at) values (1, 'Marc', '', 0, '2026-10-03')")
    con.execute("insert into session (sid, user_id, is_host, created_at) values ('a', 1, 1, '2026-10-03')")
    con.execute("insert into session (sid, user_id, is_host, created_at) values ('b', null, 0, '2026-10-03')")
    con.commit()
    con.close()
    migrate.upgrade(u)
    con = sqlite3.connect(tmp_path / "db.sqlite")
    assert con.execute("select sid, zugang from session order by sid").fetchall() == [("a", 1), ("b", 0)]
    assert con.execute("select name, is_admin, freigegeben from user").fetchall() == [("Marc", 0, 1)]
    con.close()


@pytest.mark.parametrize("path", ["/api/admin/users/999", "/api/admin/users/999/abmelden"])
def test_unknown_users_are_404(client, path):
    login(client, "marc", admin=True)
    r = client.patch(path, json={}) if path.endswith("999") else client.post(path)
    assert r.status_code == 404
