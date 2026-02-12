"""Configuration and settings management."""

import json
import os
from pathlib import Path
from typing import Dict, Any


class Config:
    """Manages application configuration."""

    DEFAULT_SETTINGS = {
        "samplerate": 48000,
        "buffer_size": 512
    }

    def __init__(self):
        self.config_dir = Path.home() / ".config" / "pipewire-controller"
        self.config_file = self.config_dir / "settings.json"
        self.config_dir.mkdir(parents=True, exist_ok=True)

    def load(self) -> Dict[str, Any]:
        """Load settings from config file."""
        if self.config_file.exists():
            try:
                with open(self.config_file, "r") as f:
                    return json.load(f)
            except (json.JSONDecodeError, IOError):
                pass
        return self.DEFAULT_SETTINGS.copy()

    def save(self, settings: Dict[str, Any]) -> bool:
        """Save settings to config file."""
        try:
            with open(self.config_file, "w") as f:
                json.dump(settings, f, indent=2)
            return True
        except IOError:
            return False
