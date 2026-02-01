.PHONY: help install install-dev test test-v test-cov lint format clean

.DEFAULT_GOAL := help

# Colors
BLUE := \033[36m
RESET := \033[0m

help: ## Show this help message
	@echo "Usage: make [target]"
	@echo ""
	@echo "Targets:"
	@awk 'BEGIN {FS = ":.*##"} /^[a-zA-Z_-]+:.*##/ { printf "  $(BLUE)%-15s$(RESET) %s\n", $$1, $$2 }' $(MAKEFILE_LIST)

install: ## Install dependencies
	uv sync

install-dev: ## Install dependencies including dev tools
	uv sync --all-groups --all-extras --all-packages

test: ## Run tests
	uv run python -m pytest

test-v: ## Run tests with verbose output
	uv run python -m pytest -v

test-cov: ## Run tests with coverage report
	uv run python -m pytest --cov=workgarden --cov-report=term-missing

lint: ## Run linter (ruff)
	uv run ruff check src tests --fix

format: ## Format code (ruff)
	uv run ruff format src tests
	uv run ruff check --fix src tests

clean: ## Remove build artifacts and cache
	rm -rf build dist *.egg-info .pytest_cache .ruff_cache .coverage
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
