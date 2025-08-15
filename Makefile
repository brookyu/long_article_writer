# Long Article Writer - Development Makefile

.PHONY: help setup start stop restart logs clean build pull-models test

# Default target
help:
	@echo "Long Article Writer - Available Commands:"
	@echo ""
	@echo "  setup         - Initial setup (copy env, create directories)"
	@echo "  start         - Start all services"
	@echo "  stop          - Stop all services"
	@echo "  restart       - Restart all services"
	@echo "  logs          - Show logs from all services"
	@echo "  pull-models   - Download required Ollama models"
	@echo "  clean         - Clean up containers and volumes"
	@echo "  build         - Build Docker images"
	@echo "  test          - Run tests"
	@echo "  dev-backend   - Run backend in development mode"
	@echo "  dev-frontend  - Run frontend in development mode"

# Initial setup
setup:
	@echo "Setting up Long Article Writer..."
	@if [ ! -f .env ]; then cp env.example .env; echo "Created .env file"; fi
	@mkdir -p uploads exports logs
	@echo "Setup complete! Edit .env file if needed, then run 'make start'"

# Start all services
start:
	@echo "Starting Long Article Writer services..."
	docker-compose up -d
	@echo "Services started! Check status with 'docker-compose ps'"
	@echo "Frontend: http://localhost:3000"
	@echo "Backend API: http://localhost:8000/api/docs"

# Stop all services
stop:
	@echo "Stopping services..."
	docker-compose down

# Restart all services
restart: stop start

# Show logs
logs:
	docker-compose logs -f

# Pull required Ollama models
pull-models:
	@echo "Pulling Ollama models (this may take 10-15 minutes)..."
	@echo "Waiting for Ollama to be ready..."
	@until docker exec law_ollama ollama list > /dev/null 2>&1; do sleep 2; done
	docker exec law_ollama ollama pull llama3.1:8b
	docker exec law_ollama ollama pull nomic-embed-text
	@echo "Models downloaded! Check with: docker exec law_ollama ollama list"

# Clean up (WARNING: This will delete all data!)
clean:
	@echo "WARNING: This will delete all containers, volumes, and data!"
	@read -p "Are you sure? [y/N] " -n 1 -r; \
	echo; \
	if [[ $$REPLY =~ ^[Yy]$$ ]]; then \
		docker-compose down -v --remove-orphans; \
		docker system prune -f; \
		rm -rf uploads/* exports/* logs/*; \
		echo "Cleanup complete!"; \
	else \
		echo "Cleanup cancelled."; \
	fi

# Build Docker images
build:
	@echo "Building Docker images..."
	docker-compose build

# Run tests (placeholder)
test:
	@echo "Running tests..."
	@echo "Backend tests:"
	@if [ -d "backend" ]; then \
		cd backend && python -m pytest tests/ -v || echo "No backend tests found"; \
	fi
	@echo "Frontend tests:"
	@if [ -d "frontend" ]; then \
		cd frontend && npm test || echo "No frontend tests configured"; \
	fi

# Development mode - backend only
dev-backend:
	@echo "Starting backend in development mode..."
	@echo "Make sure Docker services are running: make start"
	cd backend && \
	export DATABASE_URL="mysql://law_user:law_password@localhost:3306/long_article_writer" && \
	export MILVUS_HOST="localhost" && \
	export OLLAMA_HOST="localhost" && \
	uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# Development mode - frontend only
dev-frontend:
	@echo "Starting frontend in development mode..."
	cd frontend && npm install && npm run dev

# Check service health
health:
	@echo "Checking service health..."
	@curl -s http://localhost:8000/health | jq . || echo "Backend not responding"
	@curl -s http://localhost:3000 > /dev/null && echo "Frontend: OK" || echo "Frontend: Not responding"

# Show service status
status:
	@echo "Service Status:"
	@docker-compose ps

# View specific service logs
logs-backend:
	docker-compose logs -f backend

logs-frontend:
	docker-compose logs -f frontend

logs-mysql:
	docker-compose logs -f mysql

logs-milvus:
	docker-compose logs -f milvus

logs-ollama:
	docker-compose logs -f ollama

# Database operations
db-shell:
	docker exec -it law_mysql mysql -u law_user -p long_article_writer

# Ollama operations
ollama-shell:
	docker exec -it law_ollama bash

ollama-models:
	docker exec law_ollama ollama list

# Quick start for new users
quickstart: setup start
	@echo ""
	@echo "🚀 Long Article Writer is starting up!"
	@echo ""
	@echo "Next steps:"
	@echo "1. Wait for services to be ready (30-60 seconds)"
	@echo "2. Run 'make pull-models' to download AI models"
	@echo "3. Visit http://localhost:3000 to start writing!"
	@echo ""
	@echo "Use 'make logs' to monitor startup progress"