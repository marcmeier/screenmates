"""Security headers, how long a browser without a name keeps its access, and links the server writes."""

from datetime import timedelta

from sqlmodel import select

from app.config import settings
from app.models import Einladung, Session, now

from .conftest import login, rein


def test_security_headers_everywhere(client):
    for path in ("/api/health", "/api/zugang"):
        h = client.get(path).headers
        assert h["x-content-type-options"] == "nosniff"
        assert h["x-frame-options"] == "DENY"
        assert h["referrer-policy"] == "strict-origin-when-cross-origin"
        csp = h["content-security-policy"]
        assert "script-src 'self'" in csp and "frame-ancestors 'none'" in csp
        assert "frame-src https://www.youtube-nocookie.com" in csp


def test_every_response_has_a_fresh_nonce_for_proxies_that_inject_scripts(client):
    import re

    nonces = [
        re.search(r"script-src 'self' 'nonce-([\w-]+)'", client.get("/api/health").headers["content-security-policy"])[
            1
        ]
        for _ in range(2)
    ]
    assert len(nonces[0]) >= 16 and nonces[0] != nonces[1]


def test_the_policy_can_be_replaced_or_switched_off(client, monkeypatch):
    monkeypatch.setattr(settings, "content_security_policy", "default-src 'self'")
    assert client.get("/api/health").headers["content-security-policy"] == "default-src 'self'"
    monkeypatch.setattr(settings, "content_security_policy", "off")
    h = client.get("/api/health").headers
    assert "content-security-policy" not in h and h["x-content-type-options"] == "nosniff"


def test_the_api_docs_keep_working(client):
    h = client.get("/docs").headers
    assert "content-security-policy" not in h  # Swagger UI comes from a CDN
    assert h["x-content-type-options"] == "nosniff"


def test_a_withdrawn_or_expired_invitation_closes_the_door_for_browsers_without_a_name(client, browser, db):
    login(client, "marc", admin=True)
    gast = browser()
    token = rein(gast)
    assert gast.get("/api/movies").status_code == 200
    e = db.exec(select(Einladung).where(Einladung.token == token)).one()
    e.widerrufen = True
    db.add(e)
    db.commit()
    assert gast.get("/api/movies").status_code == 423
    assert gast.get("/api/zugang").json()["offen"] is False

    # With a name it doesn't matter what became of the link.
    lena = browser()
    token = rein(lena, direkt=True)
    lena.post("/api/users", json={"name": "Lena"})
    e = db.exec(select(Einladung).where(Einladung.token == token)).one()
    e.gueltig_bis = now() - timedelta(days=1)
    db.add(e)
    db.commit()
    assert lena.get("/api/movies").status_code == 200


def test_browsers_that_never_got_a_name_are_forgotten_after_a_month(client, browser, db):
    login(client, "marc", admin=True)
    alt = browser()
    rein(alt)
    sid = alt.cookies.get(settings.session_cookie)
    s = db.get(Session, sid)
    s.created_at = now() - timedelta(days=31)
    db.add(s)
    db.commit()
    rein(browser())  # making a new session tidies up
    db.expire_all()
    assert db.get(Session, sid) is None
    assert db.get(Session, client.cookies.get(settings.session_cookie)) is not None  # a name keeps it


def test_calendar_links_use_public_url_and_ignore_forwarded_host(client, monkeypatch):
    from datetime import UTC, datetime

    login(client, "marc")
    termin = (datetime.now(UTC) + timedelta(days=2)).isoformat()
    client.put("/api/termin", json={"termin": termin})
    text = client.get("/api/termin.ics", headers={"X-Forwarded-Host": "evil.example"}).text
    assert "evil.example" not in text and "URL:http://testserver/#/abend" in text
    monkeypatch.setattr(settings, "public_url", "https://movies.example.org/")
    assert "URL:https://movies.example.org/#/abend" in client.get("/api/termin.ics").text
