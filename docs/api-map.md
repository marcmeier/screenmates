# API-Karte

Alle Endpunkte liegen unter `/api`. Die interaktive Doku gibt es unter `/docs`, wenn das Backend läuft.

**Recht:** – jeder · **N** gewählter Name · **E** Ersteller oder Admin · **A** Admin

**Zugangsfrage:** Ist eine gesetzt, antwortet die ganze API Browsern ohne Zugang mit `423` – außer `/health`, `/zugang…`, `/kino/mtx-auth` und dem Senden per OBS-Key (`/kino/whip`, `/kino/sitzung/whip/…`). „jeder“ heißt dann: jeder mit Zugang.

## Katalog

| Methode | Pfad | Recht | Zweck |
|---|---|:-:|---|
| GET | `/health`, `/status` | – | Healthcheck. Katalog-, Sync- und Feature-Status, Anzahl Merkliste und Gesehen |
| GET | `/movies` | – | Katalog, nach Beliebtheit (`limit`, `offset`) |
| GET | `/movies/{id}` · `/search/{id}` | – | Details (ergänzt fehlende Daten aus TMDB) |
| GET | `/movies/{id}/credits` | – | Besetzung und Schlüssel-Crew |
| GET | `/movies/{id}/aehnliche` | – | Empfehlungen (Fallback: gemeinsame Genres) |
| GET | `/search?q=` | – | Filmsuche (`limit`, `seite`) |
| GET | `/discover` | – | Filme mit Filtern (nur bereits erschienene): `sort`, `include` (alle diese Genres)/`exclude` (Genre-IDs), `sprachen`, `jahr_*`, `note_*`, `dauer_*`, `stimmen_*`, `seite` |
| GET | `/genres` | – | Genre-IDs und Namen |
| GET | `/personen?q=` | – | Personensuche (TMDB), nach Bekanntheit |
| GET | `/personen/{id}/filme` | – | Filmografie (optional `genre`), bekannteste zuerst, ohne reine Auftritte |
| POST | `/sync` | A | Beliebteste und bestbewertete Filme aus TMDB übernehmen |
| POST | `/ki-suche` | – | Freitext → Filmvorschläge (braucht `LLM_API_KEY`) |
| GET | `/movies/{id}/anbieter` | – | „Wo läuft's?": Abo/kostenlos/leihen/kaufen in DE (JustWatch über TMDB), Abos der Gruppe zuerst mit `bei` |
| GET | `/movies/{id}/trailer` | – | Bester YouTube-Trailer (deutsch vor englisch) oder `null` |
| GET | `/movies/{id}/prognose` | – | „Wem gefällt's?": geschätzte Sterne pro Person mit Begründung, ab 8 Bewertungen (`docs/PROGNOSE.md`) |
| GET | `/anbieter` | – | Abo-Dienste für die Auswahl (ohne Leih-Shops) |

| GET | `/stoebern` | – | Regale zum Stöbern: „Läuft bei uns", je Dienst (eigene Abos zuerst), Kostenlos, Neu, Genres, Geheimtipps, Klassiker; jedes mit seinem Raster-`filter` |

`/discover` filtert auch nach Streaming: `abos=true` (Abos der Gruppe), `anbieter=8,9` (diese Dienste im Abo),
`kostenlos=true` (kostenlos, auch mit Werbung). `/anbieter?zum_stoebern=true` liefert nur Dienste, die als
Regal taugen (ohne Leih-Shops, Channels, Werbe-Varianten), eigene Abos zuerst.

Jeder Film trägt die Gruppen-Flags `gesehen`, `gemerkt` und `vorgeschlagen_von`.

## Nutzer & Rechte

| Methode | Pfad | Recht | Zweck |
|---|---|:-:|---|
| GET | `/users` | – | Freigegebene Namen, `ich`, `admin`, `antraege` (offene Anträge, nur für Admins) |
| POST | `/users` | – | Namen beantragen (`freigegeben: false`). Der erste Name einer leeren Datenbank wird Admin, Admins legen direkt freigegebene Namen an. Höchstens 20 offene Anträge |
| POST | `/users/waehlen` | – | Anmelden (`user_id`, ggf. `movie_id` als Film-PIN) bzw. Abmelden (`user_id: null`). Gedrosselt |
| DELETE | `/users/{id}` | A | Nutzer löschen bzw. Antrag ablehnen (Ratings und Votes weg, Kommentare anonym). Nicht den letzten Admin |
| PUT/DELETE | `/users/{id}/bild` | E | Profilbild hochladen (Bild als Request-Body, max. 5 MB; JPG/PNG/WebP/GIF, wird zu 256×256 WebP ohne Metadaten) bzw. entfernen. E = die Person selbst oder ein Admin |
| GET | `/users/{id}/bild` | – | Profilbild (URL mit `?v=…` aus `users[].bild`, lange gecacht) |
| GET/POST | `/users/{id}/schutz` | –/E | Schutz abfragen (nur `hat_schutz`) bzw. setzen oder entfernen |
| POST | `/abos` | N | Eigene Streaming-Abos setzen (Provider-IDs) |
| POST | `/dabei` | N | Eigene Teilnahme am nächsten Abend umschalten |
| DELETE | `/dabei` | A | Teilnahme aller zurücksetzen |

## Zugang & Verwaltung

