# Contributing

Bug reports, ideas and pull requests are welcome. For bugs and feature requests, use the
[issue forms](https://github.com/marcmeier/screenmates/issues/new/choose). Security issues go through
[SECURITY.md](SECURITY.md) instead.

## Setup

Python 3.12+ and Node 20+ (CI uses 3.13 and 24).

```bash
git clone https://github.com/marcmeier/screenmates.git
cd screenmates
make install
make dev            # backend on :8000, Vite on :5173
```

Without configuration the app uses a small demo catalog. For real data, copy `backend/.env.example` to
`backend/.env` and add a [TMDB API key](https://www.themoviedb.org/settings/api). `make kino-install`
downloads MediaMTX for the cinema; `make dev` starts it automatically afterwards.

## Tests and linting

```bash
make lint           # ruff + eslint
make format         # fix formatting
make test           # pytest + Playwright E2E
```

The E2E tests need Chromium once: `cd frontend && npx playwright install chromium`. The cinema tests
run when MediaMTX and FFmpeg are present (`./scripts/mediamtx.sh`, `./scripts/ffmpeg-whip.sh`).

CI runs lint, unit tests, E2E tests and the Docker Compose setup on every pull request.

## Database changes

After changing `backend/app/models.py`, generate a migration:

```bash
make migration name="short description"
```

Check the generated file in `backend/migrations/versions/`; new `NOT NULL` columns on existing tables
need a `server_default`. There's a test that fails if a model change has no migration.

## Texts

UI strings are in `frontend/src/i18n/de.js` and `en.js` with the same keys. Server-side strings are
written in German in the code and translated through `backend/app/texte_en.py`. New strings need both
languages.

## Conventions

- Formatting is handled by ruff and eslint.
- A lot of the code uses German names (`abend` = evening, `kiste` = case, `gastgeber` = host,
  `kino` = cinema, `erfolge` = awards). Stick with the names already used nearby.
- Keep pull requests focused. Include screenshots for UI changes, and a changelog entry for anything
  users will notice.

## Layout

```
backend/app/          FastAPI app: routers/, models.py, session.py (auth), tmdb.py, ki.py (AI search)
backend/migrations/   Alembic migrations, applied on startup
backend/tests/        pytest
frontend/src/         Vue app: components/, stores/, i18n/
frontend/e2e/         Playwright tests
deploy/mediamtx.yml   MediaMTX config
docs/                 longer documentation
```

Contributions are licensed under the [AGPL-3.0](LICENSE).
