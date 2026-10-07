"""Push notifications: keys, devices, choices, who gets what, reminders, and delivery."""

import base64
import json
from datetime import UTC, datetime, timedelta

import pytest
from sqlmodel import Session, select

from app import push
from app.db import engine
from app.models import Abend, KinoState, PushAbo

from .conftest import gesendet, login
from .test_umfrage import PUSHDIENST, empfaenger, geraet, in_tagen


@pytest.fixture
def runde(client, browser):
    login(client, "marc", admin=True)
    client.me = client.get("/api/users").json()["ich"]
    leute = {"marc": client}
    for name in ("lena", "kim"):
        c = browser()
        c.me = login(c, name)
        leute[name] = c
    for name, c in leute.items():
        geraet(c, name)
    gesendet.clear()
    return leute


def test_the_public_key_is_an_uncompressed_p256_point_and_stays(client):
    login(client, "marc")
    k = client.get("/api/push").json()["schluessel"]
    raw = base64.urlsafe_b64decode(k + "=" * (-len(k) % 4))
    assert len(raw) == 65 and raw[0] == 4
    assert client.get("/api/push").json()["schluessel"] == k


def test_devices_belong_to_whoever_is_logged_in_on_them(client, browser):
    login(client, "marc")
    lena = browser()
    login(lena, "lena")
    keys = {"p256dh": "B" * 87, "auth": "A" * 22}
    for fremd in (
        "http://fcm.googleapis.com/fcm/send/x",  # not https
        "https://intern.example/fcm.googleapis.com/x",  # the host counts, not the path
        "https://fcm.googleapis.com.boese.example/x",
        "https://fcm.googleapis.com:8443/x",
        "https://localhost/x",
    ):
        r = client.post("/api/push/abo", json={"endpoint": fremd, "keys": keys})
        assert r.status_code == 422, fremd
    for bekannt in ("https://updates.push.services.mozilla.com/wpush/v2/x", "https://web.push.apple.com/x"):
        assert client.post("/api/push/abo", json={"endpoint": bekannt, "keys": keys}).status_code == 200
    client.post("/api/push/abmelden", json={"endpoint": "https://updates.push.services.mozilla.com/wpush/v2/x"})
    client.post("/api/push/abmelden", json={"endpoint": "https://web.push.apple.com/x"})
    geraet(client, "handy")
    assert client.get("/api/push").json()["geraete"] == 1
    geraet(lena, "handy")  # the same browser, now logged in as lena
    assert client.get("/api/push").json()["geraete"] == 0
    assert lena.get("/api/push").json()["geraete"] == 1
    lena.post("/api/push/abmelden", json={"endpoint": f"{PUSHDIENST}handy"})
    assert lena.get("/api/push").json()["geraete"] == 0


def test_at_most_ten_devices_the_oldest_goes(client):
    login(client, "marc")
    for i in range(12):
        geraet(client, f"g{i}")
    assert client.get("/api/push").json()["geraete"] == 10
    with Session(engine) as s:
        endpoints = {a.endpoint for a in s.exec(select(PushAbo)).all()}
    assert f"{PUSHDIENST}g0" not in endpoints and f"{PUSHDIENST}g11" in endpoints


def test_choices_and_the_test_message(client, monkeypatch):
    login(client, "marc")
    assert client.post("/api/push/test").status_code == 409  # no device yet
    geraet(client, "marc")
    arten = {a["key"]: a["an"] for a in client.get("/api/push").json()["arten"]}
    assert arten == dict.fromkeys(push.ARTEN, True)
    r = client.put("/api/push/arten", json={"arten": {"kino": False}}).json()
    assert {a["key"]: a["an"] for a in r["arten"]}["kino"] is False
    assert client.put("/api/push/arten", json={"arten": {"quatsch": True}}).status_code == 422
    # The test message is delivered right away, and its result is reported.
    zugestellt = []
    monkeypatch.setattr(push, "zustellen", lambda z: zugestellt.append(z) or True)
    assert client.post("/api/push/test").json() == {"geraete": 1, "von": 1}
    assert zugestellt[0].daten["tag"] == "test"
    monkeypatch.setattr(push, "zustellen", lambda z: False)
    assert client.post("/api/push/test").status_code == 502


def test_a_new_date_tells_everyone_else_who_wants_it(runde):
    lena, kim, marc = runde["lena"], runde["kim"], runde["marc"]
    kim.put("/api/push/arten", json={"arten": {"termin": False}})
    marc.put("/api/termin", json={"termin": in_tagen(3), "notiz": "bei Marc"})
    assert empfaenger("termin") == {"lena"}
    z = gesendet[0]
    assert z.daten["titel"].startswith("📅 Filmabend steht")
    assert z.daten["text"].startswith("marc: ") and "Uhr · bei Marc" in z.daten["text"]
    gesendet.clear()
    marc.put("/api/termin", json={"termin": in_tagen(3), "notiz": "bei Lena"})  # same time: no news
    assert gesendet == []
    lena.put("/api/termin", json={"termin": in_tagen(4)})
    assert "verschoben" in gesendet[0].daten["titel"]


