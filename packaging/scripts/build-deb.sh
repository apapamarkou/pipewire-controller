#!/usr/bin/env bash
# Build a .deb package inside a Docker container.
# Usage: build-deb.sh [distro-version]  e.g. build-deb.sh 24.04
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
VERSION="$(grep '^version' "$REPO_ROOT/pyproject.toml" | head -1 | sed 's/.*= *"\(.*\)"/\1/')"
OUTPUT="$REPO_ROOT/packaging/output"
CONF="$REPO_ROOT/packaging/distro-versions.conf"

DISTRO_VER="${1:-$(grep '^debian-versions=' "$CONF" | cut -d= -f2 | cut -d, -f1)}"

if [[ "$DISTRO_VER" =~ ^[0-9]+$ ]]; then
    IMAGE="debian:$DISTRO_VER"
    LABEL="Debian $DISTRO_VER"
else
    IMAGE="ubuntu:$DISTRO_VER"
    LABEL="Ubuntu $DISTRO_VER"
fi

command -v docker >/dev/null 2>&1 || { echo "⚠ docker not found — skipping"; exit 2; }

mkdir -p "$OUTPUT"

echo "→ Building $LABEL .deb in Docker"

WHEEL_DIR="$(mktemp -d)"
python3 -m pip wheel "$REPO_ROOT" --no-deps -w "$WHEEL_DIR" -q

docker run --rm \
    -v "$REPO_ROOT:/src:ro,z" \
    -v "$OUTPUT:/output:z" \
    -v "$WHEEL_DIR:/wheels:ro,z" \
    "$IMAGE" \
    bash -euo pipefail -c "
        export DEBIAN_FRONTEND=noninteractive
        apt-get update -qq
        apt-get install -y -qq dpkg-dev devscripts python3-pip git debhelper
        git config --global --add safe.directory /src
        STAGING=/tmp/deb-build/pipewire-controller-$VERSION
        mkdir -p \$STAGING
        git -C /src archive --format=tar HEAD | tar -x -C \$STAGING
        cp -r /src/packaging/debian \$STAGING/debian
        chmod +x \$STAGING/debian/rules
        cd \$STAGING
        dpkg-buildpackage -us -uc -b
        find /tmp/deb-build -name '*.deb' | while read -r f; do
            base=\"\$(basename \"\$f\" .deb)\"
            cp \"\$f\" /output/\${base}~${DISTRO_VER}.deb
        done
    "
rm -rf "$WHEEL_DIR"

echo "✓ $LABEL .deb in $OUTPUT/"
