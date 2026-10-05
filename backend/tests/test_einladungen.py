"""Invite-only: the door, invitation links per group, requests and joining."""

from datetime import UTC, datetime, timedelta

from sqlmodel import select

from app.models import Einladung, Mitglied, User

from .conftest import login


def link(c, gid=1, **opt):
    r = c.post(f"/api/admin/gruppen/{gid}/einladungen", json=opt)
    assert r.status_code == 201, r.text
    return r.json()


def members(db, gid=1):
    db.expire_all()
    return {m.user_id for m in db.exec(select(Mitglied).where(Mitglied.gruppe_id == gid)).all()}


# --- the door --------------------------------------------------------------------------------


def test_a_fresh_install_is_open_until_the_first_name(client, browser):
    assert client.get("/api/zugang").json() == {"gesperrt": False, "offen": True, "einladung": None}
    assert client.get("/api/users").status_code == 200
    login(client, "marc", admin=True)
    fremd = browser()
    assert fremd.get("/api/zugang").json()["offen"] is False
    for path in ("/api/users", "/api/watched", "/api/movies", "/api/status", "/api/kino", "/api/erfolge"):
        assert fremd.get(path).status_code == 423, path
    assert fremd.post("/api/users", json={"name": "x"}).status_code == 423
    assert fremd.get("/api/health").status_code == 200
    # Whoever is logged in carries on, also after logging out.
    client.post("/api/users/waehlen", json={"user_id": None})
    assert client.get("/api/users").status_code == 200


def test_an_invitation_opens_the_door_and_says_where_to(client, browser):
    login(client, "marc", admin=True)
    e = link(client, notiz="Gruppenchat")
    b = browser()
    r = b.post("/api/zugang", json={"token": e["token"]})
    assert r.json() == {"offen": True, "einladung": {"gruppe": "Unsere Gruppe", "direkt": False}}
    assert b.get("/api/zugang").json()["einladung"] == {"gruppe": "Unsere Gruppe", "direkt": False}
    assert b.get("/api/movies").status_code == 200


def test_wrong_expired_withdrawn_or_used_up_invitations_dont_open(client, browser, db):
    login(client, "marc", admin=True)
    assert browser().post("/api/zugang", json={"token": "gibtsnicht123"}).status_code == 403
    alt = link(client, tage=1)
    e = db.get(Einladung, alt["id"])
    e.gueltig_bis = datetime.now(UTC) - timedelta(minutes=1)
    db.add(e)
    db.commit()
    assert browser().post("/api/zugang", json={"token": alt["token"]}).status_code == 403
    weg = link(client)
    client.delete(f"/api/admin/einladungen/{weg['id']}")
    assert browser().post("/api/zugang", json={"token": weg["token"]}).status_code == 403
    einmal = link(client, max_nutzungen=1, direkt=True)
    b = browser()
    b.post("/api/zugang", json={"token": einmal["token"]})
    assert b.post("/api/users", json={"name": "Lena"}).json()["freigegeben"] is True
    assert browser().post("/api/zugang", json={"token": einmal["token"]}).status_code == 403


def test_guessing_is_throttled(client, browser):
    login(client, "marc", admin=True)
    b = browser()
    for _ in range(10):
        assert b.post("/api/zugang", json={"token": "falsch-falsch"}).status_code == 403
    e = link(client)
    assert b.post("/api/zugang", json={"token": e["token"]}).status_code == 429


# --- new names via a link -------------------------------------------------------------------------


def test_a_direct_link_lets_new_people_straight_into_its_group(client, browser, db):
    login(client, "marc", admin=True)
    g2 = client.post("/api/admin/gruppen", json={"name": "Horror-Crew"}).json()["id"]
    e = link(client, g2, direkt=True)
    b = browser()
    b.post("/api/zugang", json={"token": e["token"]})
    u = b.post("/api/users", json={"name": "Kim"}).json()
    assert u["freigegeben"] is True
    assert u["id"] in members(db, g2) and u["id"] not in members(db, 1)
    assert b.post("/api/users/waehlen", json={"user_id": u["id"]}).status_code == 200
    assert b.get("/api/users").json()["gruppe"]["name"] == "Horror-Crew"
    db.expire_all()
    assert db.get(Einladung, e["id"]).nutzungen == 1


