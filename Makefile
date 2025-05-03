
# Makefile for Forex Bot PostgreSQL

.PHONY: help install dev-setup start stop test clean docker-build docker-up docker-down migrate backfill

help:
	@echo "Available commands:"
	@echo "  install      - Install Python dependencies"
	@echo "  dev-setup    - Set up development environment"
	@echo "  start        - Start the application"
	@echo "  stop         - Stop the application"
	@echo "  test         - Run tests"
	@echo "  clean        - Clean up temporary files"
	@echo "  docker-build - Build Docker image"
	@echo "  docker-up    - Start Docker services"
	@echo "  docker-down  - Stop Docker services"
	@echo "  migrate      - Run database migrations"
	@echo "  backfill     - Backfill data from 2025-01-01"

install:
	pip install -r requirements.txt

dev-setup: install
	@echo "Setting up development environment..."
	@if [ ! -f .env ]; then cp .env.example .env; echo "Created .env file from template"; fi
	@echo "Please edit .env file with your configuration"
	@echo "Then run: make docker-up"

start:
	python main.py

stop:
	@echo "Stopping application..."
	@pkill -f "python main.py" || true

test:
	pytest tests/ -v

clean:
	find . -type f -name "*.pyc" -delete
	find . -type d -name "__pycache__" -delete
	rm -rf .pytest_cache/
	rm -rf logs/*.log

docker-build:
	docker build -t forex-bot .

docker-up:
	docker-compose up -d postgres redis
	@echo "Waiting for services to start..."
	@sleep 10
	@echo "Services started. You can now run 'python main.py' or 'make start'"

docker-down:
	docker-compose down

docker-full-up:
	docker-compose up -d

docker-logs:
	docker-compose logs -f

migrate:
	python -c "from app.database.connection import init_database; init_database()"

backfill:
	python scripts/backfill_2025.py

backfill-dry:
	python scripts/backfill_2025.py --dry-run

migrate-sqlite:
	@echo "Usage: make migrate-sqlite SQLITE_PATH=/path/to/news.db"
	@if [ -n "$(SQLITE_PATH)" ]; then \
		python scripts/migrate_sqlite.py $(SQLITE_PATH); \
	else \
		echo "Please provide SQLITE_PATH parameter"; \
	fi

lint:
	flake8 app/ tests/ --max-line-length=120
	black --check app/ tests/

format:
	black app/ tests/

check: lint test
	@echo "All checks passed!"

# Development workflow
dev: dev-setup docker-up migrate
	@echo "Development environment ready!"
	@echo "Run 'make start' to start the application"

# Production deployment
deploy: install migrate
	@echo "Production deployment ready"
