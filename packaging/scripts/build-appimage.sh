#!/usr/bin/env bash
# Build a self-contained AppImage locally using python-appimage.
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
VERSION="$(grep '^version' "$REPO_ROOT/pyproject.toml" | head -1 | sed 's/.*= *"\(.*\)"/\1/')"
OUTPUT="$REPO_ROOT/packaging/output"

command -v python-appimage >/dev/null 2>&1 || \
    python3 -m pip install --quiet python-appimage || \
    { echo "✗ python-appimage not available"; exit 1; }

mkdir -p "$OUTPUT"

# Install the package so find_spec can locate it
pip install -q --no-deps "$REPO_ROOT"

# Build appdir metadata
APPDIR_META="$(mktemp -d)"
trap 'rm -rf "$APPDIR_META"' EXIT

cat > "$APPDIR_META/requirements.txt" << EOF
PyQt6>=6.4
numpy>=1.24
local+pipewire_controller
EOF

cat > "$APPDIR_META/entrypoint.sh" << 'EOF'
#! /bin/bash
export QT_QPA_PLATFORM=xcb
"${APPDIR}/usr/bin/python3" -m pipewire_controller "$@"
EOF

# python-appimage derives the output filename from Name= in the desktop file
sed 's/^Name=.*/Name=PipeWireController/' \
    "$REPO_ROOT/packaging/specs/pipewire-controller.desktop" \
    > "$APPDIR_META/pipewire-controller.desktop"
cp "$REPO_ROOT/resources/icons/pipewire-controller.png" "$APPDIR_META/pipewire-controller.png"

WORKDIR="$(mktemp -d)"
trap 'rm -rf "$APPDIR_META" "$WORKDIR"' EXIT
cp -r "$APPDIR_META/." "$WORKDIR/appdir/"

cd "$WORKDIR"
python-appimage build app \
    --python-version 3.11 \
    --name PipeWireController \
    appdir

BUILT="$(ls "$WORKDIR"/PipeWireController-x86_64.AppImage 2>/dev/null | head -1)"
[ -z "$BUILT" ] && { echo "✗ AppImage not produced"; exit 1; }

cp "$BUILT" "$OUTPUT/PipeWireController-${VERSION}-x86_64.AppImage"
echo "✓ $OUTPUT/PipeWireController-${VERSION}-x86_64.AppImage"
