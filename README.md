# screenmates

Ein eigenständiger Nachbau der Filmabend-App (Reverse Engineering von
`horror.marha.de`): ein Organizer für den gemeinsamen Horror-Filmabend.
Katalog aus [TMDB](https://www.themoviedb.org/), dazu die soziale Schicht
drumherum — Watched-Log, Merkliste, Vorschläge, Feature-Wünsche, Nutzer mit
„Film-als-PIN"-Schutz und Host-Modus.

> Dies ist ein unabhängiger Klon zu Lern-/Hobbyzwecken. Es werden **keine**
> Daten der Originalseite übernommen — der Katalog wird frisch aus TMDB
> befüllt, bzw. läuft ohne Key auf mitgelieferten Seed-Daten.

## Stack

| Teil      | Technik |
|-----------|---------|
| Backend   | FastAPI + SQLModel (SQLite), Session-Cookie, httpx-TMDB-Client |
| Frontend  | Vue 3 + Vite + Pinia, eigenes CSS (dunkles Theme, Akzent `#e50914`) |
| Medien    | ffmpeg (für die geplante Clip-Funktion) |

## Schnellstart

### Backend
```bash
cd backend
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env        # optional: TMDB_API_KEY / LLM_API_KEY eintragen
uvicorn app.main:app --reload --port 8000
```
Ohne TMDB-Key startet die App mit einer kleinen Auswahl bekannter Horrorfilme
als Seed-Daten. Mit Key liefert `POST /api/sync` echte Katalogdaten.

### Frontend (Entwicklung)
```bash
cd frontend
npm install
npm run dev        # http://localhost:5173 , API wird zu :8000 geproxied
```

### Produktion (ein Origin)
```bash
cd frontend && npm run build      # erzeugt frontend/dist
# Das Backend liefert dist/ automatisch unter / aus:
cd ../backend && uvicorn app.main:app --port 8000
```

## Konfiguration

Alle Keys sind optional (`.env`, Vorlage in `backend/.env.example`):

- `TMDB_API_KEY` — echter Filmkatalog (v3-Key oder v4-Bearer-Token).
- `LLM_API_KEY` — aktiviert die „KI-Suche"; ohne Key fällt sie auf normale
  Discover-Ergebnisse zurück.

## Stand / Roadmap

**Fertig (MVP):** Katalog, Suche, Entdecken, Merkliste, Gesehen (mit Wertungen
& Gästebuch), Wünsche (Votes/Notes), Info, Nutzer & Film-als-PIN, Host-Modus,
Glücksrad-Pool, Status.

**Noch offen:** Video-Clips (Aufnahme/Schneiden via ffmpeg), vollständige
KI-Suche über ein LLM, Ähnliche/Personen-Tabs im Frontend, Live-Events (SSE).

Details zur reverse-engineerten API: `docs/api-map.md`.
