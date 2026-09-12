# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2024 Andrianos Papamarkou
"""System dependency detection — PipeWire, WirePlumber, pipewire-jack."""

from __future__ import annotations

import shutil
import subprocess
from dataclasses import dataclass

from .log import get_logger

log = get_logger("detection")

_TIMEOUT = 3


@dataclass
class ComponentStatus:
    name: str
    installed: bool
    running: bool | None  # None = not a service / not checkable
    version: str | None = None
    note: str | None = None

    @property
    def ok(self) -> bool:
        if not self.installed:
            return False
        if self.running is not None:
            return self.running
        return True

    @property
    def symbol(self) -> str:
        if self.ok:
            return "✓"
        if self.installed and self.running is False:
            return "⚠"
        return "✕"


@dataclass
class SystemStatus:
    pipewire: ComponentStatus
    wireplumber: ComponentStatus
    pipewire_jack: ComponentStatus

    @property
    def pipewire_available(self) -> bool:
        return self.pipewire.installed and self.pipewire.running is True

    @property
    def fully_operational(self) -> bool:
        return self.pipewire_available and self.wireplumber.ok


def _cmd_exists(cmd: str) -> bool:
    return shutil.which(cmd) is not None


def _service_active(unit: str) -> bool:
    try:
        r = subprocess.run(
            ["systemctl", "--user", "is-active", unit],
            capture_output=True,
            text=True,
            timeout=_TIMEOUT,
        )
        return r.stdout.strip() == "active"
    except Exception:
        return False


def _pipewire_version() -> str | None:
    try:
        r = subprocess.run(
            ["pipewire", "--version"],
            capture_output=True,
            text=True,
            timeout=_TIMEOUT,
        )
        for line in r.stdout.splitlines():
            if "libpipewire" in line.lower() or "pipewire" in line.lower():
                return line.strip()
        return r.stdout.strip().splitlines()[0] if r.stdout.strip() else None
    except Exception:
        return None


def _jack_installed() -> bool:
    """Check if pipewire-jack is installed by looking for the JACK library shim."""
    import ctypes

    try:
        ctypes.cdll.LoadLibrary("libjack.so.0")
        return True
    except OSError:
        pass
    # Fallback: check for pw-jack wrapper
    return _cmd_exists("pw-jack")


def detect_system() -> SystemStatus:
    """Detect PipeWire ecosystem components. Never raises."""
    try:
        pw_installed = _cmd_exists("pipewire") or _cmd_exists("pw-metadata")
        pw_running = _service_active("pipewire") if pw_installed else False
        pw_version = _pipewire_version() if pw_installed else None

        wp_installed = _cmd_exists("wireplumber") or _cmd_exists("wpctl")
        wp_running = _service_active("wireplumber") if wp_installed else False

        jack_installed = _jack_installed()

        return SystemStatus(
            pipewire=ComponentStatus(
                name="PipeWire",
                installed=pw_installed,
                running=pw_running,
                version=pw_version,
            ),
            wireplumber=ComponentStatus(
                name="WirePlumber",
                installed=wp_installed,
                running=wp_running,
            ),
            pipewire_jack=ComponentStatus(
                name="PipeWire JACK",
                installed=jack_installed,
                running=None,
                note="JACK compatibility layer" if jack_installed else "Not installed",
            ),
        )
    except Exception as exc:
        log.error("System detection failed: %s", exc)
        return SystemStatus(
            pipewire=ComponentStatus("PipeWire", False, False),
            wireplumber=ComponentStatus("WirePlumber", False, False),
            pipewire_jack=ComponentStatus("PipeWire JACK", False, None),
        )
