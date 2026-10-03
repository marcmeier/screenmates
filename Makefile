# screenmates — common tasks. `make help` lists them.
SHELL := /bin/bash
VENV  := backend/.venv
PY    := $(VENV)/bin/python

.PHONY: help install kino-install dev backend frontend kino-server test test-backend test-e2e migration lint format build run
MTX   := .tools/mediamtx
# With MediaMTX installed, `make dev`/`make run` switch the Kino on automatically.
KINO  := $(if $(wildcard $(MTX)),MEDIAMTX_WEBRTC_URL=http://127.0.0.1:8889,)

help:
	@grep -E '^[a-z0-9-]+:.*## ' $(MAKEFILE_LIST) | awk -F':.*## ' '{printf "  \033[1m%-13s\033[0m %s\n", $$1, $$2}'

install: ## Backend-venv und Frontend-Abhängigkeiten installieren
	test -d $(VENV) || python3 -m venv $(VENV)
	$(PY) -m pip install -q -r backend/requirements-dev.txt
	cd frontend && npm ci

kino-install: ## MediaMTX für das Kino herunterladen (.tools/mediamtx)
	./scripts/mediamtx.sh

dev: ## Backend (:8000), Vite (:5173) und – falls installiert – den Kino-Server starten
	@trap 'kill 0' EXIT; \
	if [ -x $(MTX) ]; then $(MAKE) -s kino-server & fi; \
	$(MAKE) -s backend & $(MAKE) -s frontend & wait

backend: ## Nur das Backend mit Auto-Reload
	cd backend && $(KINO) .venv/bin/uvicorn app.main:app --reload --port 8000

kino-server: ## Nur MediaMTX (Kino) mit deploy/mediamtx.yml
	$(MTX) deploy/mediamtx.yml

frontend: ## Nur den Vite-Dev-Server
	cd frontend && npm run dev

test: test-backend test-e2e ## Alle Tests

test-backend: ## pytest
	cd backend && .venv/bin/pytest

test-e2e: ## Playwright gegen echtes Backend (braucht `npx playwright install chromium`)
	cd frontend && npm run test:e2e

migration: ## Neue DB-Migration aus Modelländerungen erzeugen: make migration name="spalte xy"
	@test -n "$(name)" || (echo 'Bitte mit name="…" aufrufen' && exit 1)
	cd backend && .venv/bin/alembic revision --autogenerate -m "$(name)"
	@echo "Migration prüfen (Hinweise oben in der Datei) und mit committen."

lint: ## ruff + eslint
	cd backend && .venv/bin/ruff check . && .venv/bin/ruff format --check .
	cd frontend && npm run lint

format: ## Code formatieren
	cd backend && .venv/bin/ruff format . && .venv/bin/ruff check --fix .
	cd frontend && npx eslint --fix .

build: ## Frontend für Produktion bauen
	cd frontend && npm run build

run: build ## Produktion lokal: API + SPA auf :8000 (plus Kino-Server, falls installiert)
	@trap 'kill 0' EXIT; \
	if [ -x $(MTX) ]; then $(MTX) deploy/mediamtx.yml & fi; \
	cd backend && $(KINO) .venv/bin/uvicorn app.main:app --port 8000 & wait
