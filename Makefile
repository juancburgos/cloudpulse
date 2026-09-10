# CloudPulse — developer entry points
# Everything a reviewer or a new contributor needs, behind one command.

SHELL := /bin/bash
COMPOSE := docker compose -f deploy/docker-compose.yml
API_HOST ?= 127.0.0.1:8001

.DEFAULT_GOAL := help

.PHONY: help up down restart logs ps smoke test lint fmt bundle clean android-debug

help: ## Show this help
	@grep -hE '^[a-zA-Z_-]+:.*?## ' $(MAKEFILE_LIST) \
		| awk 'BEGIN{FS=":.*?## "}{printf "  \033[36m%-16s\033[0m %s\n", $$1, $$2}'

up: ## Build and start api + db (requires .env)
	@test -f .env || (echo "missing .env — copy .env.example" && exit 1)
	$(COMPOSE) up -d --build
	@echo "API on http://$(API_HOST) — run 'make smoke' when it settles"

down: ## Stop and remove containers (keeps the database volume)
	$(COMPOSE) down

restart: ## Recreate only the API container (no downtime for the database)
	$(COMPOSE) up -d --build api

logs: ## Tail logs from every service
	$(COMPOSE) logs -f --tail 100

ps: ## Show service status
	$(COMPOSE) ps

smoke: ## End-to-end check: health, status, write, read
	bash scripts/smoke-test.sh

test: ## Run the backend test suite
	cd backend && python -m pytest -q

lint: ## Check formatting and imports (no changes)
	cd backend && python -m ruff check app tests && python -m ruff format --check app tests

fmt: ## Apply formatting and import order
	cd backend && python -m ruff check --fix app tests && python -m ruff format app tests

android-debug: ## Build a debug APK
	cd android && ./gradlew assembleDebug

bundle: ## Build a signed release App Bundle (needs the upload keystore)
	cd android && ./gradlew bundleRelease

clean: ## Remove build outputs and stopped containers
	$(COMPOSE) down --remove-orphans
	cd android && ./gradlew clean || true
	find . -name __pycache__ -type d -prune -exec rm -rf {} + 2>/dev/null || true
