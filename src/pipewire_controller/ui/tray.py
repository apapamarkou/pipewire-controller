# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2024 Andrianos Papamarkou
"""System tray application."""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
from pathlib import Path

from PyQt6.QtCore import QTimer, pyqtSignal
from PyQt6.QtGui import QColor, QIcon, QPainter, QPixmap
from PyQt6.QtNetwork import QLocalServer, QLocalSocket
from PyQt6.QtWidgets import QApplication, QMenu, QSystemTrayIcon

from .. import __version__
from ..config import load as load_config
from ..config import save as save_config
from ..detection import detect_system
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


def _make_status_action(menu: QMenu, color: str, label: str = "System Status…") -> object:
    """Plain QAction with a colored dot pixmap icon."""
    action = menu.addAction(label)
    px = QPixmap(14, 14)
    px.fill(QColor(0, 0, 0, 0))
    p = QPainter(px)
    p.setRenderHint(QPainter.RenderHint.Antialiasing)
    c = QColor(color)
    p.setBrush(c)
    p.setPen(c)
    p.drawEllipse(1, 1, 12, 12)
    p.end()
    action.setIcon(QIcon(px))
    return action

class TrayApp(QApplication):
    """Main application — lives in the system tray."""

    _status_detected = pyqtSignal(object)

    def __init__(self, argv: list[str]) -> None:
        super().__init__(argv)
        self.setApplicationName("PipeWire Audio Control Center")
        self.setApplicationVersion(__version__)
        self.setQuitOnLastWindowClosed(False)

        self._config = load_config()
        self._panel: ControlPanel | None = None
        self._controller = None
        self._about_dialog: AboutDialog | None = None
        self._sysinfo_dialog: SystemInfoDialog | None = None
        self._shortcuts: ShortcutManager | None = None
        self._cached_status = None  # last known SystemStatus, populated in bg thread

        variant = self._config.get("window", {}).get("tray_icon", "dark")
        self._icon = _find_icon(variant)
        self._tray = QSystemTrayIcon(self._icon, self)
        self._tray.setToolTip(f"PipeWire Audio Control Center {__version__}")
        self._menu = QMenu()
        self._menu.aboutToShow.connect(self._rebuild_tray_menu)
        self._tray.setContextMenu(self._menu)
        self._tray.activated.connect(self._on_tray_activated)
        self._tray.show()
        self._server = QLocalServer(self)
        self._server.newConnection.connect(self._on_ipc_connection)
        QLocalServer.removeServer(_SOCKET_NAME)
        self._server.listen(_SOCKET_NAME)

        self._status_detected.connect(self._apply_status)
        QTimer.singleShot(0, self._init_panel)
        QTimer.singleShot(0, self._refresh_status_bg)
        self.aboutToQuit.connect(self._on_quit)

    def _rebuild_tray_menu(self) -> None:
        """Clear and repopulate the persistent tray menu (called on aboutToShow)."""
        self._menu.clear()
        self._menu.setStyleSheet(
            "QMenu { background: #1a1a1a; color: #e0e0e0; border: 1px solid #2d2d2d; }"
            "QMenu::item { padding: 4px 20px 4px 8px; }"
            "QMenu::item:selected { background: #2e2e2e; }"
            "QMenu::icon { padding-left: 4px; }"
        )
        show_action = self._menu.addAction("Show / Hide Panel")
        show_action.triggered.connect(lambda: QTimer.singleShot(0, self._toggle_panel))

        qpw_installed = (
            self._cached_status.qpwgraph.installed
            if self._cached_status is not None
            else bool(shutil.which("qpwgraph"))
        )
        if qpw_installed:
            qpw_action = self._menu.addAction("Open qpwgraph")
            qpw_action.triggered.connect(lambda: QTimer.singleShot(0, self._launch_qpwgraph))

        ee_installed = (
            self._cached_status.easyeffects.installed
            if self._cached_status is not None
            else bool(shutil.which("easyeffects"))
        )
        if ee_installed:
            ee_action = self._menu.addAction("Open EasyEffects")
            ee_action.triggered.connect(lambda: QTimer.singleShot(0, self._launch_easyeffects))

        self._menu.addSeparator()

        status = self._cached_status
        if status is None:
            dot_color = "#9e9e9e"
            label = "System Status… (detecting)"
        elif not (status.pipewire.ok and status.wireplumber.ok and status.pipewire_jack.installed):
            dot_color = "#f44336"
            label = "System Status… (check)"
        elif not (status.qpwgraph.installed and status.easyeffects.installed):
            dot_color = "#ff9800"
            label = "System Status… (add ons)"
        else:
            dot_color = "#4caf50"
            label = "System Status… (all set)"
        status_action = _make_status_action(self._menu, dot_color, label)
        status_action.triggered.connect(lambda: QTimer.singleShot(0, self._show_system_status))

        self._menu.addSeparator()
        about_action = self._menu.addAction(f"About  (v{__version__})")
        about_action.triggered.connect(lambda: QTimer.singleShot(0, self._show_about))
        self._menu.addSeparator()
        quit_action = self._menu.addAction("Quit")
        quit_action.triggered.connect(lambda: QTimer.singleShot(0, self.quit))

    def _build_tray_menu(self) -> QMenu:
        """Kept for compatibility — returns the persistent menu."""
        return self._menu

    def _refresh_status_bg(self) -> None:
        """Run detect_system() in a background thread, then update cached status."""
        import threading
        threading.Thread(target=self._detect_and_apply, daemon=True).start()

    def _detect_and_apply(self) -> None:
        status = detect_system()
        self._status_detected.emit(status)

    def _apply_status(self, status) -> None:
        self._cached_status = status
        self._rebuild_tray_menu()
        if self._panel is not None:
            self._panel._toolbar.refresh_tool_buttons()

    def update_tooltip(
        self,
        rate: int | None = None,
        quantum: int | None = None,
        period_ms: float | None = None,
        preset_name: str | None = None,
    ) -> None:
        """Update the tray tooltip with current system state."""
        lines = [f"PipeWire Audio Control Center v{__version__}"]
        if rate is not None:
            lines.append(f"Samplerate {rate} Hz")
        if quantum is not None:
            lines.append(f"Buffersize {quantum}")
        if period_ms is not None:
            lines.append(f"Period latency: {period_ms:.2f} ms")
        if preset_name:
            lines.append(f"Configuration: {preset_name}")
        self._tray.setToolTip("\n".join(lines))

    def _launch_qpwgraph(self) -> None:
        try:
            subprocess.Popen(["qpwgraph"])
        except FileNotFoundError:
            pass

    def _launch_easyeffects(self) -> None:
        try:
            subprocess.Popen(["easyeffects"])
        except FileNotFoundError:
            pass

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
        # Let the controller push tooltip updates to the tray
        self._controller.set_tooltip_callback(self.update_tooltip)

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
        if self._sysinfo_dialog is not None and self._sysinfo_dialog.isVisible():
            self._sysinfo_dialog.raise_()
            self._sysinfo_dialog.activateWindow()
            return
        self._sysinfo_dialog = SystemInfoDialog()
        self._sysinfo_dialog.finished.connect(self._refresh_status_bg)
        self._sysinfo_dialog.show()
        self._sysinfo_dialog.raise_()
        self._sysinfo_dialog.activateWindow()

    def _on_sysinfo_closed(self) -> None:
        self._sysinfo_dialog = None

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
        if self._sysinfo_dialog is not None:
            self._sysinfo_dialog.close()
            self._sysinfo_dialog = None
        if self._about_dialog is not None:
            self._about_dialog.close()
            self._about_dialog = None
        if self._panel is not None:
            self._panel.save_geometry()
            self._panel.force_close()
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
