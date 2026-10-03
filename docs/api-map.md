# API-Karte (reverse-engineered)

Die Original-App (`horror.marha.de`, FastAPI) stellt 51 Endpunkte bereit.
Diese Liste dokumentiert die Zielschnittstelle; der ✓-Status zeigt, was in
screenmates bereits implementiert ist.

| Status | Methode | Pfad | Zweck |
|:-:|---|---|---|
| ✓ | GET | /api/health | Healthcheck |
| ✓ | GET | /api/status | Katalog-/Sync-Status |
| ✓ | GET | /api/movies | Katalogliste |
| ✓ | GET | /api/movies/{id} | Filmdetails |
| ✓ | GET | /api/movies/{id}/credits | Besetzung/Crew |
| ✓ | GET | /api/movies/{id}/aehnliche | Ähnliche Filme |
| ✓ | GET | /api/search | Suche |
| ✓ | GET | /api/search/{id} | Detail über Suche |
| ✓ | GET | /api/discover | Entdecken mit Filtern |
| ✓ | GET | /api/personen | Personensuche |
| ✓ | GET | /api/personen/{id}/filme | Filmografie |
| ✓ | GET/POST | /api/users (+ /waehlen, /{id}, /{id}/schutz) | Nutzer & Film-als-PIN |
| ✓ | GET/POST/PATCH/DELETE | /api/watched (+ rating, notes, hearts, dabei) | Watched-Log |
| ✓ | GET/POST/DELETE | /api/wishlist | Merkliste |
| ✓ | GET/POST/DELETE | /api/suggestions (+ /alle) | Vorschläge |
| ✓ | GET/POST/PATCH/DELETE | /api/features (+ vote, notes, done) | Wünsche |
| ✓ | GET/PUT | /api/info | Info-Panel (Markdown) |
| ✓ | GET/POST | /api/host (+ /film) | Host-Modus & Passwort-Film |
| ✓ | GET/POST | /api/spin | Glücksrad |
| ✓ | POST | /api/dabei | Teilnahme |
| ✓ | GET | /api/events | Aktivitäts-Feed |
| ✓ | POST | /api/ki-suche | KI-Suche (Fallback ohne Key) |
| ✓ | POST | /api/sync | TMDB-Sync |
| ☐ | POST/GET/PATCH/DELETE | /api/clips (+ /{id}/video, /vorschau, /schneiden, /aufnahme) | Video-Clips |
| ☐ | GET/PUT/DELETE | /api/aufnahmen (+ /film) | Aufnahmen |
| ☐ | GET | /stream/{pfad} | Medien-Stream |
