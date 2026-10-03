# Changelog

## Unveröffentlicht

### Behoben
- **Mit TMDB endeten Raster und Suche nach 20 Filmen**, obwohl es z. B. 320 Horrorfilme bei
  Netflix gibt: TMDB liefert 20 Filme pro Seite, die App fragte 24 an und hielt „weniger als
  gefragt" für das Ende. Jetzt meldet der Server, ob es weitergeht und wie viele es insgesamt sind.

### Verbessert
- Raster laden beim Scrollen von selbst nach („Mehr laden" bleibt als Knopf), und „Alle Filme"
  zeigt die Gesamtzahl („320 Filme").

## 0.5.0 – 2026-10-03

**Stöbern, losen, einladen:** „Finden" zeigt das Horror-Angebot von Netflix, Prime & Co. in
Regalen, die Filmabend-Kiste ersetzt das Glücksrad, und der Abend bekommt Termin, Einladungskarte
und Erinnerungen. Dazu schätzt screenmates, wem ein Film gefallen wird – ehrlich gemessen.

### Neu
- **Stöbern statt Suchen-müssen:** „Finden" startet mit Regalen wie bei einem Streamingdienst:
  „Läuft bei uns" (eure Abos), je ein Regal pro Dienst (Netflix, Prime Video, Disney+, Paramount+,
  Joyn, WOW … eure eigenen zuerst, mit „Euer Abo"), „Kostenlos streamen", „Neu erschienen",
  „Geheimtipps" und „Klassiker". Seitwärts wischen oder blättern, „Alle zeigen" öffnet das ganze
  Angebot im Raster.
- **„Alle Filme" mit Dienst-Auswahl:** Logos zum Filtern nach einem Dienst, dazu „Kostenlos" und
  „Läuft bei uns". Die gewählte Ansicht wird gemerkt.
- **Filmabend-Kiste statt Glücksrad**, wie das Öffnen einer Kiste in Counter-Strike 2: Ein Band aus
  Postern rast unter der Markierung durch, bremst lange ab und enthüllt den Film des Abends. Die
  **Seltenheitsfarben** (Standard, Limitiert, Geheim, Verdeckt, ★ Legendär) zeigen die echten
  Chancen, der Kisteninhalt listet sie in Prozent. Mit Klick-Geräuschen und Fanfare (abschaltbar),
  Beinahe-Treffern, „Überspringen" (auch Escape) und kurzer Animation bei „weniger Bewegung".
- **„Wem gefällt's?"** in jeder Filmansicht: geschätzte Sterne pro Person aus ihren eigenen
  Bewertungen, mit Begründung („wie Freitag der 13., ★ 5"). Ab 8 Bewertungen, bis 25 als „erste
  Tendenz". Im Rückblick-Test bis zu 20 % genauer als der Durchschnitt der Person. Was die
  Prognose kann und was nicht, steht in `docs/PROGNOSE.md`.
- **Termin und Einladung:** Datum und Ort für den nächsten Abend. „Einladen" erzeugt eine Karte
  als Bild (Termin, Poster der Vorschläge ohne Veto, wer dabei ist) und einen Text mit Link. Auf
  dem Handy geht beides direkt ins Teilen-Menü, sonst Bild speichern und Text kopieren.
- **„Heute vor einem Jahr":** Auf dem Filmabend erscheint, was ihr um dieses Datum in früheren
  Jahren geschaut habt, mit euren Sternen und dem beliebtesten Kommentar.

### Betrieb
- Erste echte Migration (`0002`): Tabelle `abend` und Spalte `movie.keywords`. Fehlende Stichworte
  älterer Filme holt die Prognose nach und nach aus TMDB (höchstens 30 pro Anfrage).
- `scripts/prognose-backtest.py` misst die Prognose an echten TMDB-Filmen.

### Tests
- 110 Backend-Tests, 34 Browser-Tests (auch gegen den Docker-Stack und in UTC). Neue Prüfungen
  jeweils mit absichtlich eingebauten Fehlern gegengecheckt; Regale und Prognose zusätzlich mit
  echten TMDB-Daten, die Migration an einer Kopie einer echten Datenbank.

## 0.4.0 – 2026-10-03

Der **Filmabend wird persönlicher**: Wo läuft der Film, wer hat welches Abo, wie fand ihn wer –
und wer ihn auf keinen Fall sehen will. Dazu eine Datenbank, die künftige Updates ohne
Datenverlust mitmacht.

### Neu
- **Seitenleiste einklappbar**: nur Icons (mit Tooltips, Kurzlogo „sm“, Live-Zähler am Kino-Icon),
  pro Gerät gemerkt. Auf dem Handy unverändert.
- **Bewerten und Kommentieren direkt in der Detailansicht** jedes gesehenen Films – nicht mehr
  nur unter Unsere Filme → Gesehen. Dazu der Gruppen-Schnitt „Ihr: ★ 4,7“ neben der TMDB-Wertung.
- **„Wo läuft's?“** in jeder Filmansicht: Abo, kostenlos, leihen, kaufen in Deutschland (Daten:
  JustWatch über TMDB). Abos, die jemand aus der Gruppe hat, stehen vorn – mit Namen.
- **Meine Abos** in den Einstellungen (nur echte Abo-Dienste, keine Leih-Shops) und der Filter
  **„Läuft bei uns“** in Finden. „Prime Video mit Werbung“ zählt als Prime Video.
- **Trailer** in der Detailansicht, deutsch bevorzugt; YouTube (nocookie) lädt erst beim Klick.
- **Veto**: Jede Person kann einen vorgeschlagenen Film ablehnen; das Glücksrad lässt ihn aus.
  Vetos verfallen, wenn der Film geschaut oder die Vorschläge geleert werden.

### Betrieb
- **Datenbank-Migrationen mit Alembic.** Die App bringt die Datenbank beim Start selbst auf den
  neuesten Stand. Datenbanken aus 0.2/0.3 werden ohne Datenverlust übernommen (fehlende Tabellen
  werden ergänzt). Künftige Schema-Änderungen: `make migration name="…"`. Ein Test schlägt fehl,
  wenn ein Modell geändert, aber keine Migration geschrieben wurde. Migrationen laufen mit
  ausgeschalteten Fremdschlüsseln, damit ein Tabellen-Umbau unter SQLite keine Kaskaden auslöst.

### Behoben
- Bewertungen und Kommentare aus einer Ansicht erschienen in anderen offenen Ansichten erst nach
  dem Neuladen.
- Escape schloss ein Fenster nicht mehr, wenn nach einer Aktion der Fokus aus dem Fenster fiel.
- Bewertungen überall mit deutschem Komma (4,7 statt 4.7).

### Tests
- 92 Backend-Tests, 28 Browser-Tests (auch gegen den kompletten Docker-Stack). Anbieter und
  Trailer zusätzlich mit echten TMDB-Daten, die Migration an einer Kopie einer echten Datenbank
  geprüft.

## 0.3.0 – 2026-10-03

Das **Kino**: gemeinsam live schauen, auch wenn alle an verschiedenen Orten sitzen.

### Neu
- **Kino** als eigener Bereich: Der Host teilt einen Browser-Tab (oder sendet per WHIP aus
  OBS), alle sehen live dasselbe Bild über WebRTC. Medienserver MediaMTX verteilt; screenmates
  prüft Rechte und leitet nur die Verbindungsaushandlung weiter.
- Menüpunkt „Kino“ mit Live-Anzeige und Zahl der Zuschauenden, Banner „Jetzt im Kino“ auf dem
  Filmabend, Film nach der Vorstellung mit allen Zuschauenden als gesehen eintragen.
- Sende-Pult mit **Qualität** (Hoch 1080p / Mittel 720p / Sparsam 480p) und **Inhalt**
  (Film / Spiel bis 60 fps) sowie Live-Anzeige der tatsächlichen Sendewerte.
- **Navigation in drei Bereiche** statt zehn Punkte: Filmabend · Finden · Unsere Filme
  (plus Kino). Ein Suchfeld für Entdecken, Titel, Personen und KI. Alte Links werden umgeleitet.
- Schrift Inter, mit dem eigenen Build ausgeliefert.

### Verbessert (alles gemessen, Details in `docs/KINO-QUALITAET.md`)
- **Bild:** 1080p ab der ersten Sekunde statt 480×270 in den ersten ~15 s – Auflösung halten,
  Startbitrate, H.264 statt VP8.
- **Ton:** Stereo mit bis zu 192 kbit/s statt Mono mit ~32 kbit/s (Sender *und* Zuschauer
  fordern Stereo an, sonst mischt Chrome herunter).
- **Gleichmäßigkeit:** 300 ms Wiedergabepuffer beim Zuschauer – größte Abweichung vom
  Aufnahmetakt 65 → 24 ms.
- Personensuche: Leute mit Horror-Bezug zuerst; Filmografien ohne Doku-Auftritte, bekannteste
  Filme zuerst, Rollen auf Deutsch.
- Entdecken und TMDB-Abgleich: nur Spielfilme ab 60 min, „Beste Bewertung“ erst ab 200 Stimmen.

### Behoben
- Sender wie OBS/FFmpeg brachen zufällig ab, wenn MediaMTX einen ICE-TCP-Kandidaten zuerst
  nannte – sie bekommen jetzt nur UDP-Kandidaten.
- Glücksrad-Beschriftungen standen teils auf dem Kopf.

### Betrieb & Tests
- `make kino-install`, MediaMTX in `compose.yaml`; neue Tabelle, bestehende Datenbanken bleiben gültig.
- CI-Job, der den kompletten `docker compose`-Stack startet und alle E2E-Tests dagegen fährt.
- 69 Backend-Tests, 23 Browser-Tests – darunter Kino mit echtem Medienserver, OBS-Ersatz per
  FFmpeg, TCP-Ausweichweg bei gesperrtem UDP und Stereo per Frequenzanalyse.

### Noch nicht im echten Einsatz geprüft
- Zuschauen über das Internet (Checkliste: `docs/KINO-CHECK.md`).
- Echtes OBS als Sender.

## 0.2.0 – 2026-10-03

Senior-Review des ersten Stands; Befunde und Behebungen in `docs/REVIEW.md`.

- Rechte-Modell (Name zum Schreiben, Host zum Verwalten), Schutz- und Host-Film werden nie
  ausgeliefert, Drosselung beim Raten.
- Schema mit Kaskaden und Unique-Constraints, Schema-Version, Validierung überall.
- TMDB-Ergebnisse mit Postern, robuster Client; KI-Suche über die Anthropic API.
- Neues Frontend mit allen Bereichen, Fehlermeldungen, Tastaturbedienung, mobile Ansicht.
- Tests, Lint, CI, Docker.

## 0.1.0 – 2026-10-03

Erster lauffähiger Nachbau (MVP): Katalog, Suche, Merkliste, Gesehen, Wünsche, Info, Namenswahl.
