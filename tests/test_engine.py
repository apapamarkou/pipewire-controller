"""Tests for PipewireEngine - Pure logic testing without GUI."""

import pytest
import json
import subprocess
from unittest.mock import Mock, patch
from pipewire_controller.engine import PipewireEngine


class TestPipewireEngine:
    """Test PipeWire engine logic."""

    def test_set_sample_rate_success(self, mocker):
        """Test successful sample rate change."""
        mock_run = mocker.patch("subprocess.run")
        mock_run.return_value = Mock(returncode=0)
        
        engine = PipewireEngine()
        result = engine.set_sample_rate(48000)
        
        assert result is True
        mock_run.assert_called_once_with(
            ["pw-metadata", "-n", "settings", "0", "clock.force-rate", "48000"],
            check=True,
            capture_output=True,
            timeout=5
        )

    def test_set_sample_rate_failure(self, mocker):
        """Test sample rate change failure."""
        mock_run = mocker.patch("subprocess.run")
        mock_run.side_effect = subprocess.CalledProcessError(1, "pw-metadata")
        
        engine = PipewireEngine()
        result = engine.set_sample_rate(48000)
        
        assert result is False

    def test_set_buffer_size_success(self, mocker):
        """Test successful buffer size change."""
        mock_run = mocker.patch("subprocess.run")
        mock_run.return_value = Mock(returncode=0)
        
        engine = PipewireEngine()
        result = engine.set_buffer_size(512)
        
        assert result is True
        mock_run.assert_called_once_with(
            ["pw-metadata", "-n", "settings", "0", "clock.force-quantum", "512"],
            check=True,
            capture_output=True,
            timeout=5
        )

    def test_set_buffer_size_timeout(self, mocker):
        """Test buffer size change timeout."""
        mock_run = mocker.patch("subprocess.run")
        mock_run.side_effect = subprocess.TimeoutExpired("pw-metadata", 5)
        
        engine = PipewireEngine()
        result = engine.set_buffer_size(512)
        
        assert result is False

    def test_get_supported_rates_with_devices(self, mocker):
        """Test getting supported rates from pw-dump."""
        pw_dump_output = json.dumps([
            {
                "type": "PipeWire:Interface:Node",
                "info": {
                    "props": {"media.class": "Audio/Sink"},
                    "params": {
                        "EnumFormat": [
                            {"rate": 48000},
                            {"rate": 96000},
                            {"rate": 192000}
                        ]
                    }
                }
            }
        ])
        
        mock_run = mocker.patch("subprocess.run")
        mock_run.return_value = Mock(stdout=pw_dump_output, returncode=0)
        
        engine = PipewireEngine()
        rates = engine.get_supported_sample_rates()
        
        assert 48000 in rates
        assert 96000 in rates
        assert 192000 in rates
        assert rates == sorted(rates)

    def test_get_supported_rates_fallback_on_error(self, mocker):
        """Test fallback rates when pw-dump fails."""
        mock_run = mocker.patch("subprocess.run")
        mock_run.side_effect = subprocess.CalledProcessError(1, "pw-dump")
        
        engine = PipewireEngine()
        rates = engine.get_supported_sample_rates()
        
        assert 44100 in rates
        assert 48000 in rates
        assert len(rates) > 0

    def test_get_supported_rates_with_range(self, mocker):
        """Test rate extraction with min/max range."""
        pw_dump_output = json.dumps([
            {
                "type": "PipeWire:Interface:Node",
                "info": {
                    "props": {"media.class": "Audio/Source"},
                    "params": {
                        "EnumFormat": [
                            {"rate": {"min": 44100, "max": 96000}}
                        ]
                    }
                }
            }
        ])
        
        mock_run = mocker.patch("subprocess.run")
        mock_run.return_value = Mock(stdout=pw_dump_output, returncode=0)
        
        engine = PipewireEngine()
        rates = engine.get_supported_sample_rates()
        
        assert 44100 in rates
        assert 48000 in rates
        assert 96000 in rates
        assert 192000 not in rates

    def test_extract_rates_ignores_non_audio_devices(self):
        """Test that non-audio devices are ignored."""
        devices = [
            {
                "type": "PipeWire:Interface:Node",
                "info": {
                    "props": {"media.class": "Video/Source"},
                    "params": {"EnumFormat": [{"rate": 30}]}
                }
            }
        ]
        
        engine = PipewireEngine()
        rates = engine._extract_rates_from_devices(devices)
        
        assert len(rates) == 0

    def test_get_current_rate(self, mocker):
        """Test getting current sample rate."""
        mock_run = mocker.patch("subprocess.run")
        mock_run.return_value = Mock(
            stdout="key='clock.force-rate' value='48000' type=''\n",
            returncode=0
        )
        
        engine = PipewireEngine()
        rate = engine.get_current_rate()
        
        assert rate == 48000

    def test_get_current_rate_not_set(self, mocker):
        """Test getting rate when not set."""
        mock_run = mocker.patch("subprocess.run")
        mock_run.return_value = Mock(stdout="", returncode=0)
        
        engine = PipewireEngine()
        rate = engine.get_current_rate()
        
        assert rate is None

    def test_get_current_quantum(self, mocker):
        """Test getting current buffer size."""
        mock_run = mocker.patch("subprocess.run")
        mock_run.return_value = Mock(
            stdout="key='clock.force-quantum' value='512' type=''\n",
            returncode=0
        )
        
        engine = PipewireEngine()
        quantum = engine.get_current_quantum()
        
        assert quantum == 512

    def test_get_device_info(self, mocker):
        """Test getting current device info."""
        mock_run = mocker.patch("subprocess.run")
        mock_run.return_value = Mock(
            stdout="Audio\n * 52. USB DAC [Audio/Sink]\n",
            returncode=0
        )
        
        engine = PipewireEngine()
        info = engine.get_device_info()
        
        assert info is not None
        assert "Audio/Sink" in info

    def test_get_device_info_failure(self, mocker):
        """Test device info when wpctl fails."""
        mock_run = mocker.patch("subprocess.run")
        mock_run.side_effect = subprocess.CalledProcessError(1, "wpctl")
        
        engine = PipewireEngine()
        info = engine.get_device_info()
        
        assert info is None

    def test_timeout_configuration(self):
        """Test that timeout is configurable."""
        engine = PipewireEngine()
        assert engine.timeout == 5

    def test_json_parse_error_returns_fallback(self, mocker):
        """Test that invalid JSON returns fallback rates."""
        mock_run = mocker.patch("subprocess.run")
        mock_run.return_value = Mock(stdout="invalid json", returncode=0)
        
        engine = PipewireEngine()
        rates = engine.get_supported_sample_rates()
        
        assert len(rates) > 0
        assert 48000 in rates

    def test_empty_devices_returns_fallback(self, mocker):
        """Test that empty device list returns fallback rates."""
        mock_run = mocker.patch("subprocess.run")
        mock_run.return_value = Mock(stdout="[]", returncode=0)
        
        engine = PipewireEngine()
        rates = engine.get_supported_sample_rates()
        
        assert len(rates) > 0
        assert 44100 in rates
        assert 48000 in rates
