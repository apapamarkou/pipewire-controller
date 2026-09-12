# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2024 Andrianos Papamarkou
"""Configuration persistence — named presets, UI state, device friendly names."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .log import get_logger

log = get_logger("config")

CONFIG_DIR = Path.home() / ".config" / "pipewire-controller"
CONFIG_FILE = CONFIG_DIR / "config.json"

_SCHEMA_VERSION = 1

_DEFAULT_CONFIG: dict[str, Any] = {
    "schema_version": _SCHEMA_VERSION,
    "active_preset": "Default",
    "presets": {
        "Default": {
            "name": "Default",
            "description": "",
            "samplerate": 48000,
            "quantum": 1024,
            "force_rate": False,
            "force_quantum": False,
            "panel_width": 340,
            "panel_docked": True,
            "always_on_top": False,
            "pinned": False,
            "auto_load": False,
            "accordion_state": {},
            "friendly_names": {},
            "channel_names": {},
            "meter_mode": "Peak",
            "master_mode": "Stereo",
            "master_channel_map": {},
        }
    },
    "window": {
        "width": 340,
        "docked": True,
        "always_on_top": False,
        "pinned": False,
    },
}


def _ensure_dir() -> None:
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)


def load() -> dict[str, Any]:
    """Load config from disk. Returns defaults on any error."""
    _ensure_dir()
    if not CONFIG_FILE.exists():
        return _deep_copy(_DEFAULT_CONFIG)
    try:
        with CONFIG_FILE.open() as f:
            data = json.load(f)
        return _migrate(data)
    except Exception as exc:
        log.warning("Failed to load config (%s), using defaults", exc)
        return _deep_copy(_DEFAULT_CONFIG)


def save(config: dict[str, Any]) -> bool:
    """Persist config to disk. Returns True on success."""
    _ensure_dir()
    try:
        with CONFIG_FILE.open("w") as f:
            json.dump(config, f, indent=2)
        return True
    except Exception as exc:
        log.error("Failed to save config: %s", exc)
        return False


def _migrate(data: dict[str, Any]) -> dict[str, Any]:
    """Migrate older config formats forward."""
    version = data.get("schema_version", 0)
    if version < 1:
        # v0 → v1: wrap old flat settings into a Default preset
        preset = _deep_copy(_DEFAULT_CONFIG["presets"]["Default"])
        preset["samplerate"] = data.get("samplerate", 48000)
        preset["quantum"] = data.get("buffer_size", 1024)
        result = _deep_copy(_DEFAULT_CONFIG)
        result["presets"]["Default"] = preset
        log.info("Migrated config from v%d to v%d", version, _SCHEMA_VERSION)
        return result
    return data


def _deep_copy(obj: Any) -> Any:
    return json.loads(json.dumps(obj))


def get_preset(config: dict[str, Any], name: str) -> dict[str, Any] | None:
    return config.get("presets", {}).get(name)


def active_preset(config: dict[str, Any]) -> dict[str, Any]:
    name = config.get("active_preset", "Default")
    preset = get_preset(config, name)
    if preset is None:
        preset = _deep_copy(_DEFAULT_CONFIG["presets"]["Default"])
    return preset


def save_preset(config: dict[str, Any], preset: dict[str, Any]) -> None:
    name = preset.get("name", "Default")
    config.setdefault("presets", {})[name] = preset


def delete_preset(config: dict[str, Any], name: str) -> bool:
    if name == config.get("active_preset"):
        return False
    return config.get("presets", {}).pop(name, None) is not None


def rename_preset(config: dict[str, Any], old: str, new: str) -> bool:
    presets = config.get("presets", {})
    if old not in presets or new in presets:
        return False
    presets[new] = presets.pop(old)
    presets[new]["name"] = new
    if config.get("active_preset") == old:
        config["active_preset"] = new
    return True
