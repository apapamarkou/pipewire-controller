# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2024 Andrianos Papamarkou
"""System tray application."""

from __future__ import annotations

import os
import sys
from pathlib import Path

from PyQt6.QtCore import QTimer
from PyQt6.QtGui import QIcon
from PyQt6.QtNetwork import QLocalServer, QLocalSocket
from PyQt6.QtWidgets import QApplication, QMenu, QSystemTrayIcon

from .. import __version__
from ..config import load as load_config
from ..config import save as save_config
from ..log import get_logger, setup_logging
from ..shortcuts import ShortcutManager
from .dialogs import AboutDialog, SystemInfoDialog
from .panel import ControlPanel

log = get_logger("tray")


def _find_icon(variant: str = "dark") -> QIcon:
    """Return tray icon for the requested variant ("dark" or "light").

    Looks in standard XDG icon directories. Packages (deb/rpm/tarball) install:
      - dark/light icons to hicolor/128x128/apps/
      - main icon      to hicolor/512x512/apps/
    AppImage installs them under $APPDIR/usr/share/icons/hicolor/.
    """
    bases: list[Path] = [
        Path("/usr/share/icons/hicolor"),
        Path.home() / ".local/share/icons/hicolor",
    ]

    appdir = os.environ.get("APPDIR")
    if appdir:
        bases.insert(0, Path(appdir) / "usr/share/icons/hicolor")

    # Try requested variant first, then the other variant, then main icon
    other = "light" if variant == "dark" else "dark"
    candidates = [
        ("128x128", f"pipewire-controller.{variant}.png"),
        ("128x128", f"pipewire-controller.{other}.png"),
        ("512x512", "pipewire-controller.png"),
    ]

    for base in bases:
        for size, name in candidates:
            p = base / size / "apps" / name
            if p.exists():
                return QIcon(str(p))

    return QIcon.fromTheme("audio-card", QIcon.fromTheme("multimedia-volume-control"))


_SOCKET_NAME = "pipewire-controller"
_MSG_TOGGLE = b"toggle"


class TrayApp(QApplication):
    """Main application — lives in the system tray."""

    def __init__(self, argv: list[str]) -> None:
        super().__init__(argv)
        self.setApplicationName("PipeWire Audio Control Center")
        self.setApplicationVersion(__version__)
        self.setQuitOnLastWindowClosed(False)

        self._config = load_config()
        self._panel: ControlPanel | None = None
        self._controller = None
        self._about_dialog: AboutDialog | None = None
        self._shortcuts: ShortcutManager | None = None

        variant = self._config.get("window", {}).get("tray_icon", "dark")
        self._icon = _find_icon(variant)
        self._tray = QSystemTrayIcon(self._icon, self)
        self._tray.setToolTip(f"PipeWire Audio Control Center {__version__}")
        self._tray.setContextMenu(self._build_tray_menu())
        self._tray.activated.connect(self._on_tray_activated)
        self._tray.show()

        self._server = QLocalServer(self)
        self._server.newConnection.connect(self._on_ipc_connection)
        QLocalServer.removeServer(_SOCKET_NAME)
        self._server.listen(_SOCKET_NAME)

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

    def _on_ipc_connection(self) -> None:
        conn = self._server.nextPendingConnection()
        conn.waitForReadyRead(200)
        if conn.readAll() == _MSG_TOGGLE:
            self._toggle_panel()
        conn.deleteLater()

    def _init_panel(self) -> None:
        self._panel = ControlPanel(self._config)
        self._panel.tray_icon_changed.connect(self._on_tray_icon_changed)
        self._shortcuts = ShortcutManager(self._panel)
        self._shortcuts.setup_defaults(self._toggle_panel)

        # Wire the application controller (sections + PipeWire)
        from ..controller import AppController

        self._controller = AppController(self._panel, self._config)

        # Start with panel hidden; subsequent launches toggle via IPC
        QTimer.singleShot(0, self._panel.reposition)

    def _on_tray_icon_changed(self, variant: str) -> None:
        """Swap the tray icon live when the user toggles dark/light."""
        icon = _find_icon(variant)
        self._tray.setIcon(icon)

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
        if reason in (
            QSystemTrayIcon.ActivationReason.Trigger,
            QSystemTrayIcon.ActivationReason.MiddleClick,
        ):
            self._toggle_panel()

    def _on_quit(self) -> None:
        self._server.close()
        QLocalServer.removeServer(_SOCKET_NAME)
        if self._controller is not None:
            self._controller.shutdown()
        if self._panel is not None:
            self._panel.save_geometry()
        save_config(self._config)
        log.info("Application quit, config saved")


def _send_toggle() -> bool:
    """Send toggle to a running instance. Returns True if delivered."""
    sock = QLocalSocket()
    sock.connectToServer(_SOCKET_NAME)
    if not sock.waitForConnected(500):
        return False
    sock.write(_MSG_TOGGLE)
    sock.waitForBytesWritten(500)
    sock.disconnectFromServer()
    return True


def run(argv: list[str] | None = None) -> int:
    """Entry point."""
    setup_logging()
    if argv is None:
        argv = sys.argv
    # Check for existing instance before creating QApplication
    # QLocalSocket needs a QCoreApplication; use a temporary one
    from PyQt6.QtCore import QCoreApplication

    tmp = QCoreApplication(argv)
    already_running = _send_toggle()
    del tmp
    if already_running:
        return 0
    tray = TrayApp(argv)
    return tray.exec()
