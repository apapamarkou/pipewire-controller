"""Pytest configuration for headless GUI testing."""

import os
import pytest


def pytest_configure(config):
    """Configure pytest for headless testing."""
    # Set Qt platform to offscreen for headless testing
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    os.environ.setdefault("QT_DEBUG_PLUGINS", "0")


@pytest.fixture(scope="session")
def qapp_args():
    """Arguments for QApplication."""
    return []
