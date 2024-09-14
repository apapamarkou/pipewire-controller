#!/usr/bin/env python3

import os
import sys
import json
import subprocess

use_qt6 = '-qt6' in sys.argv

if use_qt6:
    from PyQt6.QtWidgets import QApplication, QSystemTrayIcon, QMenu,  QDialog, QLabel, QVBoxLayout
    from PyQt6.QtGui import QIcon, QAction
    from PyQt6.QtCore import Qt
else:
    from PyQt5.QtWidgets import QApplication, QSystemTrayIcon, QMenu, QAction, QDialog, QLabel, QVBoxLayout
    from PyQt5.QtGui import QIcon
    from PyQt5.QtCore import Qt

try:
    config_folder = os.path.expanduser("~/.config/pipewire-controller")
    os.makedirs(config_folder, exist_ok=True)
except Exception as e:
    print(f"An error occurred while creating the folder: {e}")

# Configuration file path
CONFIG_PATH = os.path.expanduser("~/.config/pipewire-controller/pipewire-controller.settings")
LOCK_FILE_PATH = os.path.expanduser("~/.config/pipewire-controller/pipewire-controller.lock")

# Default settings
DEFAULT_SETTINGS = {
    "samplerate": 44100,
    "buffer_size": 512
}

def load_settings():
    if os.path.exists(CONFIG_PATH):
        with open(CONFIG_PATH, "r") as f:
            return json.load(f)
    return DEFAULT_SETTINGS

def save_settings(settings):
    os.makedirs(os.path.dirname(CONFIG_PATH), exist_ok=True)
    with open(CONFIG_PATH, "w") as f:
        json.dump(settings, f)

def check_single_instance():
    if os.path.exists(LOCK_FILE_PATH):
        print("Another instance is already running.")
        sys.exit(1)
    with open(LOCK_FILE_PATH, "w") as f:
        f.write(str(os.getpid()))

def release_lock():
    if os.path.exists(LOCK_FILE_PATH):
        os.remove(LOCK_FILE_PATH)

class AboutDialog(QDialog):
    def __init__(self):
        super().__init__()

        self.setWindowTitle("About")
        self.setFixedSize(400, 400)  # Set the size of the dialog

        # Create a layout
        layout = QVBoxLayout()

        # Create a label with information
        title_label = QLabel("<h1 style='text-align: center;'>PipeWire Controller</h1>"
            "<h2 style='text-align: center;'>Version 1.0</h2>"
            "<p>A system tray icon to control pipewire</p>"
            "<p>Author <b>Andrianos Papamarkou</b></p>"
            "<p><a href='https://github.com/apapamarkou/pipewire-controller'>Visit on GitHub</a></p>"
            )

        title_label.setAlignment(Qt.AlignmentFlag.AlignCenter) if use_qt6 else title_label.setAlignment(Qt.AlignCenter)
        title_label.setOpenExternalLinks(True)

        # Add the labels to the layout
        layout.addWidget(title_label)

        # Set the layout for the dialog
        self.setLayout(layout)

    def closeEvent(self, event):
        event.ignore()
        self.hide()

class TrayIconApp(QApplication):
    def __init__(self, argv):
        super().__init__(argv)

        self.settings = load_settings()

        # Apply the settings on startup
        self.apply_settings()

        # Create tray icon
        self.tray_icon = QSystemTrayIcon()

        icon_path = os.path.expanduser('~/.local/share/icons/pipewire-controller.sh.png')
        self.tray_icon.setIcon(QIcon(icon_path))  # Use a generic sound icon

        self.tray_icon.setIcon(QIcon.fromTheme('preferences-desktop-sound'))  # Use a generic sound icon
        self.update_tooltip()
        self.tray_icon.setContextMenu(self.create_menu())
        self.tray_icon.show()

        self.about_dialog = None  # Initialize the about dialog attribute

    def create_menu(self):
        menu = QMenu()

        # Samplerate submenu
        samplerate_menu = QMenu("Samplerate", menu)
        for rate in [44100, 48000, 88200, 96000]:
            action = QAction(f"{rate}", samplerate_menu, checkable=True)
            action.setChecked(rate == self.settings["samplerate"])
            action.triggered.connect(lambda _, r=rate: self.change_samplerate(r))
            samplerate_menu.addAction(action)
        menu.addMenu(samplerate_menu)

        # Buffer size submenu
        buffer_menu = QMenu("Buffer Size", menu)
        for size in [32, 64, 128, 256, 512, 1024, 2048]:
            action = QAction(f"{size}", buffer_menu, checkable=True)
            action.setChecked(size == self.settings["buffer_size"])
            action.triggered.connect(lambda _, s=size: self.change_buffer_size(s))
            buffer_menu.addAction(action)
        menu.addMenu(buffer_menu)

        # About
        about_action = QAction("About", menu)
        about_action.triggered.connect(self.show_about_dialog)
        menu.addAction(about_action)

        # Quit
        quit_action = QAction("Quit", menu)
        quit_action.triggered.connect(self.exit_application)
        menu.addAction(quit_action)

        return menu

    def change_samplerate(self, rate):
        try:
            subprocess.run(["pw-metadata", "-n", "settings", "0", "clock.force-rate", str(rate)], check=True)
            self.settings["samplerate"] = rate
            save_settings(self.settings)
            self.update_menu()
            self.update_tooltip()
        except subprocess.CalledProcessError as e:
            print(f"Failed to change samplerate: {e}")

    def change_buffer_size(self, size):
        try:
            subprocess.run(["pw-metadata", "-n", "settings", "0", "clock.force-quantum", str(size)], check=True)
            self.settings["buffer_size"] = size
            save_settings(self.settings)
            self.update_menu()
            self.update_tooltip()
        except subprocess.CalledProcessError as e:
            print(f"Failed to change buffer size: {e}")

    def update_menu(self):
        # Update menu items to reflect current settings
        menu = self.tray_icon.contextMenu()
        for action in menu.actions():
            if isinstance(action.menu(), QMenu):
                for sub_action in action.menu().actions():
                    sub_action.setChecked(False)  # Uncheck all actions first
                    if action.text() == "Samplerate":
                        if sub_action.text() == str(self.settings["samplerate"]):
                            sub_action.setChecked(True)
                    elif action.text() == "Buffer Size":
                        if sub_action.text() == str(self.settings["buffer_size"]):
                            sub_action.setChecked(True)

    def update_tooltip(self):
        # Update the tooltip to show the current settings
        tooltip_text = f"PipeWire Controller: {self.settings['samplerate']}Hz @ {self.settings['buffer_size']}"
        self.tray_icon.setToolTip(tooltip_text)

    def apply_settings(self):
        # Apply the settings by executing the relevant commands
        try:
            subprocess.run(["pw-metadata", "-n", "settings", "0", "clock.force-rate", str(self.settings["samplerate"])], check=True)
            subprocess.run(["pw-metadata", "-n", "settings", "0", "clock.force-quantum", str(self.settings["buffer_size"])], check=True)
        except subprocess.CalledProcessError as e:
            print(f"Failed to apply settings on startup: {e}")

    def show_about_dialog(self):
        if self.about_dialog is None:
            self.about_dialog = AboutDialog()
            self.about_dialog.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose) if use_qt6 else self.about_dialog.setAttribute(Qt.WA_DeleteOnClose)
        self.about_dialog.show()
        self.about_dialog.raise_()
        self.about_dialog.activateWindow()

    def exit_application(self):
        release_lock()
        QApplication.quit()  # Properly exit the application

if __name__ == "__main__":
    check_single_instance()
    app = TrayIconApp(sys.argv)
    sys.exit(app.exec())