COMPOSE_DEV = docker compose
COMPOSE_PROD = docker compose -f docker-compose.prod.yml --env-file .env.prod
BACKEND_SERVICE = backend

.DEFAULT_GOAL := help

.PHONY: help up up-build build build-no-cache down restart ps logs logs-backend shell \
	migrate migrate-down migrate-current migrate-history migrate-stamp makemigration \
	test-deps test health frontend-dev frontend-build \
	prod-up prod-down prod-ps prod-logs prod-migrate \
	backup restore-verify clean clean-volumes

help:
	@echo "Wealth & Investment Intelligence Platform - Docker & Ops Makefile"
	@echo ""
	@echo "Development (Docker backend + local PostgreSQL):"
	@echo "  make up               Start development containers in background"
	@echo "  make up-build         Build and start development containers"
	@echo "  make build            Build backend Docker image"
	@echo "  make build-no-cache   Rebuild backend Docker image without cache"
	@echo "  make down             Stop development containers"
	@echo "  make restart          Restart backend container"
	@echo "  make ps               Show development container status"
	@echo "  make logs             Follow all development container logs"
	@echo "  make logs-backend     Follow backend container logs"
	@echo "  make shell            Open shell inside running backend container"
	@echo ""
	@echo "Database & Alembic Migrations:"
	@echo "  make migrate          Apply all pending migrations (alembic upgrade head)"
	@echo "  make migrate-down     Rollback the latest migration (alembic downgrade -1)"
	@echo "  make migrate-current  Show current Alembic revision"
	@echo "  make migrate-history  Show Alembic migration history"
	@echo "  make migrate-stamp    Stamp baseline revision on existing DB schema"
	@echo "  make makemigration m=\"msg\"  Autogenerate a new migration revision"
	@echo ""
	@echo "Testing & Frontend:"
	@echo "  make test-deps        Install pytest & test dependencies in backend container"
	@echo "  make test             Run backend pytest suite inside container"
	@echo "  make health           Check backend /health endpoint"
	@echo "  make frontend-dev     Run local Vite frontend dev server"
	@echo "  make frontend-build   Run vue-tsc type-check and Vite production build"
	@echo ""
	@echo "Production & Backups:"
	@echo "  make prod-up          Build & start production stack (Traefik + TLS)"
	@echo "  make prod-down        Stop production stack"
	@echo "  make prod-ps          Show production container status"
	@echo "  make prod-logs        Follow production logs"
	@echo "  make prod-migrate     Run migrations on production backend"
	@echo "  make backup           Create compressed PostgreSQL backup"
	@echo "  make restore-verify file=backups/xxx.sql.gz  Test-restore backup into temp DB"
	@echo ""
	@echo "Cleanup:"
	@echo "  make clean            Stop dev containers and prune dangling images"
	@echo "  make clean-volumes    Stop dev containers and remove volumes"

# --- Development ---
up:
	$(COMPOSE_DEV) up -d

up-build:
	$(COMPOSE_DEV) up -d --build

build:
	$(COMPOSE_DEV) build $(BACKEND_SERVICE)

build-no-cache:
	$(COMPOSE_DEV) build --no-cache $(BACKEND_SERVICE)

down:
	$(COMPOSE_DEV) down

restart:
	$(COMPOSE_DEV) restart $(BACKEND_SERVICE)

ps:
	$(COMPOSE_DEV) ps

logs:
	$(COMPOSE_DEV) logs -f

logs-backend:
	$(COMPOSE_DEV) logs -f $(BACKEND_SERVICE)

shell:
	$(COMPOSE_DEV) exec $(BACKEND_SERVICE) sh

# --- Database & Migrations ---
migrate:
	$(COMPOSE_DEV) exec $(BACKEND_SERVICE) alembic upgrade head

migrate-down:
	$(COMPOSE_DEV) exec $(BACKEND_SERVICE) alembic downgrade -1

migrate-current:
	$(COMPOSE_DEV) exec $(BACKEND_SERVICE) alembic current

migrate-history:
	$(COMPOSE_DEV) exec $(BACKEND_SERVICE) alembic history

migrate-stamp:
	$(COMPOSE_DEV) exec $(BACKEND_SERVICE) alembic stamp head

makemigration:
ifndef m
	$(error Usage: make makemigration m="describe_change")
endif
	$(COMPOSE_DEV) exec $(BACKEND_SERVICE) alembic revision --autogenerate -m "$(m)"

# --- Testing & Frontend ---
test-deps:
	$(COMPOSE_DEV) exec $(BACKEND_SERVICE) pip install --no-cache-dir -r requirements-dev.txt

test:
	$(COMPOSE_DEV) exec $(BACKEND_SERVICE) pytest -v

health:
	curl -fsS http://localhost:8000/health

frontend-dev:
	cd frontend && npm run dev

frontend-build:
	cd frontend && npm run build

# --- Production ---
prod-up:
	$(COMPOSE_PROD) up -d --build

prod-down:
	$(COMPOSE_PROD) down

prod-ps:
	$(COMPOSE_PROD) ps

prod-logs:
	$(COMPOSE_PROD) logs -f

prod-migrate:
	$(COMPOSE_PROD) exec $(BACKEND_SERVICE) alembic upgrade head

backup:
	./scripts/backup_postgres.sh

restore-verify:
ifndef file
	$(error Usage: make restore-verify file=backups/finance_tracker_xxx.sql.gz)
endif
	./scripts/restore_postgres.sh "$(file)" --verify-sandbox

# --- Cleanup ---
clean:
	$(COMPOSE_DEV) down --remove-orphans
	docker image prune -f

clean-volumes:
	$(COMPOSE_DEV) down -v --remove-orphans
