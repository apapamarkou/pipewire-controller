"""Pytest configuration and shared fixtures."""

import os

import pytest

# Headless Qt for CI
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("QT_DEBUG_PLUGINS", "0")


@pytest.fixture(scope="session")
def qapp_args():
    return []
