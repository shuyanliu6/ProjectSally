.PHONY: help docker-build docker-up docker-down docker-logs docker-shell db-init db-reset test clean

# Default target
help:
	@echo "Project Sally - Docker Commands"
	@echo "================================"
	@echo ""
	@echo "Docker Management:"
	@echo "  make docker-build    - Build Docker images"
	@echo "  make docker-up       - Start all services"
	@echo "  make docker-down     - Stop all services"
	@echo "  make docker-logs     - View service logs"
	@echo "  make docker-shell    - Connect to app container"
	@echo ""
	@echo "Database:"
	@echo "  make db-init         - Initialize database"
	@echo "  make db-reset        - Reset database (WARNING!)"
	@echo "  make db-shell        - Connect to database"
	@echo ""
	@echo "Testing & Development:"
	@echo "  make test            - Run test suite"
	@echo "  make lint            - Run code linting"
	@echo "  make format          - Format code"
	@echo ""
	@echo "Cleanup:"
	@echo "  make clean           - Remove containers and volumes"
	@echo ""

# Docker commands
docker-build:
	docker-compose build --no-cache

docker-up:
	docker-compose up -d
	@echo "✓ Services started"
	@echo "  Database: localhost:5432"
	@echo "  App: docker-compose exec app bash"

docker-down:
	docker-compose down
	@echo "✓ Services stopped"

docker-logs:
	docker-compose logs -f

docker-shell:
	docker-compose exec app bash

# Database commands
db-init:
	docker-compose exec app python scripts/init_db.py --create
	@echo "✓ Database initialized"

db-reset:
	@echo "WARNING: This will delete all data!"
	@read -p "Are you sure? (yes/no): " confirm; \
	if [ "$$confirm" = "yes" ]; then \
		docker-compose exec app python scripts/init_db.py --reset; \
		echo "✓ Database reset"; \
	else \
		echo "Cancelled"; \
	fi

db-shell:
	docker-compose exec database psql -U stock_user -d stock_picking_system

# Testing
test:
	docker-compose exec app python scripts/test_setup.py

lint:
	docker-compose exec app flake8 src/ --max-line-length=100

format:
	docker-compose exec app black src/ scripts/
	docker-compose exec app isort src/ scripts/

# Cleanup
clean:
	docker-compose down -v
	find . -type d -name __pycache__ -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete
	@echo "✓ Cleanup complete"

# Development workflow
dev: docker-up db-init test
	@echo "✓ Development environment ready!"
	@echo "Connect with: make docker-shell"

# Production-like workflow
prod-test: docker-build docker-up db-init test
	@echo "✓ Production test complete"
