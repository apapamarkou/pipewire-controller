#!/usr/bin/env python3

#  ____  _               _          
# |  _ \(_)_ ____      _(_)_ __ ___ 
# | |_) | | '_ \ \ /\ / / | '__/ _ \
# |  __/| | |_) \ V  V /| | | |  __/
# |_|   |_| .__/ \_/\_/ |_|_|  \___|
#        |_|                       
#   ____            _             _ _           
#  / ___|___  _ __ | |_ _ __ ___ | | | ___ _ __ 
# | |   / _ \| '_ \| __| '__/ _ \| | |/ _ \ '__|
# | |__| (_) | | | | |_| | | (_) | | |  __/ |   
#  \____\___/|_| |_|\__|_|  \___/|_|_|\___|_|   
#
#
# A simple tray icon to control your audio
#
# Created by Andrianos Papamarkou
#

import os
import sys
import json
import subprocess
from PyQt5.QtWidgets import QApplication, QSystemTrayIcon, QMenu, QAction, QDialog, QLabel, QVBoxLayout
from PyQt5.QtGui import QIcon
from PyQt5.QtCore import Qt

# Configuration file path
CONFIG_PATH = os.path.expanduser("~/.config/pipewire_controller/pipewire_controller.settings")

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
            "<p>A system tray icon to controll pipewire</p>"
            "<p>Author <b>Andrianos Papamarkou</b></p>"
            "<p></p>"
            )

        title_label.setAlignment(Qt.AlignCenter)

        # Add the labels to the layout
        layout.addWidget(title_label)


        # Set the layout for the dialog
        self.setLayout(layout)

class TrayIconApp(QApplication):
    def __init__(self, argv):
        super().__init__(argv)

        self.setQuitOnLastWindowClosed(False)  # Prevent quitting when the last window is closed

        self.settings = load_settings()

        # Apply the settings on startup
        self.apply_settings()

        # Create tray icon
        self.tray_icon = QSystemTrayIcon()
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
            self.about_dialog.setAttribute(Qt.WA_DeleteOnClose)  # Ensure the dialog is deleted when closed
        self.about_dialog.show()
        self.about_dialog.raise_()
        self.about_dialog.activateWindow()

    def exit_application(self):
        QApplication.quit()  # Properly exit the application

if __name__ == "__main__":
    app = TrayIconApp(sys.argv)
    sys.exit(app.exec_())
