"""German and English: what the server writes follows the app's language, or the reader's."""

from app import sprache
from app.texte_en import EN

from .conftest import gesendet, login
from .test_push import runde  # noqa: F401 - fixture
from .test_umfrage import in_tagen

EN_HEADER = {"X-Sprache": "en"}


def test_every_english_text_keeps_the_placeholders():
    import re

    for de, en in EN.items():
        assert sorted(re.findall(r"\{(\w+)\}", de)) == sorted(re.findall(r"\{(\w+)\}", en)), de


def test_errors_come_in_the_apps_language(client):
    r = client.put("/api/users/me/sprache", json={"sprache": "en"})
    assert r.json()["detail"] == "Bitte zuerst einen Namen wählen."
    r = client.put("/api/users/me/sprache", json={"sprache": "en"}, headers=EN_HEADER)
    assert r.json()["detail"] == "Please choose a name first."
    login(client, "marc")
    r = client.put("/api/users/me/sprache", json={"sprache": "fr"}, headers={"X-Sprache": "fr"})
    assert r.json()["detail"] == "Unbekannte Sprache."  # unknown language: German


def test_awards_shelves_and_facts_in_english(client):
    login(client, "marc")
    katalog = client.get("/api/erfolge", headers=EN_HEADER).json()["katalog"]
    stammgast = {e["key"]: e for e in katalog}["stammgast-2"]
    assert (stammgast["name"], stammgast["text"]) == ("Regular", "Attended 5 confirmed movie nights")
    deutsch = {e["key"]: e for e in client.get("/api/erfolge").json()["katalog"]}["stammgast-2"]
    assert deutsch["text"] == "Bei 5 bestätigten Filmabenden dabei"
    regale = client.get("/api/stoebern", headers=EN_HEADER).json()["regale"]
    assert regale[0]["titel"] == "Popular"
    fakten = client.get("/api/statistik", headers=EN_HEADER).json()["fakten"]
    assert any(f["text"] in ("films in the catalogue", "film in the catalogue") for f in fakten)
    assert any("Katalog" in f["text"] for f in client.get("/api/statistik").json()["fakten"])


def test_push_and_bell_speak_each_readers_language(runde):  # noqa: F811
    marc, lena = runde["marc"], runde["lena"]
    lena.put("/api/users/me/sprache", json={"sprache": "en"})
    gesendet.clear()
    marc.put("/api/termin", json={"termin": in_tagen(3), "notiz": "bei Marc"})
    an = {z.endpoint.rsplit("/", 1)[1]: z.daten for z in gesendet}
    assert an["lena"]["titel"].startswith("📅 Movie night is on")
    assert "Uhr" not in an["lena"]["text"] and "bei Marc" in an["lena"]["text"]
    assert an["kim"]["titel"].startswith("📅 Filmabend steht") and "Uhr" in an["kim"]["text"]
    glocke = lena.get("/api/glocke").json()
    eintraege = glocke["eintraege"]
    assert eintraege and eintraege[0]["titel"].startswith("📅 Movie night is on")


def test_the_language_is_back_to_german_after_a_request():
    assert sprache.aktuell() == "de"
    with sprache.als("en"):
        assert sprache.tr("Film nicht gefunden.") == "Film not found."
    assert sprache.tr("Film nicht gefunden.") == "Film nicht gefunden."
