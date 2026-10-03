# Changelog

## Unveröffentlicht

### Neu
- **Seitenleiste einklappbar**: nur Icons (mit Tooltips, Kurzlogo „sm“, Live-Zähler am Kino-Icon),
  pro Gerät gemerkt. Auf dem Handy unverändert.
- **Bewerten und Kommentieren direkt in der Detailansicht** jedes gesehenen Films – nicht mehr
  nur unter Unsere Filme → Gesehen. Dazu der Gruppen-Schnitt „Ihr: ★ 4,7“ neben der TMDB-Wertung.

### Behoben
- Bewertungen und Kommentare aus einer Ansicht erschienen in anderen offenen Ansichten erst nach
  dem Neuladen.
- Escape schloss ein Fenster nicht mehr, wenn nach einer Aktion der Fokus aus dem Fenster fiel.
- Bewertungen überall mit deutschem Komma (4,7 statt 4.7).

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