def test_live_things_only_reach_those_without_an_open_app(runde):
    lena, marc = runde["lena"], runde["marc"]
    marc.post("/api/suggestions", json={"movie_id": 694})
    lena.get("/api/live")  # lena has screenmates open
    assert marc.post("/api/kiste").status_code == 201
    assert empfaenger("kiste") == {"kim"}
    assert gesendet[0].dringend is True


def test_a_baton_offer_reaches_the_person_asked(runde):
    marc, kim = runde["marc"], runde["kim"]
    marc.put("/api/termin", json={"termin": in_tagen(2)})
    gesendet.clear()
    marc.post("/api/gastgeber/uebergeben", json={"an": kim.me["id"]})
    assert empfaenger("stab") == {"kim"}


def test_a_reply_reaches_the_author_but_not_yourself(runde):
    lena, marc = runde["lena"], runde["marc"]
    w = marc.post("/api/watched", json={"movie_id": 694}).json()["id"]
    note = lena.post(f"/api/watched/{w}/notes", json={"text": "Gänsehaut!"}).json()["notes"][0]["id"]
    marc.post(f"/api/watched/{w}/notes", json={"text": "Absolut", "parent_id": note})
    assert empfaenger("antwort") == {"lena"}
    assert gesendet[0].daten["titel"].startswith("💬 marc hat dir geantwortet – Shining")
    gesendet.clear()
    lena.post(f"/api/watched/{w}/notes", json={"text": "Selbstgespräch", "parent_id": note})
    assert gesendet == []


def test_going_live_tells_the_group_once(runde, db, kino_on):
    from app.routers import kino

    db.expire_all()
    st = kino._state(db, 1)
    kino._saele[1].sender = runde["marc"].me["id"]
    st.titel = "Halloween"
    db.add(st)
    db.commit()
    publish = {"action": "publish", "path": "kino-1", "token": st.secret}
    assert runde["marc"].post("/api/kino/mtx-auth", json=publish).status_code == 200
    assert empfaenger("kino") == {"lena", "kim"}
    assert "„Halloween“" in gesendet[0].daten["text"] and gesendet[0].daten["url"] == "/#/kino"
    gesendet.clear()
    runde["marc"].post("/api/kino/mtx-auth", json=publish)  # OBS reconnects
    assert gesendet == []
    assert isinstance(db.get(KinoState, 1), KinoState)


def test_the_reminder_goes_out_once_and_not_to_those_who_said_no(runde):
    kim, marc = runde["kim"], runde["marc"]
    marc.put("/api/termin", json={"termin": in_tagen(2), "notiz": "bei Marc"})
    kim.put("/api/dabei", json={"antwort": "nein"})
    gesendet.clear()
    with Session(engine) as s:
        termin = s.get(Abend, 1).termin.replace(tzinfo=UTC)
        assert push.faellige_erinnerungen(s, jetzt=termin - timedelta(hours=4)) == 0  # too early
        assert push.faellige_erinnerungen(s, jetzt=termin - timedelta(hours=2)) == 2
        assert push.faellige_erinnerungen(s, jetzt=termin - timedelta(hours=1)) == 0  # once
    assert empfaenger("erinnerung") == {"marc", "lena"}
    assert "bei Marc" in gesendet[0].daten["text"]


def test_just_before_the_start_those_coming_but_not_in_the_app_hear_it(runde):
    kim, lena, marc = runde["kim"], runde["lena"], runde["marc"]
    marc.put("/api/termin", json={"termin": in_tagen(2), "notiz": "bei Marc"})
    lena.put("/api/dabei", json={"antwort": "ja"})
    kim.put("/api/dabei", json={"antwort": "vielleicht"})
    marc.put("/api/dabei", json={"antwort": "nein"})
    lena.get("/api/live")  # lena already has screenmates open
    gesendet.clear()
    with Session(engine) as s:
        termin = s.get(Abend, 1).termin.replace(tzinfo=UTC)
        assert push.los_meldungen(s, jetzt=termin - timedelta(minutes=20)) == 0  # too early
        assert push.los_meldungen(s, jetzt=termin - timedelta(minutes=3)) == 1
        assert push.los_meldungen(s, jetzt=termin) == 0  # once
    assert empfaenger("los") == {"kim"}
    assert gesendet[0].dringend is True and "bei Marc" in gesendet[0].daten["text"]


