#!/usr/bin/env bash
# Test AppImage on a clean Ubuntu image.
# Usage: test-appimage.sh <appimage-file>
set -euo pipefail

APPIMAGE_FILE="${1:-}"

[[ -f "$APPIMAGE_FILE" ]] || { echo "✗ AppImage not found: $APPIMAGE_FILE"; exit 1; }
command -v docker >/dev/null 2>&1 || { echo "⚠ docker not found — skipping"; exit 2; }

APPIMAGE_NAME="$(basename "$APPIMAGE_FILE")"
echo "→ Testing $APPIMAGE_NAME"

docker run --rm \
    --privileged \
    -v "$APPIMAGE_FILE:/tmp/$APPIMAGE_NAME:ro" \
    ubuntu:24.04 \
    bash -euo pipefail -c "
        export DEBIAN_FRONTEND=noninteractive
        apt-get update -qq
        apt-get install -y -qq libfuse2 libxcb-cursor0 libxcb1 libxkbcommon0 libxkbcommon-x11-0
        chmod +x /tmp/$APPIMAGE_NAME
        /tmp/$APPIMAGE_NAME --appimage-extract >/dev/null
        echo '→ Verifying AppImage contents'
        test -f squashfs-root/AppRun && echo 'AppRun OK'
        test -f squashfs-root/pipewire-controller.desktop && echo 'desktop file OK'
        test -f squashfs-root/pipewire-controller.png && echo 'icon OK'
        squashfs-root/AppRun python3 -c 'import pipewire_controller; print(\"import OK\")' 2>/dev/null || \
            python3 squashfs-root/opt/python3.11/bin/python3 -c \
                'import sys; sys.path.insert(0, \"squashfs-root/opt/python3.11/lib/python3.11/site-packages\"); import pipewire_controller; print(\"import OK\")'
        echo 'All checks passed'
    "
echo "✓ $APPIMAGE_NAME — OK"
