# screenmates — common tasks. `make help` lists them.
SHELL := /bin/bash
VENV  := backend/.venv
PY    := $(VENV)/bin/python

.PHONY: help install kino-install dev backend frontend kino-server test test-backend test-e2e migration lint format build run lock
MTX   := .tools/mediamtx
# With MediaMTX installed, `make dev`/`make run` switch the Kino on automatically.
KINO  := $(if $(wildcard $(MTX)),MEDIAMTX_WEBRTC_URL=http://127.0.0.1:8889,)

help:
	@grep -E '^[a-z0-9-]+:.*## ' $(MAKEFILE_LIST) | awk -F':.*## ' '{printf "  \033[1m%-13s\033[0m %s\n", $$1, $$2}'

install: ## Install the backend venv and frontend dependencies
	test -d $(VENV) || python3 -m venv $(VENV)
	$(PY) -m pip install -q -r backend/requirements-dev.txt
	cd frontend && npm ci

kino-install: ## Download MediaMTX for the cinema (.tools/mediamtx)
	./scripts/mediamtx.sh

dev: ## Start backend (:8000), Vite (:5173) and – if installed – the cinema media server
	@trap 'kill 0' EXIT; \
	if [ -x $(MTX) ]; then $(MAKE) -s kino-server & fi; \
	$(MAKE) -s backend & $(MAKE) -s frontend & wait

backend: ## Backend only, with auto-reload
	cd backend && $(KINO) .venv/bin/uvicorn app.main:app --reload --port 8000

kino-server: ## MediaMTX (cinema) only, with deploy/mediamtx.yml
	$(MTX) deploy/mediamtx.yml

frontend: ## Vite dev server only
	cd frontend && npm run dev

test: test-backend test-e2e ## All tests

test-backend: ## pytest
	cd backend && .venv/bin/pytest

test-e2e: ## Playwright against the real backend (needs `npx playwright install chromium`)
	cd frontend && npm run test:e2e

migration: ## Generate a DB migration from model changes: make migration name="add column xy"
	@test -n "$(name)" || (echo 'Usage: make migration name="…"' && exit 1)
	cd backend && .venv/bin/alembic revision --autogenerate -m "$(name)"
	@echo "Review the migration (notes at the top of the file) and commit it."

lint: ## ruff + eslint
	cd backend && .venv/bin/ruff check . && .venv/bin/ruff format --check .
	cd frontend && npm run lint

format: ## Format the code
	cd backend && .venv/bin/ruff format . && .venv/bin/ruff check --fix .
	cd frontend && npx eslint --fix .

lock: ## Re-pin the backend dependencies (requirements*.in -> requirements*.txt, with hashes)
	cd backend && .venv/bin/pip install -q pip-tools && \
	  .venv/bin/pip-compile -q --generate-hashes --strip-extras --allow-unsafe -o requirements.txt requirements.in && \
	  .venv/bin/pip-compile -q --generate-hashes --strip-extras --allow-unsafe -o requirements-dev.txt requirements-dev.in

build: ## Build the frontend for production
	cd frontend && npm run build

run: build ## Production locally: API + SPA on :8000 (plus the cinema media server, if installed)
	@trap 'kill 0' EXIT; \
	if [ -x $(MTX) ]; then $(MTX) deploy/mediamtx.yml & fi; \
	cd backend && $(KINO) .venv/bin/uvicorn app.main:app --port 8000 & wait
