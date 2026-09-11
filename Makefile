.DEFAULT_GOAL := help
PY := .venv/Scripts/python.exe
ifeq (,$(wildcard .venv/Scripts/python.exe))
PY := .venv/bin/python
endif
PORT ?= 8000

.PHONY: help setup api web dev test lint format demo clean

help: ## Show this help
	@grep -hE '^[a-z-]+:.*?## ' $(MAKEFILE_LIST) | awk -F':.*?## ' '{printf "  \033[36m%-8s\033[0m %s\n", $$1, $$2}'

setup: ## Create the venv, install the backend and the frontend
	python -m venv .venv
	$(PY) -m pip install --upgrade pip
	$(PY) -m pip install -e ".[dev]"
	cd frontend && npm install

api: ## Run the API (override the port with PORT=8010)
	$(PY) -m uvicorn setubiz.api:app --reload --port $(PORT) --app-dir backend

web: ## Run the PWA dev server (proxies /api to SETUBIZ_API, default localhost:8000)
	cd frontend && npm run dev

dev: ## Run both, API in the background
	$(MAKE) api & $(MAKE) web

test: ## Run the suite; the deterministic decision layer must stay at 100%
	$(PY) -m pytest backend/tests \
		--cov=setubiz.finance --cov=setubiz.eligibility --cov=setubiz.documents \
		--cov-fail-under=100

lint: ## Lint and typecheck both halves
	$(PY) -m ruff check backend
	$(PY) -m ruff format --check backend
	cd frontend && npx tsc --noEmit

format: ## Autoformat the backend
	$(PY) -m ruff check backend --fix
	$(PY) -m ruff format backend

demo: ## One-command boot: docker compose up
	docker compose up --build

clean:
	rm -rf .venv frontend/node_modules frontend/dist .pytest_cache .coverage
