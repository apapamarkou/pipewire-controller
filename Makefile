.PHONY: run test lint lint-fix clean install uninstall packages package test-packages test-package help

APP_NAME  := pipewire-controller
SRC_DIR   := src/pipewire_controller
ICONS_DIR := $(HOME)/.local/share/icons/hicolor/256x256/apps
APPS_DIR  := $(HOME)/.local/share/applications

help:
	@echo "PipeWire Audio Control Center — Development Commands"
	@echo "====================================================="
	@echo ""
	@echo "  make run           - Run the application"
	@echo "  make test          - Run test suite"
	@echo "  make lint          - Check code style"
	@echo "  make lint-fix      - Auto-fix code style"
	@echo "  make install       - Install for development"
	@echo "  make uninstall     - Uninstall"
	@echo "  make packages      - Build all packages"
	@echo "  make package       - Interactively build a package"
	@echo "  make test-packages - Test all built packages"
	@echo "  make test-package  - Interactively test a package"
	@echo "  make clean         - Remove build artifacts"
	@echo ""

run:
	PYTHONPATH=src python3 -m pipewire_controller

test:
	PYTHONPATH=src python3 -m pytest tests/ -v

lint:
	ruff check src/ tests/
	black --check src/ tests/

lint-fix:
	ruff check --fix src/ tests/
	black src/ tests/

install:
	pip3 install -e ".[dev]"

uninstall:
	bash uninstall

clean:
	rm -rf build/ dist/ *.egg-info packaging/output/
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete 2>/dev/null || true

packages:
	bash packaging/scripts/packages.sh

package:
	bash packaging/scripts/packages.sh --interactive

test-packages:
	bash packaging/scripts/test-packages.sh

test-package:
	bash packaging/scripts/test-packages.sh --interactive
