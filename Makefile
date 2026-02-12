.PHONY: help install install-dev test test-cov format lint clean run build

help:
	@echo "PipeWire Controller - Development Commands"
	@echo "==========================================="
	@echo ""
	@echo "  make install      - Install package"
	@echo "  make install-dev  - Install with dev dependencies"
	@echo "  make test         - Run tests"
	@echo "  make test-cov     - Run tests with coverage"
	@echo "  make format       - Format code with black"
	@echo "  make lint         - Lint code with ruff"
	@echo "  make clean        - Remove build artifacts"
	@echo "  make run          - Run application"
	@echo "  make build        - Build distribution packages"
	@echo ""

install:
	pip install .

install-dev:
	pip install -e ".[dev]"

test:
	pytest -v

test-cov:
	pytest --cov=src/pipewire_controller --cov-report=term-missing --cov-report=html

format:
	black src/ tests/

lint:
	ruff check src/ tests/

clean:
	rm -rf build/ dist/ *.egg-info
	rm -rf .pytest_cache .coverage htmlcov/
	find . -type d -name __pycache__ -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete

run:
	PYTHONPATH=src python -m pipewire_controller

build:
	python -m build
