# Contributing to screenmates

Thanks for your interest in screenmates! Bug reports, ideas and pull requests are all welcome.
This guide gets you from a fresh clone to a green pull request.

## Ways to help

- **Report a bug** – use the [bug report form](https://github.com/marcmeier/screenmates/issues/new?template=bug_report.yml).
  Screenshots and the version from the about page help a lot.
- **Suggest a feature** – use the [feature request form](https://github.com/marcmeier/screenmates/issues/new?template=feature_request.yml).
  If you run screenmates, your group can also vote on ideas in the app under *Wishes & ideas*.
- **Translate** – the UI speaks German and English (`frontend/src/i18n/`, server texts in
  `backend/app/texte_en.py`). Fixes to wording are very welcome.
- **Security issues** – please don't open a public issue; see [SECURITY.md](SECURITY.md).

## Development setup

Requirements: Python ≥ 3.12, Node ≥ 20 (CI uses Python 3.13 and Node 24).

```bash
git clone https://github.com/marcmeier/screenmates.git
cd screenmates
make install        # backend venv + npm ci
make dev            # backend :8000 + Vite :5173 → http://localhost:5173
```

Without any configuration screenmates runs on a small built-in demo catalog. For the real catalog,
copy `backend/.env.example` to `backend/.env` and add a free
[TMDB API key](https://www.themoviedb.org/settings/api).

For the cinema, run `make kino-install` once – `make dev` then starts MediaMTX alongside.
`make help` lists every task.

## Before you open a pull request

```bash
make lint           # ruff (check + format) and eslint
make format         # auto-fix formatting
make test           # pytest + Playwright E2E against the real backend
```

For the browser tests, install Chromium once: `cd frontend && npx playwright install chromium`.
The cinema E2E steps run when MediaMTX and FFmpeg are available (`./scripts/mediamtx.sh` and
`./scripts/ffmpeg-whip.sh`).

CI runs lint, unit tests, E2E tests and the full `docker compose` stack on every pull request – all
jobs need to be green before merging.

### Database changes

The schema is managed with Alembic. After changing a model in `backend/app/models.py`:

```bash
make migration name="short description"
```

Review the generated file in `backend/migrations/versions/` (add a `server_default` for new
`NOT NULL` columns on existing tables). A test fails if a model change has no migration.

### Texts and translations

User-facing strings live in `frontend/src/i18n/de.js` and `en.js` (same keys in both). Server-side
texts stay German in the code and are looked up in `backend/app/texte_en.py` via `tr()`. When you add
a string, add both languages.

## Conventions

- **Code style:** enforced by ruff and eslint – `make format` fixes most things.
- **Naming:** much of the domain vocabulary in the code is German (`abend` = evening, `kiste` = case,
  `gastgeber` = host, `kino` = cinema, `erfolge` = awards). Please stay consistent with the
  surrounding code rather than mixing in English synonyms.
- **Commits & PRs:** keep pull requests focused on one change and describe *what* and *why*. Add
  screenshots for UI changes (desktop and phone if layout is affected).
- **Changelog:** add a line to the top section of [CHANGELOG.md](CHANGELOG.md) for user-visible changes.

## Project layout

```
backend/app/          FastAPI app – routers/ by area, models.py, session.py (auth), tmdb.py, ki.py (AI)
backend/migrations/   Alembic migrations (applied automatically at startup)
backend/tests/        pytest
frontend/src/         Vue 3 SPA – components/, stores/ (Pinia), i18n/
frontend/e2e/         Playwright tests
deploy/mediamtx.yml   media server config for the cinema
docs/                 deeper documentation
```

## License

By contributing you agree that your contributions are licensed under the
[GNU Affero General Public License v3.0](LICENSE).
