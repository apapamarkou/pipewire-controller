# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2024 Andrianos Papamarkou
"""System tray application."""

from __future__ import annotations

import sys
from pathlib import Path

from PyQt6.QtCore import QTimer
from PyQt6.QtGui import QIcon
from PyQt6.QtWidgets import QApplication, QMenu, QSystemTrayIcon

from .. import __version__
from ..config import load as load_config
from ..config import save as save_config
from ..log import get_logger, setup_logging
from ..shortcuts import ShortcutManager
from .dialogs import AboutDialog, SystemInfoDialog
from .panel import ControlPanel

log = get_logger("tray")

_ICON_PATHS = [
    Path.home() / ".local/share/icons/pipewire-controller.png",
    Path(__file__).parent.parent.parent.parent / "resources/icons/pipewire-controller.py.png",
    Path(__file__).parent.parent / "resources/icons/pipewire-controller.py.png",
]


def _find_icon() -> QIcon:
    for p in _ICON_PATHS:
        if p.exists():
            return QIcon(str(p))
    return QIcon.fromTheme("audio-card", QIcon.fromTheme("multimedia-volume-control"))


class TrayApp(QApplication):
    """Main application — lives in the system tray."""

    def __init__(self, argv: list[str]) -> None:
        super().__init__(argv)
        self.setApplicationName("PipeWire Audio Control Center")
        self.setApplicationVersion(__version__)
        self.setQuitOnLastWindowClosed(False)

        self._config = load_config()
        self._panel: ControlPanel | None = None
        self._about_dialog: AboutDialog | None = None
        self._shortcuts: ShortcutManager | None = None

        self._icon = _find_icon()
        self._tray = QSystemTrayIcon(self._icon, self)
        self._tray.setToolTip(f"PipeWire Audio Control Center {__version__}")
        self._tray.setContextMenu(self._build_tray_menu())
        self._tray.activated.connect(self._on_tray_activated)
        self._tray.show()

        # Build panel after event loop starts so geometry is correct
        QTimer.singleShot(0, self._init_panel)

        self.aboutToQuit.connect(self._on_quit)

    def _build_tray_menu(self) -> QMenu:
        menu = QMenu()
        menu.setStyleSheet(
            "QMenu { background: #1a1a1a; color: #e0e0e0; border: 1px solid #2d2d2d; }"
            "QMenu::item:selected { background: #2e2e2e; }"
        )

        show_action = menu.addAction("Show / Hide Panel")
        show_action.triggered.connect(self._toggle_panel)

        menu.addSeparator()

        status_action = menu.addAction("System Status…")
        status_action.triggered.connect(self._show_system_status)

        menu.addSeparator()

        about_action = menu.addAction(f"About  (v{__version__})")
        about_action.triggered.connect(self._show_about)

        menu.addSeparator()

        quit_action = menu.addAction("Quit")
        quit_action.triggered.connect(self.quit)

        return menu

    def _init_panel(self) -> None:
        self._panel = ControlPanel(self._config)
        self._shortcuts = ShortcutManager(self._panel)
        self._shortcuts.setup_defaults(self._toggle_panel)

        # Show panel on startup
        self._panel.show()
        self._panel.raise_()

    def _toggle_panel(self) -> None:
        if self._panel is None:
            return
        self._panel.toggle_visible()

    def _show_about(self) -> None:
        if self._about_dialog is None:
            self._about_dialog = AboutDialog()
        self._about_dialog.show()
        self._about_dialog.raise_()
        self._about_dialog.activateWindow()

    def _show_system_status(self) -> None:
        dlg = SystemInfoDialog()
        dlg.exec()

    def _on_tray_activated(self, reason: QSystemTrayIcon.ActivationReason) -> None:
        if reason == QSystemTrayIcon.ActivationReason.Trigger:
            self._toggle_panel()

    def _on_quit(self) -> None:
        if self._panel is not None:
            self._panel.save_geometry()
        save_config(self._config)
        log.info("Application quit, config saved")


def run(argv: list[str] | None = None) -> int:
    """Entry point."""
    setup_logging()
    if argv is None:
        argv = sys.argv

    # Handle --toggle CLI flag for external shortcut integration
    if "--toggle" in argv:
        # Send signal to running instance via config-based IPC (future phase)
        # For now, just start normally
        argv = [a for a in argv if a != "--toggle"]

    app = TrayApp(argv)
    return app.exec()
