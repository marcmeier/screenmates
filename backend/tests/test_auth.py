"""Who may do what: anonymous reads, user writes, admin-only administration."""

import pytest

from .conftest import become_admin, binden, login, rein


def test_reads_do_not_create_sessions(client, db):
    from sqlmodel import select

    from app.models import Session

    client.get("/api/users")
    client.get("/api/watched")
    assert db.exec(select(Session)).all() == []
    assert "screenmates_sid" not in client.cookies


@pytest.mark.parametrize(
    ("method", "path", "body"),
    [
        ("post", "/api/watched", {"movie_id": 694}),
        ("post", "/api/wishlist", {"movie_id": 694}),
        ("post", "/api/suggestions", {"movie_id": 694}),
        ("post", "/api/features", {"text": "x"}),
        ("post", "/api/dabei", None),
    ],
)
def test_writes_require_a_name(client, method, path, body):
    r = getattr(client, method)(path, json=body) if body else getattr(client, method)(path)
    assert r.status_code == 401


@pytest.mark.parametrize(
    ("method", "path", "body"),
    [
        ("put", "/api/info", {"text": "hi"}),
        ("delete", "/api/suggestions/alle", None),
        ("delete", "/api/dabei", None),
        ("get", "/api/admin/users", None),
        ("get", "/api/admin/gruppen/1/einladungen", None),
        ("post", "/api/admin/gruppen/1/einladungen", {}),
        ("get", "/api/admin/gruppen/1/anfragen", None),
        ("post", "/api/admin/users", {"name": "neu"}),
        ("post", "/api/sync", None),
    ],
)
def test_admin_requires_admin(client, method, path, body):
    login(client, "marc")
    r = client.request(method.upper(), path, json=body)
    assert r.status_code == 403


def test_duplicate_names_are_rejected(client):
    assert client.post("/api/users", json={"name": "marc"}).status_code == 201
    assert client.post("/api/users", json={"name": "marc"}).status_code == 409
    assert client.post("/api/users", json={"name": ""}).status_code == 422
    assert client.post("/api/users", json={"name": "x" * 31}).status_code == 422


def test_an_invitation_does_not_let_you_pick_someone_elses_name(client, browser):
    """The hole this closes: with any link, anyone could log in as the admin."""
    marc = login(client, "marc", admin=True)
    stranger = browser()
    assert stranger.post("/api/users/waehlen", json={"user_id": marc["id"]}).status_code == 423  # first the door
    rein(stranger)
    r = stranger.post("/api/users/waehlen", json={"user_id": marc["id"]})
    assert r.status_code == 403
    assert "Anmeldecode" in r.json()["detail"]
    assert stranger.get("/api/users").json()["ich"] is None
    assert stranger.get("/api/admin/users").status_code == 403


def test_a_name_belongs_to_the_browser_that_made_it(client):
    me = login(client, "marc")
    assert client.get("/api/users").json()["auf_geraet"] == [me["id"]]
    # Logging out keeps the name here: picking it again needs nothing else.
    client.post("/api/users/waehlen", json={"user_id": None})
    assert client.get("/api/users").json()["ich"] is None
    assert client.post("/api/users/waehlen", json={"user_id": me["id"]}).status_code == 200
    # Forgetting it does not.
    assert client.delete(f"/api/login/namen/{me['id']}").json() == {"namen": []}
    assert client.get("/api/users").json()["ich"] is None
    assert client.post("/api/users/waehlen", json={"user_id": me["id"]}).status_code == 403


def test_a_login_code_connects_another_device(client, browser):
    me = login(client, "marc")
    c = client.post("/api/login/code")
    assert c.status_code == 201
    code = c.json()["code"]
    assert len(code) == 9 and code[4] == "-" and c.json()["path"] == f"/#/login/{code}"

    phone = browser()  # no invitation: the code opens the door too
    r = phone.post("/api/login", json={"code": code.lower().replace("-", " ")})  # typed sloppily
    assert r.status_code == 200
    assert r.json()["ich"]["name"] == "marc"
    assert phone.get("/api/users").json()["ich"]["id"] == me["id"]
    assert client.get("/api/login").json() == {"geraete": 2}
    # Once only.
    assert browser().post("/api/login", json={"code": code}).status_code == 403


def test_codes_expire_and_are_stored_only_as_hashes(client, browser, db):
    from datetime import timedelta

    from sqlmodel import select

    from app.models import LoginCode, now

    login(client, "marc")
    code = client.post("/api/login/code").json()["code"]
    lc = db.exec(select(LoginCode)).one()
    assert code.replace("-", "") not in lc.code_hash
    lc.valid_until = now() - timedelta(seconds=1)
    db.add(lc)
    db.commit()
    assert browser().post("/api/login", json={"code": code}).status_code == 403


def test_wrong_codes_count_like_wrong_invitations(client, browser):
    login(client, "marc")
    b = browser()
    for _ in range(10):
        assert b.post("/api/login", json={"code": "AAAA-AAAA"}).status_code == 403
    code = client.post("/api/login/code").json()["code"]
    assert b.post("/api/login", json={"code": code}).status_code == 429
    assert b.post("/api/zugang", json={"token": "irgendwas-langes"}).status_code == 429


def test_signing_out_other_devices(client, browser):
    login(client, "marc")
    phone = browser()
    phone.post("/api/login", json={"code": client.post("/api/login/code").json()["code"]})
    assert client.post("/api/login/andere-abmelden").json() == {"abgemeldet": 1, "geraete": 1}
    assert phone.get("/api/users").json()["ich"] is None
    assert phone.get("/api/users").json()["auf_geraet"] == []
    assert client.get("/api/users").json()["ich"]["name"] == "marc"


def test_admins_make_login_codes_for_others(client, browser):
    login(client, "marc", admin=True)
    tom = client.post("/api/admin/users", json={"name": "Tom"}).json()  # made by an admin: on no device yet
    lena_b = browser()
    login(lena_b, "lena")
    assert lena_b.post(f"/api/admin/users/{tom['id']}/login-code").status_code == 403
    code = client.post(f"/api/admin/users/{tom['id']}/login-code").json()["code"]
    toms_phone = browser()
    assert toms_phone.post("/api/login", json={"code": code}).json()["ich"]["name"] == "Tom"


def test_names_waiting_for_approval_get_no_codes(client, browser):
    login(client, "marc", admin=True)
    b = browser()
    rein(b)
    lena = b.post("/api/users", json={"name": "Lena"}).json()
    assert client.post(f"/api/admin/users/{lena['id']}/login-code").status_code == 404


def test_delete_user_is_admin_only(client, browser):
    marc = login(client, "marc")
    other = browser()
    login(other, "lena")
    binden(other, marc["id"])  # lena's browser knows marc's name too: it goes with him
    assert other.delete(f"/api/users/{marc['id']}").status_code == 403
    become_admin(other)
    assert other.delete(f"/api/users/{marc['id']}").status_code == 200
    assert [u["name"] for u in other.get("/api/users").json()["users"]] == ["lena"]
    assert other.get("/api/users").json()["auf_geraet"] == [other.get("/api/users").json()["ich"]["id"]]
    # marc's session survives, but is no longer bound to a user.
    assert client.get("/api/users").json()["ich"] is None
