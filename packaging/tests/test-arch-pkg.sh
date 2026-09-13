#!/usr/bin/env bash
# Test Arch PKGBUILD / .pkg.tar.zst installation.
# Usage: test-arch-pkg.sh <pkg-file>
set -euo pipefail

PKG_FILE="${1:-}"

[[ -f "$PKG_FILE" ]] || { echo "✗ Package not found: $PKG_FILE"; exit 1; }
command -v docker >/dev/null 2>&1 || { echo "⚠ docker not found — skipping"; exit 2; }

PKG_NAME="$(basename "$PKG_FILE")"
echo "→ Testing $PKG_NAME on Arch Linux"

docker run --rm \
    -v "$PKG_FILE:/tmp/$PKG_NAME:ro" \
    archlinux:latest \
    bash -euo pipefail -c "
        pacman -Sy --noconfirm 2>&1 | tail -3
        pacman -U --noconfirm --nodeps /tmp/$PKG_NAME 2>&1 | tail -5
        echo '→ Verifying installation'
        pacman -Q pipewire-controller
        python3 -c 'import pipewire_controller; print(\"import OK\")'
        test -f /usr/bin/pipewire-controller && echo 'binary OK'
        test -f /usr/share/applications/pipewire-controller.desktop && echo 'desktop file OK'
        test -f /usr/share/icons/hicolor/512x512/apps/pipewire-controller.png && echo 'icon OK'
        echo 'All checks passed'
    "
echo "✓ $PKG_NAME on Arch Linux — OK"
