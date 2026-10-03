# API-Karte

Alle Endpunkte liegen unter `/api`. Die interaktive Doku gibt es unter `/docs`, wenn das Backend läuft.

**Recht:** – jeder · **N** gewählter Name · **E** Ersteller oder Host · **H** Host

## Katalog

| Methode | Pfad | Recht | Zweck |
|---|---|:-:|---|
| GET | `/health`, `/status` | – | Healthcheck. Katalog-, Sync- und Feature-Status, Anzahl Merkliste und Gesehen |
| GET | `/movies` | – | Katalog, nach Beliebtheit (`limit`, `offset`) |
| GET | `/movies/{id}` · `/search/{id}` | – | Details (ergänzt fehlende Daten aus TMDB) |
| GET | `/movies/{id}/credits` | – | Besetzung und Schlüssel-Crew |
| GET | `/movies/{id}/aehnliche` | – | Empfehlungen (Fallback: gemeinsame Genres) |
| GET | `/search?q=` | – | Filmsuche (`limit`, `seite`) |
| GET | `/discover` | – | Horror mit Filtern: `sort`, `include`/`exclude` (Genre-IDs), `jahr_*`, `note_*`, `dauer_*`, `stimmen_*`, `seite` |
| GET | `/genres` | – | Genre-IDs und Namen |
| GET | `/personen?q=` | – | Personensuche (TMDB), Personen mit Horror-Bezug zuerst |
| GET | `/personen/{id}/filme` | – | Filmografie (`nur_horror`), bekannteste zuerst, ohne reine Auftritte |
| POST | `/sync` | H | Beliebteste und bestbewertete Horrorfilme aus TMDB übernehmen |
| POST | `/ki-suche` | – | Freitext → Filmvorschläge (braucht `LLM_API_KEY`) |
| GET | `/movies/{id}/anbieter` | – | „Wo läuft's?": Abo/kostenlos/leihen/kaufen in DE (JustWatch über TMDB), Abos der Gruppe zuerst mit `bei` |
| GET | `/movies/{id}/trailer` | – | Bester YouTube-Trailer (deutsch vor englisch) oder `null` |
| GET | `/movies/{id}/prognose` | – | „Wem gefällt's?": geschätzte Sterne pro Person mit Begründung, ab 8 Bewertungen (`docs/PROGNOSE.md`) |
| GET | `/anbieter` | – | Abo-Dienste für die Auswahl (ohne Leih-Shops) |

| GET | `/stoebern` | – | Regale zum Stöbern: „Läuft bei uns", je Dienst (eigene Abos zuerst), Kostenlos, Neu, Geheimtipps, Klassiker; jedes mit seinem Raster-`filter` |

`/discover` filtert auch nach Streaming: `abos=true` (Abos der Gruppe), `anbieter=8,9` (diese Dienste im Abo),
`kostenlos=true` (kostenlos, auch mit Werbung). `/anbieter?zum_stoebern=true` liefert nur Dienste, die als
Regal taugen (ohne Leih-Shops, Channels, Werbe-Varianten), eigene Abos zuerst.

Jeder Film trägt die Gruppen-Flags `gesehen`, `gemerkt` und `vorgeschlagen_von`.

## Nutzer & Rechte

| Methode | Pfad | Recht | Zweck |
|---|---|:-:|---|
| GET | `/users` | – | Alle Namen, `ich`, `host` |
| POST | `/users` | – | Namen anlegen |
| POST | `/users/waehlen` | – | Anmelden (`user_id`, ggf. `movie_id` als Film-PIN) bzw. Abmelden (`user_id: null`). Gedrosselt |
| DELETE | `/users/{id}` | H | Nutzer löschen (Ratings und Votes weg, Kommentare anonym) |
| GET/POST | `/users/{id}/schutz` | –/E | Schutz abfragen (nur `hat_schutz`) bzw. setzen oder entfernen |
| POST | `/abos` | N | Eigene Streaming-Abos setzen (Provider-IDs) |
| POST | `/dabei` | N | Eigene Teilnahme am nächsten Abend umschalten |
| DELETE | `/dabei` | H | Teilnahme aller zurücksetzen |
| GET | `/host` | – | `host` (diese Session) und `eingerichtet` |
| POST | `/host` | N | Host werden (`movie_id` = Host-Film, gedrosselt). Der erste legt den Film fest |
| GET/POST | `/host/film` | H | Host-Film anzeigen bzw. ändern |

## Filmabend

| Methode | Pfad | Recht | Zweck |
|---|---|:-:|---|
| GET | `/suggestions` | – | Vorschläge pro Film mit `von`, nach Stimmen sortiert |
| POST | `/suggestions` | N | Film vorschlagen (idempotent) |
| DELETE | `/suggestions/{movie_id}` | N | Eigenen Vorschlag zurückziehen |
| DELETE | `/suggestions` | N | Alle eigenen Vorschläge zurückziehen |
| DELETE | `/suggestions/alle` | H | Alle Vorschläge löschen |
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
| DELETE | `/watched/{id}` | H | Eintrag samt Ratings und Kommentaren löschen |
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
| PATCH | `/features/{id}/done` | H | Erledigt markieren |
| POST | `/features/{id}/vote` | N | Stimme umschalten |
| POST | `/features/{id}/notes` | N | Anmerkung |
| DELETE | `/feature-notes/{id}` | E | Anmerkung löschen |
| GET/PUT | `/info` | –/H | Markdown-Infotext |

## Kino

| Methode | Pfad | Recht | Zweck |
|---|---|:-:|---|
| GET | `/kino` | – | Live-Status, Titel, verknüpfter Film, Zuschauende, Publikum der Vorstellung |
| POST | `/kino/programm` | H | Titel setzen, Film verknüpfen |
| POST/DELETE | `/kino/da` | N | Herzschlag beim Zuschauen bzw. Abmelden |
| POST | `/kino/whip` | H oder OBS-Key | Senden (WHIP-Proxy zu MediaMTX) |
| POST | `/kino/whep` | N | Zuschauen (WHEP-Proxy) |
| PATCH/DELETE | `/kino/sitzung/{whip,whep}/{id}` | wie oben | WebRTC-Sitzung nachverhandeln bzw. beenden |
| GET | `/kino/obs` · POST `/kino/obs/neu` | H | Server-URL und Stream-Key für OBS, Key erneuern |
| DELETE | `/kino` | H | Übertragung für alle beenden (auch OBS) |
| POST | `/kino/mtx-auth` | intern | Rechteprüfung, die MediaMTX bei jeder Aktion aufruft |

## Noch nicht umgesetzt (aus dem Original)

`/clips/*`, `/aufnahmen/*`, `/stream/{pfad}`: Video-Clips aus Filmen schneiden und abspielen.
