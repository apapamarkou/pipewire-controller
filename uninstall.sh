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
$script="pipewire-controller.py"

# Remove files
rm -f "$LOCAL_BIN_DIR/$script"
rm -f "$ICON_DIR/$script.png"
rm -f "$AUTOSTART_DIR/$script.desktop"
rm -f "$ΗΟΜΕ/.local/share/applications/$script.desktop"

echo "Uninstallation completed successfully."
