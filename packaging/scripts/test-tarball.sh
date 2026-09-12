#!/usr/bin/env bash
# Test the tarball installer in a temporary directory (no Docker required).
# This validates the package structure and install script logic without
# damaging the developer's host installation.
#
# Usage: test-tarball.sh [tarball]
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
OUTPUT="$REPO_ROOT/packaging/output"

RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'; CYAN='\033[0;36m'; NC='\033[0m'
ok()   { echo -e "${GREEN}✓${NC} $*"; }
fail() { echo -e "${RED}✗${NC} $*" >&2; exit 1; }
info() { echo -e "${CYAN}→${NC} $*"; }
warn() { echo -e "${YELLOW}⚠${NC} $*"; }

# Find tarball
TARBALL="${1:-}"
if [[ -z "$TARBALL" ]]; then
    TARBALL="$(ls "$OUTPUT"/pipewire-controller-*-linux.tar.gz 2>/dev/null | head -1)"
fi
[[ -f "$TARBALL" ]] || fail "No tarball found. Run 'make package' first."

info "Testing: $(basename "$TARBALL")"

# ── Structure check ───────────────────────────────────────────────────────────
info "Checking tarball structure..."

CONTENTS="$(tar -tzf "$TARBALL")"

check_file() {
    echo "$CONTENTS" | grep -q "$1" || fail "Missing in tarball: $1"
    ok "Found: $1"
}

check_file "wheels/pipewire.controller-"
check_file "install"
check_file "uninstall"
check_file "README.md"
check_file "LICENSE"
check_file "pipewire-controller.desktop"
check_file "pipewire-controller.png"

# ── Wheel validity ────────────────────────────────────────────────────────────
info "Checking wheel..."
TMPDIR="$(mktemp -d)"
trap 'rm -rf "$TMPDIR"' EXIT

tar -xzf "$TARBALL" -C "$TMPDIR" --strip-components=1

WHEEL="$(ls "$TMPDIR/wheels"/pipewire_controller-*.whl 2>/dev/null | head -1)"
[[ -f "$WHEEL" ]] || fail "Wheel not found after extraction"
ok "Wheel found: $(basename "$WHEEL")"

# Check wheel is a valid zip
python3 -c "import zipfile; zipfile.ZipFile('$WHEEL').testzip()" || fail "Wheel is not a valid zip"
ok "Wheel is valid zip"

# Check wheel contains expected modules
WHEEL_CONTENTS="$(python3 -c "import zipfile; print('\n'.join(zipfile.ZipFile('$WHEEL').namelist()))")"
echo "$WHEEL_CONTENTS" | grep -q "pipewire_controller/__init__.py" || fail "Missing __init__.py in wheel"
echo "$WHEEL_CONTENTS" | grep -q "pipewire_controller/__main__.py" || fail "Missing __main__.py in wheel"
ok "Wheel contains required modules"

# ── Install script syntax ─────────────────────────────────────────────────────
info "Checking install script syntax..."
bash -n "$TMPDIR/install" || fail "install script has syntax errors"
ok "install script syntax OK"
bash -n "$TMPDIR/uninstall" || fail "uninstall script has syntax errors"
ok "uninstall script syntax OK"

# ── Python import check ───────────────────────────────────────────────────────
info "Checking Python importability..."
INSTALL_DIR="$(mktemp -d)"
trap 'rm -rf "$TMPDIR" "$INSTALL_DIR"' EXIT

pip3 install --quiet --target="$INSTALL_DIR" "$WHEEL" 2>/dev/null || \
    pip3 install --quiet --target="$INSTALL_DIR" --break-system-packages "$WHEEL" 2>/dev/null || \
    warn "pip install to temp dir failed — skipping import check"

if [[ -d "$INSTALL_DIR/pipewire_controller" ]]; then
    PYTHONPATH="$INSTALL_DIR" python3 -c "
import pipewire_controller
from pipewire_controller.detection import detect_system
from pipewire_controller.config import load
from pipewire_controller.latency import generate_chirp
from pipewire_controller.metering import ChannelMeter
print('All imports OK')
" || fail "Import check failed"
    ok "Python imports OK"
fi

echo ""
ok "Package test passed: $(basename "$TARBALL")"
