# screenmates — common tasks. `make help` lists them.
SHELL := /bin/bash
VENV  := backend/.venv
PY    := $(VENV)/bin/python

.PHONY: help install dev backend frontend test test-backend test-e2e lint format build run

help:
	@grep -E '^[a-z0-9-]+:.*## ' $(MAKEFILE_LIST) | awk -F':.*## ' '{printf "  \033[1m%-13s\033[0m %s\n", $$1, $$2}'

install: ## Backend-venv und Frontend-Abhängigkeiten installieren
	test -d $(VENV) || python3 -m venv $(VENV)
	$(PY) -m pip install -q -r backend/requirements-dev.txt
	cd frontend && npm ci

dev: ## Backend (:8000) und Vite (:5173) zusammen starten
	@trap 'kill 0' EXIT; $(MAKE) -s backend & $(MAKE) -s frontend & wait

backend: ## Nur das Backend mit Auto-Reload
	cd backend && .venv/bin/uvicorn app.main:app --reload --port 8000

frontend: ## Nur den Vite-Dev-Server
	cd frontend && npm run dev

test: test-backend test-e2e ## Alle Tests

test-backend: ## pytest
	cd backend && .venv/bin/pytest

test-e2e: ## Playwright gegen echtes Backend (braucht `npx playwright install chromium`)
	cd frontend && npm run test:e2e

lint: ## ruff + eslint
	cd backend && .venv/bin/ruff check . && .venv/bin/ruff format --check .
	cd frontend && npm run lint

format: ## Code formatieren
	cd backend && .venv/bin/ruff format . && .venv/bin/ruff check --fix .
	cd frontend && npx eslint --fix .

build: ## Frontend für Produktion bauen
	cd frontend && npm run build

run: build ## Produktion lokal: ein Prozess liefert API + SPA auf :8000
	cd backend && .venv/bin/uvicorn app.main:app --port 8000
