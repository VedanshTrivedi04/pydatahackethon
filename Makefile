# ShipFaster — Developer Convenience Makefile
# Usage: make <target>

.PHONY: help up down api worker migrate seed lint test

help:
	@echo ""
	@echo "ShipFaster Dev Commands:"
	@echo "  make up       - Start Docker stack (Postgres, Redis, MinIO)"
	@echo "  make down     - Stop Docker stack"
	@echo "  make api      - Start FastAPI dev server (port 8000)"
	@echo "  make worker   - Start Celery worker (all queues)"
	@echo "  make migrate  - Run Alembic migrations"
	@echo "  make seed     - Seed demo tenant"
	@echo "  make lint     - Run ruff linter"
	@echo "  make test     - Run test suite"
	@echo ""

up:
	docker-compose -f infra/docker-compose.yml up -d
	@echo "Stack started. Postgres=5434, Redis=6380, MinIO=9000"

down:
	docker-compose -f infra/docker-compose.yml down

api:
	uvicorn engine.api.main:app --reload --port 8000 --log-level info

worker:
	celery -A engine.core.queue.celery_app.celery_app worker \
		--loglevel=info \
		--queues=shipfaster.high,shipfaster.default,shipfaster.low,shipfaster.dlq \
		--concurrency=4

worker-high:
	celery -A engine.core.queue.celery_app.celery_app worker \
		--loglevel=info \
		--queues=shipfaster.high \
		--concurrency=2 \
		--hostname=high-worker@%h

migrate:
	alembic upgrade head

migrate-gen:
	@read -p "Migration message: " msg; \
	alembic revision --autogenerate -m "$$msg"

seed:
	python scripts/seed_demo_tenant.py

lint:
	ruff check engine/ tests/ --fix
	ruff format engine/ tests/

test:
	pytest -v tests/

test-cov:
	pytest tests/ --cov=engine --cov-report=html --cov-report=term-missing

worker-health:
	python -m engine.workers.health
