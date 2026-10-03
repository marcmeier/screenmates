"""Kino: who may send and watch, the MediaMTX auth hook, and the WHIP/WHEP relay."""

import httpx
import respx

from app.models import KinoState
from app.routers import kino

from .conftest import become_host, login

MTX = "http://mtx:8889"
API = "http://mtx:9997"
SDP = "v=0\r\no=- 0 0 IN IP4 127.0.0.1\r\n"


def secret(db) -> str:
    """The relay secret, creating the Kino state on first use."""
    db.expire_all()
    return kino._state(db).secret


def offline():
    respx.get(f"{API}/v3/paths/get/kino").mock(return_value=httpx.Response(404))


def live(source_id="s1"):
    respx.get(f"{API}/v3/paths/get/kino").mock(
        return_value=httpx.Response(
            200,
            json={
                "ready": True,
                "readyTime": "2026-10-03T20:00:00Z",
                "source": {"type": "webRTCSession", "id": source_id},
            },
        )
    )


def test_disabled_without_mediamtx(client):
    assert client.get("/api/kino").json() == {"enabled": False, "live": False}
    login(client, "marc")
    assert client.post("/api/kino/whep", content=SDP).status_code == 503


@respx.mock
def test_status_offline_and_live(client, kino_on):
    offline()
    assert client.get("/api/kino").json()["live"] is False
    live()
    s = client.get("/api/kino").json()
    assert s["live"] is True
    assert s["seit"] == "2026-10-03T20:00:00Z"


@respx.mock
def test_watching_needs_a_name_and_is_relayed_with_the_secret(client, kino_on, db):
    route = respx.post(f"{MTX}/kino/whep").mock(
        return_value=httpx.Response(
            201,
            content=b"answer",
            headers={
                "content-type": "application/sdp",
                "location": "/kino/whep/abc-123",
                "etag": "*",
                "link": '<stun:stun.l.google.com:19302>; rel="ice-server"',
            },
        )
    )
    assert client.post("/api/kino/whep", content=SDP).status_code == 401
    login(client, "lena")
    r = client.post("/api/kino/whep", content=SDP, headers={"content-type": "application/sdp"})
    assert r.status_code == 201
    assert r.text == "answer"
    assert r.headers["location"] == "/api/kino/sitzung/whep/abc-123"
    assert "ice-server" in r.headers["link"]
    sent = route.calls.last.request
    assert sent.headers["authorization"] == f"Bearer {secret(db)}"
    assert sent.headers["content-type"] == "application/sdp"
    assert sent.content == SDP.encode()


@respx.mock
def test_publishing_is_host_or_obs_key_only(client, browser, kino_on):
    respx.post(f"{MTX}/kino/whip").mock(
        return_value=httpx.Response(201, content=b"a", headers={"location": "/kino/whip/x1"})
    )
    login(client, "marc")
    assert client.post("/api/kino/whip", content=SDP).status_code == 403
    become_host(client)
    assert client.post("/api/kino/whip", content=SDP).status_code == 201

    key = client.get("/api/kino/obs").json()["key"]
    obs = browser()  # OBS has no session, only the key
    assert obs.post("/api/kino/whip", content=SDP, headers={"authorization": "Bearer falsch"}).status_code == 403
    assert obs.post("/api/kino/whip", content=SDP, headers={"authorization": f"Bearer {key}"}).status_code == 201


def test_obs_key_is_host_only_and_rotates(client, browser, kino_on):
    login(client, "marc")
    assert client.get("/api/kino/obs").status_code == 403
    become_host(client)
    first = client.get("/api/kino/obs").json()
    assert first["server"].endswith("/api/kino/whip")
    second = client.post("/api/kino/obs/neu").json()["key"]
    assert second != first["key"]
    assert client.get("/api/kino/obs").json()["key"] == second


