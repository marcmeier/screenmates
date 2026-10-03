# Code-Review v0.1 → v0.2

Senior-Review des ersten MVP-Stands (`01abb27`). Jeder Befund ist mit seiner
Behebung und, wo möglich, dem Test aufgeführt, der eine Rückkehr verhindert.
Schweregrade: **K** kritisch · **H** hoch · **M** mittel · **N** niedrig.

## Sicherheit

| # | Befund | Behebung | Abgesichert durch |
|---|---|---|---|
| K1 | `GET /api/users/{id}/schutz` lieferte die `movie_id`, also das Passwort im Klartext. | Antwort enthält nur noch `hat_schutz`. Kein Endpunkt gibt den Schutz-Film heraus. | `test_schutz_film_is_never_revealed` |
| K2 | `GET /api/host/film` gab jedem den Host-Film (= Admin-Passwort). | Nur noch für aktive Hosts. Host-Rechte gelten pro Session und Person und verfallen beim Abmelden oder Namenswechsel. | `test_admin_requires_host`, `test_switching_name_drops_host` |
| K3 | Keine Autorisierung: Jeder konnte Nutzer löschen, fremden Schutz ändern, alle Vorschläge löschen und die Info überschreiben. | Zentrale Dependencies `require_user`, `require_host`, `require_owner_or_host`. Schreibzugriffe brauchen einen Namen, Verwaltung den Host, Eigentum gilt für Kommentare, Wünsche und Ratings. | `test_writes_require_a_name`, `test_admin_requires_host`, `test_feature_permissions`, `test_only_own_rating_can_be_deleted` |
| H1 | Film-PIN beliebig oft ratbar. | Drosselung: 8 Fehlversuche pro 10 Minuten (Nutzer bzw. Host-Session), danach HTTP 429. | `test_schutz_guessing_is_throttled` |
| H2 | Info-Panel per selbstgebautem Regex-Markdown mit `v-html`. | `marked` + `DOMPurify`. | E2E `info markdown is rendered and sanitised` (XSS-Payload) |
| M1 | Session-Cookie ohne `Secure`, Session-ID nur 24 Bytes. | `COOKIE_SECURE` konfigurierbar, 32 Byte Token. | – |

## Korrektheit

| # | Befund | Behebung | Abgesichert durch |
|---|---|---|---|
| H3 | Mit TMDB-Key fehlten in Suche, Entdecken und Ähnliche die Poster (`poster_url`), `genres` kam als JSON-String. | Ein einziger Serialisierer `movie_dict` für DB-Zeilen **und** TMDB-Treffer, Genre-IDs werden auf Namen gemappt. | `test_tmdb_results_have_posters_and_genre_lists` |
| H4 | Film- und Serien-IDs von TMDB überschneiden sich. Eine Serie hätte einen Film im Katalog überschrieben. | Katalog führt nur noch Filme (`/search/movie`), Serien stehen auf der Roadmap. | – |
| H5 | Löschen hinterließ verwaiste Ratings, Notizen, Herzen und Votes (kein CASCADE, `PRAGMA foreign_keys` aus). | `ON DELETE CASCADE` bzw. `SET NULL` im Schema, Foreign Keys aktiviert. | `test_deleting_watched_cascades`, `test_deleting_user_keeps_their_notes_but_drops_ratings` |
| H6 | Sternebewertung gespiegelt: Durch `row-reverse` vergab der erste Stern 5 Punkte. | Neue `StarRating`-Komponente in natürlicher Reihenfolge, als Radiogroup. | E2E `the n-th star gives n stars` |
| M2 | Lokale Suche betrachtete nur die ersten `limit` Zeilen der DB. | Filtert per SQL-`ILIKE` über den ganzen Katalog. | `test_local_search_scans_whole_catalogue` |
| M3 | Discover-Fallback ignorierte Sortierung, Genres, Laufzeit, `note_max` und `stimmen_max`. | Alle Filter umgesetzt, Sortierung über eine Whitelist. | `test_discover_filters_and_sort`, `test_discover_genre_include_exclude`, `test_discover_rejects_unknown_sort` |
| M4 | TMDB-Fehler (Timeout, 5xx) wurden zu HTTP 500. 404 ebenso. | `TMDBError` → 502 mit Klartext, 404 → `None`. Ein gemeinsamer `AsyncClient` statt einer neuen Verbindung pro Request. | `test_tmdb_failures_become_502` |
| M5 | `DELETE /api/watched/rating/{id}` war unbenutzbar, weil Ratings ohne ID ausgeliefert wurden. | Ratings enthalten `id`. | `test_rating_validation_and_upsert` |
| M6 | Keine Eingabevalidierung (Sterne 0–∞, unbegrenzte Texte, Limits). | Pydantic-Constraints überall (Sterne 1–5, Textlängen, `limit ≤ 100`, Jahres- und Notenbereiche). | `test_rating_validation_and_upsert`, `test_duplicate_names_are_rejected` |
| M7 | Duplikate möglich (Vorschläge, Votes, Herzen, Namen). | Unique-Constraints in der DB, Endpunkte idempotent. | `test_suggestions_grouped_and_ranked` |
| M8 | Antworten im Gästebuch konnten auf Notizen eines **anderen** Eintrags zeigen. | `parent_id` muss zum selben Eintrag gehören. | `test_notes_are_threaded_and_validated` |
| M9 | Zeitstempel ohne Zeitzone (SQLite verliert `tzinfo`). | `iso()` liefert immer UTC mit `Z`. | – |
| M10 | Schemaänderungen hätten bestehende DB-Dateien still beschädigt. | `PRAGMA user_version`-Prüfung mit klarer Fehlermeldung beim Start. | `test_outdated_database_is_refused` |
| N1 | `POST /api/dabei` war ein No-op. | Echte Teilnahme pro Nutzer, Host kann zurücksetzen. | `test_dabei_toggle_and_reset` |
| N2 | KI-Suche ignorierte die Beschreibung komplett. | Anthropic Messages API. Vorschläge werden gegen TMDB bzw. Katalog aufgelöst, erfundene Filme fallen raus. | `test_ki_resolves_titles_against_catalogue` |

