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

# Get the directory of the script
SCRIPT_DIR="$(dirname "$(realpath "$0")")"

# Define target directories
LOCAL_BIN_DIR="$HOME/.local/bin"
ICON_DIR="$HOME/.local/share/icons"
AUTOSTART_DIR="$HOME/.config/autostart"

# Create the ~/.local/bin directory if it doesn't exist
if [ ! -d "$LOCAL_BIN_DIR" ]; then
    echo "Creating directory $LOCAL_BIN_DIR"
    mkdir -p "$LOCAL_BIN_DIR"
fi

# Create the ~/.local/bin directory if it doesn't exist
if [ ! -d "$ICON_DIR" ]; then
    echo "Creating directory $ICON_DIR"
    mkdir -p "$ICON_DIR"
fi

SCRIPT="pipewire-controller.py"

# Copy script to ~/.local/bin
cp "$SCRIPT_DIR/src/$SCRIPT" "$LOCAL_BIN_DIR"
# Make sure the script is executable
chmod a+x "$LOCAL_BIN_DIR/$SCRIPT"

# Copy icon to ~/.local/share/icons
cp "$SCRIPT_DIR/src/$SCRIPT.png" "$ICON_DIR"

# Create the ~/.config/autostart directory if it doesn't exist
if [ ! -d "$AUTOSTART_DIR" ]; then
    echo "Creating directory $AUTOSTART_DIR"
    mkdir -p "$AUTOSTART_DIR"
fi

# Create the desktop file in autostart
echo "[Desktop Entry]
Type=Application
Name=Pipewire Audio Controller
Comment=Control your audio
Exec=$LOCAL_BIN_DIR/$SCRIPT $1
Icon=$ICON_DIR/$SCRIPT.png
Terminal=false
Categories=AudioVideo;Audio;Settings;
StartupNotify=true
" > "$AUTOSTART_DIR/$SCRIPT.desktop"

mkdir -p "$HOME/.local/share/applications"
# Create the desktop file in applications
echo "[Desktop Entry]
Type=Application
Name=Pipewire Audio Controller
Comment=Control your audio
Exec=$LOCAL_BIN_DIR/$SCRIPT $1
Icon=$ICON_DIR/$SCRIPT.png
Terminal=false
Categories=AudioVideo;Audio;Settings;
StartupNotify=true
" > "$HOME/.local/share/applications/$SCRIPT.desktop"

# Make sure the desktop file is executable
chmod a+x "$AUTOSTART_DIR/$SCRIPT.desktop"
chmod a+x  "$HOME/.local/share/applications/$SCRIPT.desktop"

echo "Desktop file created at $AUTOSTART_DIR/$SCRIPT.desktop"
echo "Installation complete. You can now use the tray icon to control your audio."

# Run the script
$LOCAL_BIN_DIR/$SCRIPT $1 &

# Remove the local copy of the git repo
echo "Removing local copy of git repo..."
rm -rf "$SCRIPT_DIR"

echo "Pipewire Controller has been started."
echo "Enjoy your audio!"
