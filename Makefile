.PHONY: help install install-dev install-deps setup test test-cov lint format clean build docs

# Default target
help:
	@echo "Available targets:"
	@echo "  setup        Complete setup (install system deps + package)"
	@echo "  install-deps Install system dependencies (Ubuntu/Debian)"
	@echo "  install      Install package in development mode"
	@echo "  install-dev  Install package with development dependencies"
	@echo "  test         Run tests"
	@echo "  test-cov     Run tests with coverage report"
	@echo "  lint         Run linting (flake8, mypy)"
	@echo "  format       Format code with black"
	@echo "  clean        Clean build artifacts"
	@echo "  build        Build package"
	@echo "  docs         Generate documentation"
	@echo "  init-db      Initialize database"
	@echo "  migration    Create new database migration"

# System Dependencies
# Install required system packages for Ubuntu/Debian systems
# This includes python3-venv which is needed for isolated build environments
install-deps:
	@echo "Installing system dependencies for Ubuntu/Debian..."
	@echo "This will install: python3-venv, python3-pip, python3-dev, build-essential, git"
	@echo "Note: This requires sudo privileges"
	sudo apt update
	sudo apt install -y python3-venv python3-pip python3-dev build-essential git
	@echo "System dependencies installed successfully!"
	@echo "You can now run 'make install' to install the Python package."

# Complete Setup
# One-command setup: install system dependencies and Python package
setup: install-deps install
	@echo "Complete setup finished! You can now use 'ynab-itemized --help' to get started."

# Installation
install: build
	pip install dist/ynab_itemized-0.1.0-py3-none-any.whl

install-dev: install
	pip install ".[dev]"
	pre-commit install

# Testing
test:
	pytest

test-cov:
	pytest --cov=src/ynab_itemized --cov-report=term-missing --cov-report=html

# Code quality
lint:
	flake8 src/ tests/
	mypy src/

format:
	black src/ tests/
	isort src/ tests/

# Cleanup
clean:
	rm -rf build/
	rm -rf dist/
	rm -rf *.egg-info/
	rm -rf .pytest_cache/
	rm -rf .mypy_cache/
	rm -rf htmlcov/
	find . -type d -name __pycache__ -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete

# Build
build: clean
	python -m build

# Database
init-db:
	ynab-itemized init-db

migration:
	alembic revision --autogenerate -m "$(MSG)"

migrate:
	alembic upgrade head

# Documentation (placeholder)
docs:
	@echo "Documentation generation not yet implemented"
