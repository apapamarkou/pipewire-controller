"""Tests for PipeWire controller."""

import pytest
import subprocess
from unittest.mock import Mock
from pipewire_controller.core.pipewire import PipeWireController


class TestPipeWireController:
    """Test PipeWire control functionality."""

    def test_set_sample_rate_success(self, mock_subprocess_run):
        """Test successful sample rate change."""
        mock_subprocess_run.return_value = Mock(returncode=0)
        
        result = PipeWireController.set_sample_rate(48000)
        
        assert result is True
        mock_subprocess_run.assert_called_once_with(
            ["pw-metadata", "-n", "settings", "0", "clock.force-rate", "48000"],
            check=True,
            capture_output=True,
            timeout=5
        )

    def test_set_sample_rate_failure(self, mock_subprocess_run):
        """Test sample rate change failure."""
        mock_subprocess_run.side_effect = subprocess.CalledProcessError(1, "pw-metadata")
        
        result = PipeWireController.set_sample_rate(48000)
        
        assert result is False

    def test_set_buffer_size_success(self, mock_subprocess_run):
        """Test successful buffer size change."""
        mock_subprocess_run.return_value = Mock(returncode=0)
        
        result = PipeWireController.set_buffer_size(512)
        
        assert result is True
        mock_subprocess_run.assert_called_once_with(
            ["pw-metadata", "-n", "settings", "0", "clock.force-quantum", "512"],
            check=True,
            capture_output=True,
            timeout=5
        )

    def test_set_buffer_size_timeout(self, mock_subprocess_run):
        """Test buffer size change timeout."""
        mock_subprocess_run.side_effect = subprocess.TimeoutExpired("pw-metadata", 5)
        
        result = PipeWireController.set_buffer_size(512)
        
        assert result is False

    def test_get_current_rate(self, mock_subprocess_run):
        """Test getting current sample rate."""
        mock_subprocess_run.return_value = Mock(
            stdout="key='clock.force-rate' value='48000' type=''\n",
            returncode=0
        )
        
        rate = PipeWireController.get_current_rate()
        
        assert rate == 48000

    def test_get_current_rate_not_set(self, mock_subprocess_run):
        """Test getting rate when not set."""
        mock_subprocess_run.return_value = Mock(stdout="", returncode=0)
        
        rate = PipeWireController.get_current_rate()
        
        assert rate is None

    def test_get_current_quantum(self, mock_subprocess_run):
        """Test getting current buffer size."""
        mock_subprocess_run.return_value = Mock(
            stdout="key='clock.force-quantum' value='512' type=''\n",
            returncode=0
        )
        
        quantum = PipeWireController.get_current_quantum()
        
        assert quantum == 512
