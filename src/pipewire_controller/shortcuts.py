# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2024 Andrianos Papamarkou
"""
Keyboard shortcut abstraction.

Global shortcuts on Linux require platform-specific mechanisms (e.g. keybind
daemons, X11 XGrabKey, or Wayland compositor protocols). Rather than depend on
a fragile global hotkey library, we provide:

1. A QShortcut bound to the panel window (works when the panel has focus).
2. A documented interface so the user can configure their DE/WM to call
   `pipewire-controller --toggle` to show/hide the panel from any context.

This keeps the application self-contained and avoids X11/Wayland-specific
dependencies while still providing a clean shortcut abstraction.
"""

from __future__ import annotations

from PyQt6.QtGui import QKeySequence, QShortcut
from PyQt6.QtWidgets import QWidget

from .log import get_logger

log = get_logger("shortcuts")


class ShortcutManager:
    """Manages application keyboard shortcuts."""

    def __init__(self, panel: QWidget) -> None:
        self._panel = panel
        self._shortcuts: list[QShortcut] = []

    def register(self, key_sequence: str, callback) -> QShortcut:
        """Register a shortcut on the panel widget."""
        sc = QShortcut(QKeySequence(key_sequence), self._panel)
        sc.activated.connect(callback)
        self._shortcuts.append(sc)
        log.debug("Registered shortcut: %s", key_sequence)
        return sc

    def setup_defaults(self, toggle_fn) -> None:
        """Register default application shortcuts."""
        self.register("Ctrl+Shift+P", toggle_fn)
        self.register("Meta+Shift+P", toggle_fn)
        self.register("Escape", self._panel.hide)
