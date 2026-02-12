"""Hardware detection and capability querying for PipeWire devices."""

import json
import subprocess
from typing import List, Set, Optional


class HardwareDetector:
    """Detects audio hardware and queries supported sample rates."""

    @staticmethod
    def get_supported_sample_rates() -> List[int]:
        """
        Query PipeWire for supported sample rates from connected audio devices.
        
        Returns:
            List of supported sample rates in Hz, sorted ascending.
        """
        try:
            result = subprocess.run(
                ["pw-dump"],
                capture_output=True,
                text=True,
                check=True,
                timeout=5
            )
            devices = json.loads(result.stdout)
            rates = HardwareDetector._extract_rates_from_devices(devices)
            
            # Fallback to common rates if none detected
            if not rates:
                return [44100, 48000, 88200, 96000, 176400, 192000]
            
            return sorted(rates)
            
        except (subprocess.CalledProcessError, subprocess.TimeoutExpired, json.JSONDecodeError):
            # Fallback to common rates on error
            return [44100, 48000, 88200, 96000, 176400, 192000]

    @staticmethod
    def _extract_rates_from_devices(devices: List[dict]) -> Set[int]:
        """Extract supported sample rates from pw-dump output."""
        rates = set()
        
        for device in devices:
            if device.get("type") != "PipeWire:Interface:Node":
                continue
            
            info = device.get("info", {})
            props = info.get("props", {})
            
            # Look for audio sink/source devices
            media_class = props.get("media.class", "")
            if "Audio/Sink" not in media_class and "Audio/Source" not in media_class:
                continue
            
            # Extract rates from params
            params = info.get("params", {})
            enum_format = params.get("EnumFormat", [])
            
            for fmt in enum_format:
                if isinstance(fmt, dict):
                    rate = fmt.get("rate")
                    if rate:
                        if isinstance(rate, int):
                            rates.add(rate)
                        elif isinstance(rate, dict):
                            # Handle range: {"min": 44100, "max": 192000}
                            min_rate = rate.get("min")
                            max_rate = rate.get("max")
                            if min_rate and max_rate:
                                # Add common rates within range
                                common = [44100, 48000, 88200, 96000, 176400, 192000]
                                rates.update(r for r in common if min_rate <= r <= max_rate)
        
        return rates

    @staticmethod
    def get_current_device_info() -> Optional[str]:
        """Get information about the current default audio device."""
        try:
            result = subprocess.run(
                ["wpctl", "status"],
                capture_output=True,
                text=True,
                check=True,
                timeout=5
            )
            # Parse default sink from wpctl status
            for line in result.stdout.split("\n"):
                if "* " in line and ("Sink" in line or "Audio/Sink" in line):
                    return line.strip()
            return None
        except (subprocess.CalledProcessError, subprocess.TimeoutExpired):
            return None