| Methode | Pfad | Recht | Zweck |
|---|---|:-:|---|
| GET | `/zugang` | – | `gesperrt` (Frage gesetzt), `offen` (dieser Browser hat Zugang), `frage` |
| POST | `/zugang` | – | Zugangsfrage beantworten (`movie_id`). Gedrosselt: 5 Fehlversuche pro IP, 60 insgesamt je 15 min |
| GET | `/zugang/suche` | – | Filmsuche für die Zugangsfrage – ohne Gruppen-Markierungen (gesehen, gemerkt …) |
| GET/PUT | `/admin/zugang` | A | Frage und Antwort-Film anzeigen bzw. setzen; `movie_id: null` hebt die Frage auf |
| GET/POST | `/admin/users` | A | Alle Namen inkl. Anträge und Anzahl angemeldeter Geräte bzw. direkt einen freigegebenen Namen anlegen |
| PATCH | `/admin/users/{id}` | A | `name`, `color` (`#rrggbb`), `admin`, `freigegeben` (Antrag freigeben). Es bleibt immer ein Admin |
| POST | `/admin/users/{id}/abmelden` | A | Alle Sitzungen der Person beenden; diese Browser verlieren auch den Zugang |

## Filmabend

| Methode | Pfad | Recht | Zweck |
|---|---|:-:|---|
| GET | `/suggestions` | – | Vorschläge pro Film mit `von`, nach Stimmen sortiert |
| POST | `/suggestions` | N | Film vorschlagen (idempotent) |
| DELETE | `/suggestions/{movie_id}` | N | Eigenen Vorschlag zurückziehen |
| DELETE | `/suggestions` | N | Alle eigenen Vorschläge zurückziehen |
| DELETE | `/suggestions/alle` | A | Alle Vorschläge löschen |
| POST/DELETE | `/veto` | N | Eigenes Veto gegen einen Vorschlag setzen bzw. zurücknehmen (eins pro Person) |
| GET/POST | `/spin` | – | Pool mit `gewicht` (ohne Filme mit Veto), bzw. gewichtete Ziehung |
| GET | `/termin` | – | Nächster Termin mit `notiz` (vergangene Termine: `null`) |
| PUT/DELETE | `/termin` | N | Termin setzen (ohne Zeitzone = deutsche Zeit) bzw. entfernen |
| GET | `/erinnerungen` | – | „Heute vor einem Jahr": Gesehenes aus früheren Jahren, ±3 Tage (`heute=` zum Testen) |
| GET | `/events` | – | Aktivitäts-Feed |
| GET/POST/DELETE | `/wishlist[/{movie_id}]` | –/N/N | Merkliste |

## Gesehen

| Methode | Pfad | Recht | Zweck |
|---|---|:-:|---|
| GET | `/watched` | – | Chronik (`alle=true` inklusive ausgeblendeter) |
| POST | `/watched` | N | Als gesehen eintragen. Entfernt den Film aus Merkliste und Vorschlägen |
| PATCH | `/watched/{id}` | N | Datum ändern, ausblenden |
| DELETE | `/watched/{id}` | A | Eintrag samt Ratings und Kommentaren löschen |
| POST | `/watched/{id}/rating` | N | 1–5 Sterne (überschreibt die eigene Wertung) |
| DELETE | `/watched/rating/{id}` | E | Wertung löschen |
| POST | `/watched/{id}/notes` | N | Gästebuch, mit `parent_id` als Antwort |
| DELETE | `/watched-notes/{id}` | E | Kommentar löschen (Antworten mit) |
| POST | `/watched/hearts` | N | Herz für einen Kommentar umschalten |
| POST | `/watched/{id}/dabei` | N | Teilnehmende setzen |

## Wünsche & Info

| Methode | Pfad | Recht | Zweck |
|---|---|:-:|---|
| GET/POST | `/features` | –/N | Wünsche (offen nach Stimmen, dann erledigt) |
| PATCH/DELETE | `/features/{id}` | E | Text ändern bzw. löschen |
| PATCH | `/features/{id}/done` | A | Erledigt markieren |
| POST | `/features/{id}/vote` | N | Stimme umschalten |
| POST | `/features/{id}/notes` | N | Anmerkung |
| DELETE | `/feature-notes/{id}` | E | Anmerkung löschen |
| GET/PUT | `/info` | –/H | Markdown-Infotext |

## Kino

| Methode | Pfad | Recht | Zweck |
|---|---|:-:|---|
| GET | `/kino` | – | Live-Status, Titel, verknüpfter Film, Zuschauende, Publikum der Vorstellung |
| POST | `/kino/programm` | A | Titel setzen, Film verknüpfen |
| POST/DELETE | `/kino/da` | N | Herzschlag beim Zuschauen bzw. Abmelden |
| POST | `/kino/whip` | A oder OBS-Key | Senden (WHIP-Proxy zu MediaMTX) |
| POST | `/kino/whep` | N | Zuschauen (WHEP-Proxy) |
| PATCH/DELETE | `/kino/sitzung/{whip,whep}/{id}` | wie oben | WebRTC-Sitzung nachverhandeln bzw. beenden |
| GET | `/kino/obs` · POST `/kino/obs/neu` | A | Server-URL und Stream-Key für OBS, Key erneuern |
| DELETE | `/kino` | A | Übertragung für alle beenden (auch OBS) |
| POST | `/kino/mtx-auth` | intern | Rechteprüfung, die MediaMTX bei jeder Aktion aufruft |

## Noch nicht umgesetzt (aus dem Original)

`/clips/*`, `/aufnahmen/*`, `/stream/{pfad}`: Video-Clips aus Filmen schneiden und abspielen.
