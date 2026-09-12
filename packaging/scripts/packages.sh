#!/usr/bin/env bash
# Package builder.
# Default: build all packages non-interactively.
# Usage: packages.sh [--interactive]
set -euo pipefail

INTERACTIVE=0
[[ "${1:-}" == "--interactive" ]] && INTERACTIVE=1

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
SCRIPTS="$REPO_ROOT/packaging/scripts"
CONF="$REPO_ROOT/packaging/distro-versions.conf"
VERSION="$(grep '^version' "$REPO_ROOT/pyproject.toml" | head -1 | sed 's/.*= *"\(.*\)"/\1/')"
OUTPUT="$REPO_ROOT/packaging/output"

RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'; CYAN='\033[0;36m'; NC='\033[0m'

header() { echo -e "\n${CYAN}══════════════════════════════════════${NC}"; echo -e "${CYAN}  $1${NC}"; echo -e "${CYAN}══════════════════════════════════════${NC}"; }
ok()     { echo -e "${GREEN}✓ $1${NC}"; }
warn()   { echo -e "${YELLOW}⚠ $1${NC}"; }
fail()   { echo -e "${RED}✗ $1${NC}"; }
ask()    { echo -e "${YELLOW}$1${NC}"; }

conf_versions() { grep "^$1=" "$CONF" | cut -d= -f2 | tr ',' ' '; }

run() {
    local label="$1"; shift
    header "Building: $label"
    local rc=0
    bash "$@" || rc=$?
    if   [[ $rc -eq 0 ]]; then ok "$label done"
    elif [[ $rc -eq 2 ]]; then warn "$label skipped — tool not available on this host"
    else fail "$label failed"
    fi
}

# ── Layer 2: version picker for multi-version distros ─────────────────────────
pick_versions() {
    local distro="$1" conf_key="$2" script="$3"
    local versions
    read -ra versions <<< "$(conf_versions "$conf_key")"

    if [[ $INTERACTIVE -eq 0 || ${#versions[@]} -eq 1 ]]; then
        for ver in "${versions[@]}"; do
            run "$distro $ver" "$script" "$ver"
        done
        return
    fi

    echo ""
    echo "  Available $distro versions:"
    for i in "${!versions[@]}"; do
        echo "    $((i+1))) ${versions[$i]}"
    done
    echo "    a) All"
    echo ""
    ask "Select version(s) for $distro (e.g. 1 2 or a):"
    read -r ver_choice

    if [[ "$ver_choice" == "a" ]]; then
        for ver in "${versions[@]}"; do
            run "$distro $ver" "$script" "$ver"
        done
    else
        for token in $ver_choice; do
            if [[ "$token" =~ ^[0-9]+$ ]] && (( token >= 1 && token <= ${#versions[@]} )); then
                local ver="${versions[$((token-1))]}"
                run "$distro $ver" "$script" "$ver"
            else
                warn "Invalid selection: $token — skipped"
            fi
        done
    fi
}

# ── Layer 1: package type menu ────────────────────────────────────────────────
header "PipeWire Audio Control Center — Package Builder v$VERSION"

if [[ $INTERACTIVE -eq 1 ]]; then
    echo ""
    echo "  1) Binary tarball (.tar.gz)"
    echo "  2) AppImage"
    echo "  3) openSUSE RPM"
    echo "  4) Fedora RPM"
    echo "  5) Debian .deb"
    echo "  6) Ubuntu .deb"
    echo "  7) Arch PKGBUILD"
    echo "  a) All of the above"
    echo ""
    ask "Select package type(s) (e.g. 1 4 5 or a):"
    read -r choices
    [[ "$choices" == "a" ]] && choices="1 2 3 4 5 6 7"
else
    choices="1 2 3 4 5 6 7"
fi

mkdir -p "$OUTPUT"

[[ "$choices" == *"1"* ]] && run "Binary tarball"  "$SCRIPTS/build-tarball.sh"
[[ "$choices" == *"2"* ]] && run "AppImage"        "$SCRIPTS/build-appimage.sh"
[[ "$choices" == *"3"* ]] && pick_versions "openSUSE" "opensuse-versions" "$SCRIPTS/build-opensuse-rpm.sh"
[[ "$choices" == *"4"* ]] && pick_versions "Fedora"   "fedora-versions"   "$SCRIPTS/build-fedora-rpm.sh"
[[ "$choices" == *"5"* ]] && pick_versions "Debian"   "debian-versions"   "$SCRIPTS/build-deb.sh"
[[ "$choices" == *"6"* ]] && pick_versions "Ubuntu"   "ubuntu-versions"   "$SCRIPTS/build-deb.sh"
[[ "$choices" == *"7"* ]] && run "Arch PKGBUILD"   "$SCRIPTS/build-arch-pkgbuild.sh"

# ── Summary ───────────────────────────────────────────────────────────────────
header "Output"
ls -lh "$OUTPUT"/ 2>/dev/null || warn "No output files found"
ok "Done"
