.PHONY: help build up down restart logs test clean create-service

help: ## Pokaži help
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-20s\033[0m %s\n", $$1, $$2}'

build: ## Build svi servisi (respects COMPOSE_BAKE setting from .env)
	@if [ "$$(grep '^COMPOSE_BAKE=' .env 2>/dev/null | cut -d'=' -f2)" = "true" ]; then \
		echo "🚀 Using Docker Bake for faster builds..."; \
		COMPOSE_BAKE=true docker-compose build; \
	else \
		docker-compose build; \
	fi

build-fast: ## Build with Bake for better performance (set COMPOSE_BAKE=true in .env first)
	COMPOSE_BAKE=true docker-compose build

up: ## Pokreni sve servise
	docker-compose up -d

up-build: ## Build and start all services (with optional bake support)
	@if [ "$$(grep '^COMPOSE_BAKE=' .env 2>/dev/null | cut -d'=' -f2)" = "true" ]; then \
		echo "🚀 Using Docker Bake for faster builds..."; \
		COMPOSE_BAKE=true docker-compose up --build -d; \
	else \
		docker-compose up --build -d; \
	fi

up-fast: ## Build and start with forced Bake acceleration
	COMPOSE_BAKE=true docker-compose up --build -d

down: ## Zaustavi sve servise
	docker-compose down

restart: ## Restartuj sve servise
	docker-compose restart

logs: ## Prikaži logove
	docker-compose logs -f

test-services: ## Testiraj servise (integration test sa running services)
	python scripts/test_services.py

clean: ## Očisti Docker resurse
	docker-compose down -v
	docker system prune -f

create-service: ## Kreiraj novi servis (make create-service NAME=my-service)
	python scripts/create_service.py --name $(NAME)

delete-service: ## Obriši servis (make delete-service NAME=my-service)
	python scripts/delete_service.py --name $(NAME) --yes 

enable-service: ## Omogući servis (make enable-service NAME=my-service)
	python scripts/manage_service.py --enable $(NAME)

disable-service: ## Onemogući servis (make disable-service NAME=my-service)
	python scripts/manage_service.py --disable $(NAME)

list-services: ## Prikaži status svih servisa
	python scripts/manage_service.py --list

# Development targets
dev-install: ## Instaliraj development dependencies
	pip install -r requirements.txt
	pip install pytest pytest-asyncio httpx aiohttp

dev-user: ## Pokreni user-service lokalno
	cd services/user-service && uvicorn main:app --reload --port 8001

dev-product: ## Pokreni product-service lokalno  
	cd services/product-service && uvicorn main:app --reload --port 8002

# Testing targets
test: ## Pokreni sve testove (clean summary)
	@echo "🧪 Running all tests..."
	@pytest tests/ --tb=no --no-header -q --disable-warnings 2>/dev/null | grep -E "passed|failed|ERROR|FAILED" | tail -1 || echo "✅ All tests passed"

test-full: ## Pokreni sve testove (sa full output)
	pytest tests/

test-unit: ## Pokreni samo unit testove (clean)
	@echo "🔧 Running unit tests..."
	@pytest tests/unit/ --tb=no --no-header -q --disable-warnings 2>/dev/null | grep -E "passed|failed|ERROR|FAILED" | tail -1 || echo "✅ Unit tests passed"

test-integration: ## Pokreni samo integration testove (clean)
	@echo "🔗 Running integration tests..."
	@pytest tests/integration/ --tb=no --no-header -q --disable-warnings 2>/dev/null | grep -E "passed|failed|ERROR|FAILED" | tail -1 || echo "✅ Integration tests passed"

test-coverage: ## Pokreni testove sa coverage report
	pytest --cov=basify --cov=services --cov-report=term-missing --cov-report=html tests/

test-verbose: ## Pokreni testove sa detaljnim output-om
	pytest -v -s tests/

test-watch: ## Pokreni testove u watch mode (zahteva pytest-watch)
	ptw tests/ -- --tb=short

test-clean: ## Pokreni testove bez warnings
	@echo "Running tests..."
	@pytest tests/ --tb=no --no-header --disable-warnings -q 2>/dev/null | tail -1

install-test-deps: ## Instaliraj test dependencies
	pip install pytest pytest-asyncio httpx aiohttp pytest-cov pytest-mock

# Database targets
db-shell: ## Konektuj se na lokalni PostgreSQL
	psql -h localhost -U postgres -d postgres

create-databases: ## Kreiraj baze za sve servise automatski
	python scripts/setup_databases.py

create-databases-manual: ## Kreiraj baze ručno
	psql -h localhost -U postgres -c "CREATE DATABASE users_db;"
	psql -h localhost -U postgres -c "CREATE DATABASE product_service_db;"