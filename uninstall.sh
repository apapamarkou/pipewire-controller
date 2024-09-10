#!/bin/bash

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

# Define target directories
LOCAL_BIN_DIR="$HOME/.local/bin"
ICON_DIR="$HOME/.local/share/icons"
AUTOSTART_DIR="$HOME/.config/autostart"
SCRIPT="pipewire-controller.py"

# Remove files
rm -f "$LOCAL_BIN_DIR/$SCRIPT"
rm -f "$ICON_DIR/$SCRIPT.png"
rm -f "$AUTOSTART_DIR/$SCRIPT.desktop"
rm -f "$ΗΟΜΕ/.local/share/applications/$SCRIPT.desktop"

echo "Uninstallation completed successfully."
