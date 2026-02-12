"""PipeWire interface for controlling sample rate and buffer size."""

import subprocess
from typing import Optional


class PipeWireController:
    """Interface to control PipeWire audio settings."""

    @staticmethod
    def set_sample_rate(rate: int) -> bool:
        """
        Set PipeWire sample rate.
        
        Args:
            rate: Sample rate in Hz
            
        Returns:
            True if successful, False otherwise
        """
        try:
            subprocess.run(
                ["pw-metadata", "-n", "settings", "0", "clock.force-rate", str(rate)],
                check=True,
                capture_output=True,
                timeout=5
            )
            return True
        except (subprocess.CalledProcessError, subprocess.TimeoutExpired):
            return False

    @staticmethod
    def set_buffer_size(size: int) -> bool:
        """
        Set PipeWire buffer size (quantum).
        
        Args:
            size: Buffer size in samples
            
        Returns:
            True if successful, False otherwise
        """
        try:
            subprocess.run(
                ["pw-metadata", "-n", "settings", "0", "clock.force-quantum", str(size)],
                check=True,
                capture_output=True,
                timeout=5
            )
            return True
        except (subprocess.CalledProcessError, subprocess.TimeoutExpired):
            return False

    @staticmethod
    def get_current_rate() -> Optional[int]:
        """Get current sample rate from PipeWire."""
        try:
            result = subprocess.run(
                ["pw-metadata", "-n", "settings"],
                capture_output=True,
                text=True,
                check=True,
                timeout=5
            )
            for line in result.stdout.split("\n"):
                if "clock.force-rate" in line:
                    parts = line.split("'")
                    if len(parts) >= 4:
                        return int(parts[3])
            return None
        except (subprocess.CalledProcessError, subprocess.TimeoutExpired, ValueError):
            return None

    @staticmethod
    def get_current_quantum() -> Optional[int]:
        """Get current buffer size from PipeWire."""
        try:
            result = subprocess.run(
                ["pw-metadata", "-n", "settings"],
                capture_output=True,
                text=True,
                check=True,
                timeout=5
            )
            for line in result.stdout.split("\n"):
                if "clock.force-quantum" in line:
                    parts = line.split("'")
                    if len(parts) >= 4:
                        return int(parts[3])
            return None
        except (subprocess.CalledProcessError, subprocess.TimeoutExpired, ValueError):
            return None