def test_a_date_set_shortly_before_needs_no_extra_reminder(runde):
    marc = runde["marc"]
    bald = (datetime.now(UTC) + timedelta(hours=1)).replace(microsecond=0)
    marc.put("/api/termin", json={"termin": bald.isoformat()})
    with Session(engine) as s:
        assert push.faellige_erinnerungen(s) == 0


@pytest.mark.parametrize(
    ("einstellung", "gesendet_als"),
    [
        ("https://github.com/marcmeier/screenmates", "https://github.com"),
        ("https://screenmates.example.org/", "https://screenmates.example.org"),
        ("mailto:admin@example.org", "mailto:admin@example.org"),
    ],
)
def test_the_contact_is_one_the_push_services_accept(client, monkeypatch, einstellung, gesendet_als):
    """Signed for real (not mocked): py_vapid refuses a contact URL with a path."""
    from py_vapid import Vapid

    from app.config import settings

    monkeypatch.setattr(settings, "push_contact", einstellung)
    assert push.kontakt() == gesendet_als
    with Session(engine) as s:
        v = Vapid.from_pem(push.privater_schluessel(s).encode())
    kopf = v.sign({"sub": push.kontakt(), "aud": "https://fcm.googleapis.com"})
    assert kopf["Authorization"].startswith("vapid t=")


def test_the_contact_falls_back_to_public_url_and_reads_the_old_name(monkeypatch):
    from app.config import Settings, settings

    monkeypatch.setattr(settings, "push_contact", "")
    monkeypatch.setattr(settings, "public_url", "https://movies.example.org/")
    assert push.kontakt() == "https://movies.example.org"
    monkeypatch.setenv("PUSH_KONTAKT", "mailto:old@example.org")
    assert Settings().push_contact == "mailto:old@example.org"


def test_delivery_really_builds_the_request(runde, monkeypatch):
    """The whole pywebpush path (keys, encryption, VAPID); only the HTTP post is caught."""
    import requests
    from cryptography.hazmat.primitives import serialization
    from cryptography.hazmat.primitives.asymmetric import ec

    browser = ec.generate_private_key(ec.SECP256R1()).public_key()
    p256dh = (
        base64.urlsafe_b64encode(
            browser.public_bytes(serialization.Encoding.X962, serialization.PublicFormat.UncompressedPoint)
        )
        .rstrip(b"=")
        .decode()
    )
    auth = base64.urlsafe_b64encode(b"0123456789abcdef").rstrip(b"=").decode()
    gepostet = []

    def post(self, url, data=None, headers=None, timeout=None, **kw):
        gepostet.append((url, headers))
        r = requests.Response()
        r.status_code = 201
        return r

    monkeypatch.setattr(requests.Session, "post", post)
    monkeypatch.setattr(requests, "post", lambda url, **kw: post(None, url, **kw))
    with Session(engine) as s:
        schluessel = push.privater_schluessel(s)
    push.zustellen(push.Zustellung(f"{PUSHDIENST}x", p256dh, auth, {"titel": "Hallo"}, 60, False, schluessel))
    ((url, headers),) = gepostet
    assert url == f"{PUSHDIENST}x"
    assert headers["Authorization"].startswith("vapid t=") and headers["Content-Encoding"] == "aes128gcm"


class _Antwort:
    def __init__(self, status):
        self.status_code = status
        self.text = ""


def test_delivery_signs_encrypts_and_forgets_gone_devices(runde, monkeypatch):
    import pywebpush

    with Session(engine) as s:
        schluessel = push.privater_schluessel(s)
    aufrufe = []
    monkeypatch.setattr(pywebpush, "webpush", lambda *a, **kw: aufrufe.append((a, kw)))
    z = push.Zustellung(f"{PUSHDIENST}lena", "B" * 87, "A" * 22, {"titel": "Hallo"}, 60, True, schluessel)
    push.zustellen(z)
    (info, daten), kw = aufrufe[0]
    assert info == {"endpoint": z.endpoint, "keys": {"p256dh": z.p256dh, "auth": z.auth}}
    assert json.loads(daten) == {"titel": "Hallo"}
    assert kw["vapid_claims"] == {"sub": "https://github.com"}
    assert (kw["ttl"], kw["headers"]) == (60, {"Urgency": "high"})

    def weg(*a, **kw):
        raise pywebpush.WebPushException("gone", response=_Antwort(410))

    monkeypatch.setattr(pywebpush, "webpush", weg)
    push.zustellen(z)
    assert runde["lena"].get("/api/push").json()["geraete"] == 0
    assert runde["kim"].get("/api/push").json()["geraete"] == 1