def test_mtx_auth_accepts_only_our_secret(client, db, kino_on):
    good = secret(db)
    ok = {"action": "read", "path": "kino", "token": good, "protocol": "webrtc"}
    assert client.post("/api/kino/mtx-auth", json=ok).status_code == 200
    assert client.post("/api/kino/mtx-auth", json=ok | {"token": "nope"}).status_code == 401
    assert client.post("/api/kino/mtx-auth", json=ok | {"path": "other"}).status_code == 401
    assert client.post("/api/kino/mtx-auth", json=ok | {"action": "playback"}).status_code == 401
    assert client.post("/api/kino/mtx-auth", content=b"not json").status_code == 400


def test_publish_starts_a_new_show(client, db, kino_on):
    login(client, "marc")
    client.post("/api/kino/da")
    assert kino._audience == {1}
    r = client.post("/api/kino/mtx-auth", json={"action": "publish", "path": "kino", "token": secret(db)})
    assert r.status_code == 200
    assert kino._audience == set()
    db.expire_all()
    assert db.get(KinoState, 1).gestartet is not None


@respx.mock
def test_presence_shows_viewers_while_live(client, browser, kino_on):
    live()
    marc = login(client, "marc")
    lena_c = browser()
    lena = login(lena_c, "lena")
    client.post("/api/kino/da")
    lena_c.post("/api/kino/da")
    s = client.get("/api/kino").json()
    assert s["zuschauer"] == sorted([marc["id"], lena["id"]])
    lena_c.delete("/api/kino/da")
    s = client.get("/api/kino").json()
    assert s["zuschauer"] == [marc["id"]]
    assert s["publikum"] == sorted([marc["id"], lena["id"]])  # who watched at all, for "gesehen"


def test_programm_is_host_only_and_links_catalogue_films(client, kino_on):
    login(client, "marc")
    assert client.post("/api/kino/programm", json={"titel": "x"}).status_code == 403
    become_host(client)
    assert client.post("/api/kino/programm", json={"titel": "Shining", "movie_id": 999999}).status_code == 422
    assert client.post("/api/kino/programm", json={"titel": " Shining ", "movie_id": 694}).status_code == 200
    with respx.mock:
        offline()
        s = client.get("/api/kino").json()
    assert (s["titel"], s["movie"]["id"]) == ("Shining", 694)


@respx.mock
def test_host_can_end_any_show(client, kino_on):
    live(source_id="obs-session")
    kick = respx.post(f"{API}/v3/webrtcsessions/kick/obs-session").mock(return_value=httpx.Response(200))
    login(client, "marc")
    assert client.delete("/api/kino").status_code == 403
    become_host(client)
    assert client.delete("/api/kino").status_code == 200
    assert kick.called


@respx.mock
def test_session_resources(client, kino_on):
    route = respx.delete(f"{MTX}/kino/whep/abc-123").mock(return_value=httpx.Response(200))
    assert client.delete("/api/kino/sitzung/whep/abc-123").status_code == 401
    login(client, "marc")
    assert client.delete("/api/kino/sitzung/whep/abc-123").status_code == 200
    assert route.called
    assert client.delete("/api/kino/sitzung/other/abc").status_code == 404
    # Traversal never reaches MediaMTX (rejected by routing or the id check).
    assert client.delete("/api/kino/sitzung/whep/..%2F..%2Fv3").status_code in (404, 405)
    assert client.delete("/api/kino/sitzung/whep/a.b").status_code == 404
    assert route.call_count == 1
    assert client.delete("/api/kino/sitzung/whip/abc-123").status_code == 403


@respx.mock
def test_mediamtx_down_is_503(client, kino_on):
    respx.post(f"{MTX}/kino/whep").mock(side_effect=httpx.ConnectError("down"))
    login(client, "marc")
    assert client.post("/api/kino/whep", content=SDP).status_code == 503


@respx.mock
def test_ending_twice_and_watching_nothing_are_handled(client, kino_on):
    respx.delete(f"{MTX}/kino/whep/gone-1").mock(return_value=httpx.Response(404))
    respx.post(f"{MTX}/kino/whep").mock(return_value=httpx.Response(404, json={"error": "no stream is available"}))
    login(client, "marc")
    assert client.delete("/api/kino/sitzung/whep/gone-1").status_code == 200
    r = client.post("/api/kino/whep", content=SDP)
    assert (r.status_code, r.json()["detail"]) == (404, "Gerade wird nichts übertragen.")
