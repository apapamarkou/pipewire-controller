"""Pytest configuration and shared fixtures."""

import os
import pytest
from unittest.mock import Mock, MagicMock

# Configure Qt for headless testing
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("QT_DEBUG_PLUGINS", "0")


@pytest.fixture(scope="session")
def qapp_args():
    """Arguments for QApplication - session scoped to avoid multiple instances."""
    return []


@pytest.fixture
def mock_subprocess_run(mocker):
    """Mock subprocess.run for testing."""
    return mocker.patch("subprocess.run")


@pytest.fixture
def mock_config_file(tmp_path):
    """Create a temporary config directory."""
    config_dir = tmp_path / ".config" / "pipewire-controller"
    config_dir.mkdir(parents=True)
    return config_dir


@pytest.fixture
def sample_pw_dump_output():
    """Sample pw-dump JSON output."""
    return """
    [
        {
            "type": "PipeWire:Interface:Node",
            "info": {
                "props": {
                    "media.class": "Audio/Sink"
                },
                "params": {
                    "EnumFormat": [
                        {"rate": 48000},
                        {"rate": 96000},
                        {"rate": {"min": 44100, "max": 192000}}
                    ]
                }
            }
        }
    ]
    """