## Performance & Betrieb

| # | Befund | Behebung |
|---|---|---|
| M11 | N+1-Abfragen in Watched- und Wunsch-Listen (pro Eintrag 3–4 Queries, rekursiv für Antworten). | Batch-Loading: konstante Anzahl Queries pro Liste, Kommentarbäume im Speicher. |
| M12 | Jeder anonyme GET legte eine Session-Zeile an (Bots füllen die DB). | Sessions entstehen erst beim Anmelden. Test: `test_reads_do_not_create_sessions`. |
| N3 | SPA-Fallback fehlte, `/irgendwas` lieferte 404 statt `index.html`. | Catch-all-Route, die `/api/*` ausspart. |
| N4 | Kein Deployment-Weg. | Multi-Stage-`Dockerfile` + `compose.yaml` (Non-Root, Healthcheck, Volume). |

## Frontend

| # | Befund | Behebung |
|---|---|---|
| H7 | Kein Fehler-Feedback: Fehlgeschlagene Aktionen verpufften still als unhandled rejections. | Zentrale Fehlerbehandlung in `api.js` mit Toasts. 401 öffnet automatisch die Namenswahl. |
| M13 | Race-Condition: Langsame Suchantworten überschrieben neuere. | `useMovieList` bricht laufende Requests per `AbortController` ab. |
| M14 | Nicht per Tastatur bedienbar (klickbare `div`s), Modals ohne Escape und Fokus-Management. | Echte Buttons und Links, `Modal` mit Fokusfalle, Escape, Scroll-Lock, ARIA. `prefers-reduced-motion` wird respektiert. |
| M15 | Die Hälfte des Backends hatte kein UI (Vorschläge, Glücksrad, Host, Personen, KI, Teilnahme). | Neue Tabs Filmabend, Personen, KI-Suche, Verwaltung, dazu Ähnliche und Besetzung im Detail-Sheet. |
| N5 | Tab-Zustand ging beim Neuladen verloren. | Hash-Routing (`#/gesehen`, `#/personen/42`), Entdecken-Filter in `localStorage`. |
| N6 | Ohne Poster wirkten Listen kaputt. | `Poster`-Komponente mit gestaltetem Platzhalter (Farbe je Film). |
| N7 | Vite-Boilerplate (`HelloWorld`, `hero.png`, Template-README) im Repo. | Entfernt. |

## Qualitätssicherung (neu)

- **Backend:** 51 pytest-Tests (Rechte, Kaskaden, Validierung, TMDB- und LLM-Mocks per `respx`), `ruff`-Lint und -Format.
  Gegenprobe: Die alten Bugs (Schutz-Leak, Foreign Keys aus) wieder eingebaut → die Tests werden rot.
- **Frontend:** ESLint (`eslint-plugin-vue`), Playwright-E2E mit 14 Schritten gegen das echte Backend.
  Die Suite schlägt auch bei Konsolenfehlern fehl.
- **CI:** GitHub Actions mit Backend-, Frontend- und E2E-Job.

## Bewusst offen

- **Migrationen:** Noch kein Alembic. Die Schema-Version schützt vor stillem Datenmüll, migriert aber nicht.
- **Rate-Limits im Speicher:** Reichen für einen Prozess. Bei mehreren Workern gehört das in die DB oder nach Redis.
- **Video-Clips** (`/api/clips`, `/api/aufnahmen`, `/stream`) aus dem Original sind weiterhin nicht umgesetzt.
- **Serien** brauchen einen zusammengesetzten Schlüssel `(media_type, id)`.
