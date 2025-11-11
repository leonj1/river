.PHONY: help install test test-unit test-integration start-redis stop-redis clean

help:
	@echo "River Python - Available Commands"
	@echo ""
	@echo "  make install            Install all packages in development mode"
	@echo "  make test               Run all tests (unit + integration)"
	@echo "  make test-unit          Run unit tests only"
	@echo "  make test-integration   Run integration tests (requires Redis)"
	@echo "  make start-redis        Start Redis containers with Docker Compose"
	@echo "  make stop-redis         Stop Redis containers"
	@echo "  make clean              Clean up Python cache and build artifacts"
	@echo ""

install:
	@echo "Installing river-core..."
	cd packages/river-core && pip install -e ".[dev]"
	@echo "Installing river-provider-redis..."
	cd packages/river-provider-redis && pip install -e ".[dev]"
	@echo "Installing river-adapter-fastapi..."
	cd packages/river-adapter-fastapi && pip install -e ".[dev]"
	@echo "✅ All packages installed"

test: test-unit test-integration

test-unit:
	@echo "Running unit tests..."
	pytest packages/river-core/tests -v

test-integration: start-redis
	@echo "Waiting for Redis to be ready..."
	@sleep 2
	@echo "Running integration tests..."
	REDIS_URL=redis://localhost:6380 pytest packages/ -v -m integration
	@echo "✅ Integration tests complete"

start-redis:
	@echo "Starting Redis containers..."
	docker-compose up -d
	@echo "Waiting for Redis to be healthy..."
	@timeout 30 sh -c 'until docker-compose ps | grep -q "healthy"; do sleep 1; done' || echo "Redis started"
	@echo "✅ Redis containers running"

stop-redis:
	@echo "Stopping Redis containers..."
	docker-compose down
	@echo "✅ Redis containers stopped"

clean:
	@echo "Cleaning Python cache and build artifacts..."
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name "*.egg-info" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".pytest_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name "dist" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name "build" -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete
	@echo "✅ Cleanup complete"
