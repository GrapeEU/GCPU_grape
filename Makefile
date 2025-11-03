.PHONY: help up down build logs shell-web shell-api test-web test-api lint-web lint-api clean install
.PHONY: graphdb-up graphdb-down graphdb-setup graphdb-logs graphdb-test graphdb-reset db status

# Default target
help:
	@echo "Grape Development Commands"
	@echo "=========================="
	@echo ""
	@echo "Main Services:"
	@echo "  make up          - Start all services (web + api)"
	@echo "  make down        - Stop all services"
	@echo "  make build       - Build all containers"
	@echo "  make logs        - View logs from all services"
	@echo ""
	@echo "Knowledge Graph:"
	@echo "  make load-kg     - Load knowledge graphs into GraphDB"
	@echo "  make run         - One-shot demo setup (GraphDB + demo KG + embeddings + stack)"
	@echo "  make graphdb-logs - Show GraphDB logs"
	@echo "  make graphdb-test - Test SPARQL connection"
	@echo "  make reset-db    - Reset GraphDB (delete all data)"
	@echo ""
	@echo "Development:"
	@echo "  make shell-web   - Open shell in web container"
	@echo "  make shell-api   - Open shell in api container"
	@echo "  make test-web    - Run frontend tests"
	@echo "  make test-api    - Run backend tests"
	@echo "  make lint-web    - Lint frontend code"
	@echo "  make lint-api    - Lint backend code"
	@echo ""
	@echo "Utilities:"
	@echo "  make status      - Show status of all services"
	@echo "  make clean       - Remove containers and artifacts"
	@echo "  make install     - Install dependencies locally"

# Start all services (GraphDB + Backend + Frontend)
up:
	@echo "🍇 Starting Grape stack..."
	docker-compose up -d --build
	@echo ""
	@echo "⏳ Waiting for services to be ready..."
	@sleep 5
	@echo ""
	@echo "✅ Services started!"
	@echo "   • GraphDB:  http://localhost:7200"
	@echo "   • Backend:  http://localhost:8000"
	@echo "   • Frontend: http://localhost:3000"
	@echo ""
	@echo "📋 Next steps:"
	@echo "   1. Load knowledge graphs: make load-kg"
	@echo "   2. Check status: make status"
	@echo "   3. View logs: make logs"

# Stop services
down:
	docker-compose down

# Build all containers
build:
	docker-compose build

# View logs
logs:
	docker-compose logs -f

# Shell access
shell-web:
	docker-compose exec web sh

shell-api:
	docker-compose exec api bash

# Run tests
test-web:
	docker-compose exec web npm run test

test-api:
	docker-compose exec api uv run pytest tests/ -v

# Linting
lint-web:
	docker-compose exec web npm run lint
	docker-compose exec web npm run format

lint-api:
	docker-compose exec api ruff check . --fix
	docker-compose exec api black .
	docker-compose exec api ruff format .

# Clean up
clean:
	docker-compose down -v --remove-orphans
	rm -rf apps/web/.next apps/web/node_modules
	find . -type d -name "__pycache__" -exec rm -rf {} +
	@echo "✓ Cleaned up Docker containers, volumes, and build artifacts"

# Local installation (optional - for IDE support)
install:
	cd apps/web && npm install
	cd apps/backend && uv venv && uv pip install -r requirements.txt
	@echo "✓ Dependencies installed locally"

# ========================================
# GraphDB Commands
# ========================================

load-kg:
	@echo "📥 Setting up GraphDB repositories and loading knowledge graphs..."
	@python3 scripts/create_repos.py
	@echo ""
	@echo "📥 Loading JSON-LD files..."
	@./scripts/setup_graphdb.sh

graphdb-logs:
	docker logs -f grape-graphdb

graphdb-test:
	@echo "🔍 Testing SPARQL endpoints..."
	python scripts/test_sparql.py

reset-db:
	@echo "⚠️  Resetting GraphDB (this will delete all data)..."
	docker-compose down -v
	docker volume rm grape_graphdb-data grape_graphdb-import 2>/dev/null || true
	@echo "✅ Database volumes removed"
	@echo "   Run 'make up' and 'make load-kg' to recreate"

status:
	@echo "🍇 Grape Services Status"
	@echo "========================"
	@echo ""
	@docker-compose ps
	@echo ""
	@echo "📊 Service URLs:"
	@if docker ps | grep -q grape-graphdb; then \
		echo "  ✅ GraphDB:  http://localhost:7200 (healthy)"; \
	else \
		echo "  ❌ GraphDB:  Not running"; \
	fi

# One-shot demo runner: start stack, load demo KG, pull model, generate embeddings
run:
	@echo "🚀 Running full demo setup..."
	docker-compose up -d --build
	@echo "⏳ Waiting for GraphDB to be ready..." && sleep 5
	@bash scripts/refresh_unified_demo.sh
	@echo "📦 Pulling Ollama model (nomic-embed-text) if needed..."
	-@docker-compose exec -T ollama ollama pull nomic-embed-text 2>/dev/null || true
	@echo "🧠 Generating embeddings for unified..."
	-@docker-compose exec -T api python scripts/generate_grape_embeddings.py unified || \
	  (echo "Fallback: run locally" && python scripts/generate_grape_embeddings.py unified)
	@echo "✅ Demo environment ready."
	@echo "   • GraphDB:  http://localhost:7200"
	@echo "   • Backend:  http://localhost:8000"
	@echo "   • Frontend: http://localhost:3000"
	@if docker ps | grep -q grape-api; then \
		echo "  ✅ Backend:  http://localhost:8000 (healthy)"; \
	else \
		echo "  ❌ Backend:  Not running"; \
	fi
	@if docker ps | grep -q grape-web; then \
		echo "  ✅ Frontend: http://localhost:3000 (healthy)"; \
	else \
		echo "  ❌ Frontend: Not running"; \
	fi
