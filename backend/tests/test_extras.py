"""Sidebar statistics, the about page, and personal themes."""

from app.routers import statistik

from .conftest import become_admin, login


def test_statistics_are_totals_only(client, browser):
    statistik._cache = (0.0, [])
    login(client, "marc")
    client.post("/api/watched", json={"movie_id": 694})
    fakten = {f["text"]: f["wert"] for f in client.get("/api/statistik").json()["fakten"]}
    assert fakten["Film gemeinsam geschaut"] == "1"  # singular for one
    assert fakten["Person dabei"] == "1"
    assert "Herzen verteilt" not in fakten  # zeros are left out
    assert not any("marc" in str(v).lower() for v in fakten.items())


def test_kino_traffic_is_added_up_across_sessions(db):
    statistik._zuletzt.clear()
    statistik.verbuchen(db, [{"id": "a", "bytesSent": 1000, "rtpPacketsSent": 100, "rtpPacketsLost": 1}])
    statistik.verbuchen(
        db,
        [{"id": "a", "bytesSent": 3000, "rtpPacketsSent": 300, "rtpPacketsLost": 2}, {"id": "b", "bytesReceived": 500}],
    )
    statistik.verbuchen(db, [])  # both ended: nothing new, nothing lost
    statistik.verbuchen(db, [{"id": "c", "bytesSent": 10}])
    assert statistik.zaehler(db, "kino_bytes") == 3510
    assert statistik.zaehler(db, "kino_pakete") == 300
    assert statistik.zaehler(db, "kino_verloren") == 2
    statistik._cache = (0.0, [])
    texte = [f["text"] for f in statistik.fakten(db)]
    assert "im Kino gestreamt" in texte
    assert any(t.startswith("Pakete beim Streamen verloren") for t in texte)


def test_about_page_is_public_and_admins_edit_it(client, browser):
    login(client, "marc")
    become_admin(client)
    assert client.put("/api/admin/seiten/impressum", json={"text": "# Impressum\\nMax"}).status_code == 200
    assert client.put("/api/admin/seiten/quatsch", json={"text": "x"}).status_code == 404
    fremd = browser()  # no invitation: the app itself stays closed …
    assert fremd.get("/api/users").status_code == 423
    r = fremd.get("/api/ueber")  # … the about page doesn't
    assert r.status_code == 200
    assert r.json()["texte"]["impressum"].startswith("# Impressum")
    assert r.json()["texte"]["spenden"] == ""
    lena = browser()
    login(lena, "lena")
    assert lena.put("/api/admin/seiten/impressum", json={"text": "x"}).status_code == 403


def test_design_is_personal(client, browser):
    login(client, "marc")
    assert client.get("/api/users").json()["ich"]["design"] == {}
    assert client.put("/api/users/me/design", json={"theme": "neon", "schrift": "grotesk"}).status_code == 200
    assert client.get("/api/users").json()["ich"]["design"] == {"theme": "neon", "schrift": "grotesk"}
    assert client.put("/api/users/me/design", json={"theme": "pink-hell", "schrift": "inter"}).status_code == 422
    lena = browser()
    login(lena, "lena")
    assert lena.get("/api/users").json()["ich"]["design"] == {}


def test_donation_accounts_are_names_turned_into_links(client, browser):
    login(client, "marc")
    become_admin(client)
    assert client.put("/api/admin/seiten/kofi", json={"text": "https://ko-fi.com/marcmeier/"}).status_code == 200
    assert client.put("/api/admin/seiten/paypal", json={"text": "@MarcMeier"}).status_code == 200
    konten = browser().get("/api/ueber").json()["konten"]
    assert konten["kofi"] == {"label": "Ko-fi", "name": "marcmeier", "url": "https://ko-fi.com/marcmeier"}
    assert konten["paypal"]["url"] == "https://paypal.me/MarcMeier"
    assert client.put("/api/admin/seiten/paypal", json={"text": "www.paypal.com/paypalme/marc"}).status_code == 200
    assert client.get("/api/ueber").json()["konten"]["paypal"]["name"] == "marc"
    for boese in ("javascript:alert(1)", "https://evil.example/x", "marc meier"):
        assert client.put("/api/admin/seiten/kofi", json={"text": boese}).status_code == 422
    assert client.put("/api/admin/seiten/kofi", json={"text": ""}).status_code == 200  # empty removes it
    assert "kofi" not in client.get("/api/ueber").json()["konten"]


def test_language_is_personal_and_keeps_the_look(client, browser):
    login(client, "marc")
    client.put("/api/users/me/design", json={"theme": "neon", "schrift": "grotesk"})
    assert client.put("/api/users/me/sprache", json={"sprache": "en"}).status_code == 200
    assert client.get("/api/users").json()["ich"]["design"] == {"theme": "neon", "schrift": "grotesk", "sprache": "en"}
    client.put("/api/users/me/design", json={"theme": "wald", "schrift": "grotesk"})
    assert client.get("/api/users").json()["ich"]["design"]["sprache"] == "en"
    assert client.put("/api/users/me/sprache", json={"sprache": "fr"}).status_code == 422
