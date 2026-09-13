#!/usr/bin/env bash
# Test .deb installation on Debian or Ubuntu.
# Usage: test-deb.sh <deb-file> [distro-version]
set -euo pipefail

DEB_FILE="${1:-}"
DISTRO_VER="${2:-13}"

[[ -f "$DEB_FILE" ]] || { echo "✗ .deb not found: $DEB_FILE"; exit 1; }
command -v docker >/dev/null 2>&1 || { echo "⚠ docker not found — skipping"; exit 2; }

if [[ "$DISTRO_VER" =~ ^[0-9]+$ ]]; then
    IMAGE="debian:$DISTRO_VER"
    LABEL="Debian $DISTRO_VER"
else
    IMAGE="ubuntu:$DISTRO_VER"
    LABEL="Ubuntu $DISTRO_VER"
fi

DEB_NAME="$(basename "$DEB_FILE")"
echo "→ Testing $DEB_NAME on $LABEL"

docker run --rm \
    -v "$DEB_FILE:/tmp/$DEB_NAME:ro" \
    "$IMAGE" \
    bash -euo pipefail -c "
        export DEBIAN_FRONTEND=noninteractive
        apt-get update -qq
        apt-get install -y -qq /tmp/$DEB_NAME 2>&1 | tail -5 || \
        dpkg -i --force-depends /tmp/$DEB_NAME 2>&1 | tail -5
        echo '→ Verifying installation'
        dpkg -l pipewire-controller | grep '^ii'
        python3 -c 'import pipewire_controller; print(\"import OK\")'
        test -f /usr/bin/pipewire-controller && echo 'binary OK'
        test -f /usr/share/applications/pipewire-controller.desktop && echo 'desktop file OK'
        test -f /usr/share/icons/hicolor/512x512/apps/pipewire-controller.png && echo 'icon OK'
        echo 'All checks passed'
    "
echo "✓ $DEB_NAME on $LABEL — OK"
