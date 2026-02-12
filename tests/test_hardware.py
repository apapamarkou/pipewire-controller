"""Tests for hardware detection."""

import pytest
import subprocess
from unittest.mock import Mock
from pipewire_controller.core.hardware import HardwareDetector


class TestHardwareDetector:
    """Test hardware detection functionality."""

    def test_get_supported_rates_success(self, mock_subprocess_run, sample_pw_dump_output):
        """Test successful rate detection."""
        mock_subprocess_run.return_value = Mock(
            stdout=sample_pw_dump_output,
            returncode=0
        )
        
        rates = HardwareDetector.get_supported_sample_rates()
        
        assert isinstance(rates, list)
        assert 48000 in rates
        assert 96000 in rates
        assert rates == sorted(rates)

    def test_get_supported_rates_fallback(self, mock_subprocess_run):
        """Test fallback to default rates on error."""
        mock_subprocess_run.side_effect = subprocess.CalledProcessError(1, "pw-dump")
        
        rates = HardwareDetector.get_supported_sample_rates()
        
        assert isinstance(rates, list)
        assert len(rates) > 0
        assert 44100 in rates
        assert 48000 in rates

    def test_get_supported_rates_timeout(self, mock_subprocess_run):
        """Test timeout handling."""
        mock_subprocess_run.side_effect = subprocess.TimeoutExpired("pw-dump", 5)
        
        rates = HardwareDetector.get_supported_sample_rates()
        
        assert isinstance(rates, list)
        assert len(rates) > 0

    def test_extract_rates_from_devices(self):
        """Test rate extraction from device data."""
        devices = [
            {
                "type": "PipeWire:Interface:Node",
                "info": {
                    "props": {"media.class": "Audio/Sink"},
                    "params": {
                        "EnumFormat": [
                            {"rate": 48000},
                            {"rate": 96000}
                        ]
                    }
                }
            }
        ]
        
        rates = HardwareDetector._extract_rates_from_devices(devices)
        
        assert 48000 in rates
        assert 96000 in rates

    def test_extract_rates_with_range(self):
        """Test rate extraction with min/max range."""
        devices = [
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
        ]
        
        rates = HardwareDetector._extract_rates_from_devices(devices)
        
        assert 44100 in rates
        assert 48000 in rates
        assert 96000 in rates
        assert 192000 not in rates

    def test_get_current_device_info(self, mock_subprocess_run):
        """Test getting current device info."""
        mock_subprocess_run.return_value = Mock(
            stdout="Audio\n * 52. USB Audio DAC [Audio/Sink]\n",
            returncode=0
        )
        
        info = HardwareDetector.get_current_device_info()
        
        assert info is not None
        assert "Audio/Sink" in info
