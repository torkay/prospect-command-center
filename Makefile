.PHONY: install dev test lint format clean docker run

# Install production dependencies
install:
	pip install -e .
	playwright install chromium

# Install development dependencies
dev:
	pip install -e ".[dev]"
	playwright install chromium

# Run tests
test:
	pytest tests/ -v --tb=short

# Run tests with coverage
test-cov:
	pytest tests/ -v --cov=prospect --cov-report=html

# Run integration tests (requires API keys)
test-integration:
	pytest tests/ -v -m integration

# Lint code
lint:
	ruff check prospect/ tests/
	black --check prospect/ tests/

# Format code
format:
	ruff check --fix prospect/ tests/
	black prospect/ tests/

# Clean build artifacts
clean:
	rm -rf build/ dist/ *.egg-info .pytest_cache .coverage htmlcov/
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true

# Build Docker image
docker:
	docker build -t prospect-command-center -f docker/Dockerfile .

# Run web server
run:
	uvicorn prospect.web.app:app --reload --host 127.0.0.1 --port 8000

# Run CLI help
cli:
	prospect --help

# Check configuration
check:
	prospect check
