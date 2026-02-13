"""System tray application UI."""

import sys
from pathlib import Path
from PyQt6.QtWidgets import QApplication, QSystemTrayIcon, QMenu
from PyQt6.QtGui import QIcon, QAction
from PyQt6.QtCore import QTimer

from ..core.pipewire import PipeWireController
from ..core.hardware import HardwareDetector
from ..engine import PipewireEngine
from ..utils.config import Config
from ..utils.process import ProcessManager
from .dialogs import AboutDialog


class TrayApplication(QApplication):
    """Main system tray application."""

    BUFFER_SIZES = [32, 64, 128, 256, 512, 1024, 2048]

    def __init__(self, argv):
        super().__init__(argv)
        
        self.config = Config()
        self.settings = self.config.load()
        
        # Use engine for all PipeWire operations
        self.engine = PipewireEngine()
        
        # Get hardware-supported sample rates
        self.supported_rates = self.engine.get_supported_sample_rates()
        
        # Apply saved settings
        self._apply_settings()
        
        # Setup tray icon
        self.tray_icon = QSystemTrayIcon()
        self._setup_icon()
        self.tray_icon.setContextMenu(self._create_menu())
        self.tray_icon.activated.connect(self._on_tray_activated)
        self.tray_icon.show()
        
        self.about_dialog = None
        
        # Keep event loop alive
        self.timer = QTimer()
        self.timer.timeout.connect(lambda: None)
        self.timer.start(1000)

    def _setup_icon(self):
        """Setup tray icon with fallback."""
        icon_paths = [
            Path.home() / ".local/share/icons/pipewire-controller.png",
            Path(__file__).parent.parent / "resources/icons/pipewire-controller.png"
        ]
        
        for path in icon_paths:
            if path.exists():
                self.tray_icon.setIcon(QIcon(str(path)))
                break
        else:
            self.tray_icon.setIcon(QIcon.fromTheme("audio-card"))
        
        self._update_tooltip()

    def _create_menu(self):
        """Create context menu with hardware-filtered rates."""
        menu = QMenu()
        
        # Sample rate submenu
        rate_menu = QMenu("Sample Rate", menu)
        for rate in self.supported_rates:
            action = QAction(f"{rate} Hz", rate_menu, checkable=True)
            action.setChecked(rate == self.settings["samplerate"])
            action.triggered.connect(lambda checked, r=rate: self._change_sample_rate(r))
            rate_menu.addAction(action)
        menu.addMenu(rate_menu)
        
        # Buffer size submenu
        buffer_menu = QMenu("Buffer Size", menu)
        for size in self.BUFFER_SIZES:
            action = QAction(f"{size}", buffer_menu, checkable=True)
            action.setChecked(size == self.settings["buffer_size"])
            action.triggered.connect(lambda checked, s=size: self._change_buffer_size(s))
            buffer_menu.addAction(action)
        menu.addMenu(buffer_menu)
        
        menu.addSeparator()
        
        # About
        about_action = QAction("About", menu)
        about_action.triggered.connect(self._show_about)
        menu.addAction(about_action)
        
        # Quit
        quit_action = QAction("Quit", menu)
        quit_action.triggered.connect(self.quit)
        menu.addAction(quit_action)
        
        return menu

    def _change_sample_rate(self, rate: int):
        """Change sample rate and update UI."""
        if self.engine.set_sample_rate(rate):
            self.settings["samplerate"] = rate
            self.config.save(self.settings)
            self._update_menu()
            self._update_tooltip()

    def _change_buffer_size(self, size: int):
        """Change buffer size and update UI."""
        if self.engine.set_buffer_size(size):
            self.settings["buffer_size"] = size
            self.config.save(self.settings)
            self._update_menu()
            self._update_tooltip()

    def _update_menu(self):
        """Update menu checkmarks."""
        menu = self.tray_icon.contextMenu()
        for action in menu.actions():
            submenu = action.menu()
            if submenu:
                for sub_action in submenu.actions():
                    if action.text() == "Sample Rate":
                        sub_action.setChecked(
                            sub_action.text() == f"{self.settings['samplerate']} Hz"
                        )
                    elif action.text() == "Buffer Size":
                        sub_action.setChecked(
                            sub_action.text() == str(self.settings["buffer_size"])
                        )

    def _update_tooltip(self):
        """Update tooltip with current settings."""
        tooltip = (
            f"PipeWire Controller\n"
            f"{self.settings['samplerate']} Hz @ {self.settings['buffer_size']} samples"
        )
        self.tray_icon.setToolTip(tooltip)

    def _apply_settings(self):
        """Apply saved settings to PipeWire."""
        self.engine.set_sample_rate(self.settings["samplerate"])
        self.engine.set_buffer_size(self.settings["buffer_size"])

    def _on_tray_activated(self, reason):
        """Handle tray icon activation."""
        if reason == QSystemTrayIcon.ActivationReason.Trigger:
            self._show_about()

    def _show_about(self):
        """Show or toggle about dialog."""
        if self.about_dialog is None:
            self.about_dialog = AboutDialog()
        
        if self.about_dialog.isVisible():
            self.about_dialog.hide()
        else:
            self.about_dialog.show()
            self.about_dialog.raise_()
            self.about_dialog.activateWindow()


def run():
    """Entry point for the application."""
    process_mgr = ProcessManager()
    process_mgr.ensure_single_instance()
    
    app = TrayApplication(sys.argv)
    app.aboutToQuit.connect(process_mgr.cleanup)
    
    sys.exit(app.exec())
