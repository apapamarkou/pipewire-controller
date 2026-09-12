# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2024 Andrianos Papamarkou
"""
Friendly name management for devices and channels.

IMPORTANT LIMITATIONS (documented per spec):
- Renaming here stores a display override in the application config.
- PipeWire-aware applications may see the friendly name if we set
  node.nick or node.description via pw-metadata.
- ALSA applications that access hardware directly will still see the
  original hardware/channel names.
- Renaming a display description does not guarantee every application
  will display the new name.
- node.name (the stable technical identifier) is NEVER modified.

PipeWire property used for user-visible renaming: node.nick
This is the recommended property for user-assigned names and is
displayed by most PipeWire-aware applications.
"""

from __future__ import annotations

import subprocess

from .log import get_logger

log = get_logger("friendly_names")

_TIMEOUT = 5


def set_node_nick(node_id: int, nick: str) -> bool:
    """
    Set node.nick on a PipeWire node via pw-metadata.

    node.nick is the user-visible display name used by PipeWire-aware
    applications. It does not modify node.name (the stable identifier).

    Returns True on success.
    """
    try:
        subprocess.run(
            ["pw-metadata", str(node_id), "node.nick", nick],
            capture_output=True,
            text=True,
            timeout=_TIMEOUT,
            check=True,
        )
        log.info("Set node.nick for node %d: %r", node_id, nick)
        return True
    except Exception as exc:
        log.warning("Failed to set node.nick for node %d: %s", node_id, exc)
        return False


def get_friendly_names(config: dict) -> dict[str, str]:
    """
    Return the friendly name map from config.
    Keys are node.name (stable), values are user-assigned display names.
    """
    preset = config.get("presets", {}).get(config.get("active_preset", "Default"), {})
    return dict(preset.get("friendly_names", {}))


def set_friendly_name(config: dict, node_name: str, display_name: str) -> None:
    """
    Store a friendly name override in the active preset.
    Does not modify node.name.
    """
    preset_name = config.get("active_preset", "Default")
    preset = config.get("presets", {}).get(preset_name, {})
    preset.setdefault("friendly_names", {})[node_name] = display_name


def get_channel_names(config: dict) -> dict[str, str]:
    """
    Return the channel name map from config.
    Keys are "{node_name}:{channel_index}", values are user-assigned names.
    """
    preset = config.get("presets", {}).get(config.get("active_preset", "Default"), {})
    return dict(preset.get("channel_names", {}))


def set_channel_name(config: dict, node_name: str, channel_index: int, name: str) -> None:
    """Store a channel name override in the active preset."""
    preset_name = config.get("active_preset", "Default")
    preset = config.get("presets", {}).get(preset_name, {})
    key = f"{node_name}:{channel_index}"
    preset.setdefault("channel_names", {})[key] = name