def test_a_request_link_waits_for_an_admin_of_that_group(client, browser, db):
    login(client, "marc", admin=True)
    g2 = client.post("/api/admin/gruppen", json={"name": "Horror-Crew"}).json()["id"]
    kim = browser()
    kim_me = login(kim, "kim")
    client.put(f"/api/admin/gruppen/{g2}/mitglieder/{kim_me['id']}", json={"admin": True})  # kim runs group 2
    e = link(kim, g2)
    neu = browser()
    neu.post("/api/zugang", json={"token": e["token"]})
    tom = neu.post("/api/users", json={"name": "Tom"}).json()
    assert tom["freigegeben"] is False
    assert [a["name"] for a in kim.get(f"/api/admin/gruppen/{g2}/anfragen").json()["anfragen"]] == ["Tom"]
    assert kim.get("/api/admin/gruppen/1/anfragen").status_code == 403  # not kim's group
    # The group admin decides; no server admin needed.
    assert kim.post(f"/api/admin/gruppen/{g2}/anfragen/{tom['id']}", json={"annehmen": True}).status_code == 200
    assert tom["id"] in members(db, g2)
    assert neu.post("/api/users/waehlen", json={"user_id": tom["id"]}).status_code == 200


def test_a_rejected_request_is_gone(client, browser, db):
    login(client, "marc", admin=True)
    e = link(client)
    b = browser()
    b.post("/api/zugang", json={"token": e["token"]})
    tom = b.post("/api/users", json={"name": "Tom"}).json()
    client.post(f"/api/admin/gruppen/1/anfragen/{tom['id']}", json={"annehmen": False})
    db.expire_all()
    assert db.get(User, tom["id"]) is None


def test_server_admins_approving_puts_the_name_into_the_links_group(client, browser, db):
    login(client, "marc", admin=True)
    g2 = client.post("/api/admin/gruppen", json={"name": "Zwei"}).json()["id"]
    e = link(client, g2)
    b = browser()
    b.post("/api/zugang", json={"token": e["token"]})
    tom = b.post("/api/users", json={"name": "Tom"}).json()
    client.patch(f"/api/admin/users/{tom['id']}", json={"freigegeben": True})
    assert tom["id"] in members(db, g2)


# --- people who already have a name ---------------------------------------------------------------


def test_a_name_joins_another_group_with_a_link(client, browser, db):
    login(client, "marc", admin=True)
    g2 = client.post("/api/admin/gruppen", json={"name": "Zwei"}).json()["id"]
    lena = browser()
    me = login(lena, "lena")
    direkt = link(client, g2, direkt=True)
    assert lena.post("/api/einladungen/annehmen", json={"token": direkt["token"]}).json()["status"] == "aufgenommen"
    assert me["id"] in members(db, g2)
    assert lena.post("/api/einladungen/annehmen", json={"token": direkt["token"]}).json()["status"] == "mitglied"


def test_joining_by_request(client, browser, db):
    login(client, "marc", admin=True)
    g2 = client.post("/api/admin/gruppen", json={"name": "Zwei"}).json()["id"]
    lena = browser()
    me = login(lena, "lena")
    e = link(client, g2)
    assert lena.post("/api/einladungen/annehmen", json={"token": e["token"]}).json()["status"] == "angefragt"
    assert me["id"] not in members(db, g2)
    anfragen = client.get(f"/api/admin/gruppen/{g2}/anfragen").json()["anfragen"]
    assert [(a["user_id"], a["neu"]) for a in anfragen] == [(me["id"], False)]
    client.post(f"/api/admin/gruppen/{g2}/anfragen/{me['id']}", json={"annehmen": True})
    assert me["id"] in members(db, g2)
    assert client.get(f"/api/admin/gruppen/{g2}/anfragen").json()["anfragen"] == []


# --- managing links ----------------------------------------------------------------------------------


def test_only_admins_of_the_group_manage_its_links(client, browser):
    login(client, "marc", admin=True)
    lena = browser()
    login(lena, "lena")
    assert lena.post("/api/admin/gruppen/1/einladungen", json={}).status_code == 403
    e = link(client, tage=None, max_nutzungen=5, notiz="  Familie ")
    assert (e["gueltig_bis"], e["max_nutzungen"], e["notiz"], e["gueltig"]) == (None, 5, "Familie", True)
    ids = [x["id"] for x in client.get("/api/admin/gruppen/1/einladungen").json()["einladungen"]]
    assert ids[0] == e["id"]  # newest first (lena's own invitation from the login helper is there too)
    assert lena.delete(f"/api/admin/einladungen/{e['id']}").status_code == 403
    client.delete(f"/api/admin/einladungen/{e['id']}")
    assert e["id"] not in [x["id"] for x in client.get("/api/admin/gruppen/1/einladungen").json()["einladungen"]]
