# Makefile for steering-wizard development tasks

.PHONY: help install test test-cov lint format format-check type-check quality clean docker-test

help:  ## Show this help message
	@echo "Available commands:"
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-15s\033[0m %s\n", $$1, $$2}'

install:  ## Install dependencies with Poetry
	poetry install

test:  ## Run tests with pytest
	poetry run pytest -v

test-cov:  ## Run tests with coverage reporting
	poetry run pytest --cov=steering_wizard --cov-report=html --cov-report=term

lint:  ## Run pylint on source code
	poetry run pylint src/steering_wizard

format:  ## Format code with Black
	poetry run black src tests

format-check:  ## Check code formatting with Black
	poetry run black --check src tests

type-check:  ## Run mypy type checking
	poetry run mypy src/steering_wizard

quality:  ## Run all quality checks (format, lint, type-check)
	poetry run black --check src tests
	poetry run pylint src/steering_wizard
	poetry run mypy src/steering_wizard

clean:  ## Clean up generated files
	rm -rf .pytest_cache
	rm -rf htmlcov
	rm -rf .coverage
	rm -rf dist
	rm -rf build
	rm -rf *.egg-info

docker-test:  ## Run tests in Docker across Python versions
	./scripts/test-all-versions.sh

docker-build:  ## Build Docker images for all Python versions
	docker-compose build

docker-test-py311:  ## Test with Python 3.11 in Docker
	docker-compose run --rm test-py311

docker-test-py312:  ## Test with Python 3.12 in Docker
	docker-compose run --rm test-py312

docker-test-py313:  ## Test with Python 3.13 in Docker
	docker-compose run --rm test-py313