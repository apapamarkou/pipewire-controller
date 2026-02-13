"""PipeWire engine - Pure logic with no GUI dependencies."""

import json
import subprocess
from typing import List, Optional, Dict, Any


class PipewireEngine:
    """Handles all PipeWire interactions without GUI dependencies."""

    def __init__(self):
        """Initialize the engine."""
        self.timeout = 5

    def set_sample_rate(self, rate: int) -> bool:
        """Set PipeWire sample rate."""
        try:
            subprocess.run(
                ["pw-metadata", "-n", "settings", "0", "clock.force-rate", str(rate)],
                check=True,
                capture_output=True,
                timeout=self.timeout
            )
            return True
        except (subprocess.CalledProcessError, subprocess.TimeoutExpired):
            return False

    def set_buffer_size(self, size: int) -> bool:
        """Set PipeWire buffer size (quantum)."""
        try:
            subprocess.run(
                ["pw-metadata", "-n", "settings", "0", "clock.force-quantum", str(size)],
                check=True,
                capture_output=True,
                timeout=self.timeout
            )
            return True
        except (subprocess.CalledProcessError, subprocess.TimeoutExpired):
            return False

    def get_supported_sample_rates(self) -> List[int]:
        """Query PipeWire for supported sample rates from connected devices."""
        try:
            result = subprocess.run(
                ["pw-dump"],
                capture_output=True,
                text=True,
                check=True,
                timeout=self.timeout
            )
            devices = json.loads(result.stdout)
            rates = self._extract_rates_from_devices(devices)
            
            if not rates:
                return self._get_fallback_rates()
            
            return sorted(rates)
            
        except (subprocess.CalledProcessError, subprocess.TimeoutExpired, json.JSONDecodeError):
            return self._get_fallback_rates()

    def _extract_rates_from_devices(self, devices: List[dict]) -> set:
        """Extract supported sample rates from pw-dump output."""
        rates = set()
        
        for device in devices:
            if device.get("type") != "PipeWire:Interface:Node":
                continue
            
            info = device.get("info", {})
            props = info.get("props", {})
            
            media_class = props.get("media.class", "")
            if "Audio/Sink" not in media_class and "Audio/Source" not in media_class:
                continue
            
            params = info.get("params", {})
            enum_format = params.get("EnumFormat", [])
            
            for fmt in enum_format:
                if isinstance(fmt, dict):
                    rate = fmt.get("rate")
                    if rate:
                        if isinstance(rate, int):
                            rates.add(rate)
                        elif isinstance(rate, dict):
                            min_rate = rate.get("min")
                            max_rate = rate.get("max")
                            if min_rate and max_rate:
                                common = [44100, 48000, 88200, 96000, 176400, 192000]
                                rates.update(r for r in common if min_rate <= r <= max_rate)
        
        return rates

    def _get_fallback_rates(self) -> List[int]:
        """Return common fallback rates."""
        return [44100, 48000, 88200, 96000, 176400, 192000]

    def get_current_rate(self) -> Optional[int]:
        """Get current sample rate from PipeWire."""
        try:
            result = subprocess.run(
                ["pw-metadata", "-n", "settings"],
                capture_output=True,
                text=True,
                check=True,
                timeout=self.timeout
            )
            for line in result.stdout.split("\n"):
                if "clock.force-rate" in line:
                    parts = line.split("'")
                    if len(parts) >= 4:
                        return int(parts[3])
            return None
        except (subprocess.CalledProcessError, subprocess.TimeoutExpired, ValueError):
            return None

    def get_current_quantum(self) -> Optional[int]:
        """Get current buffer size from PipeWire."""
        try:
            result = subprocess.run(
                ["pw-metadata", "-n", "settings"],
                capture_output=True,
                text=True,
                check=True,
                timeout=self.timeout
            )
            for line in result.stdout.split("\n"):
                if "clock.force-quantum" in line:
                    parts = line.split("'")
                    if len(parts) >= 4:
                        return int(parts[3])
            return None
        except (subprocess.CalledProcessError, subprocess.TimeoutExpired, ValueError):
            return None

    def get_device_info(self) -> Optional[str]:
        """Get information about the current default audio device."""
        try:
            result = subprocess.run(
                ["wpctl", "status"],
                capture_output=True,
                text=True,
                check=True,
                timeout=self.timeout
            )
            for line in result.stdout.split("\n"):
                if "* " in line and ("Sink" in line or "Audio/Sink" in line):
                    return line.strip()
            return None
        except (subprocess.CalledProcessError, subprocess.TimeoutExpired):
            return None
