#!/usr/bin/env bash
# Build a binary tarball: pipewire-controller-VERSION-linux.tar.gz
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
VERSION="$(grep '^version' "$REPO_ROOT/pyproject.toml" | head -1 | sed 's/.*= *"\(.*\)"/\1/')"
OUTPUT="$REPO_ROOT/packaging/output"
NAME="pipewire-controller-$VERSION-linux"
STAGING="$OUTPUT/$NAME"

mkdir -p "$OUTPUT"
rm -rf "$STAGING"
mkdir -p "$STAGING"

echo "→ Building wheel"
python3 -m pip wheel "$REPO_ROOT" --no-deps -w "$STAGING/wheels" -q

echo "→ Copying assets"
cp "$REPO_ROOT/packaging/specs/pipewire-controller.desktop" "$STAGING/"
cp "$REPO_ROOT/resources/icons/pipewire-controller.dark.png"  "$STAGING/pipewire-controller.dark.png"
cp "$REPO_ROOT/resources/icons/pipewire-controller.light.png" "$STAGING/pipewire-controller.light.png"
cp "$REPO_ROOT/resources/icons/pipewire-controller.png"       "$STAGING/pipewire-controller.png"
cp "$REPO_ROOT/README.md"                                    "$STAGING/"
cp "$REPO_ROOT/LICENSE"                                      "$STAGING/"
cp "$REPO_ROOT/install"                                      "$STAGING/install"
cp "$REPO_ROOT/uninstall"                                    "$STAGING/uninstall"
chmod +x "$STAGING/install" "$STAGING/uninstall"

echo "→ Creating tarball"
tar -czf "$OUTPUT/$NAME.tar.gz" -C "$OUTPUT" "$NAME"
rm -rf "$STAGING"

echo "✓ $OUTPUT/$NAME.tar.gz"
