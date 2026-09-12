#!/usr/bin/env bash
# Test all built packages against clean Docker images.
# Default: test all packages non-interactively.
# Usage: test-packages.sh [--interactive]
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
OUTPUT="$REPO_ROOT/packaging/output"
TESTS="$REPO_ROOT/packaging/tests"
CONF="$REPO_ROOT/packaging/distro-versions.conf"

RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'; CYAN='\033[0;36m'; NC='\033[0m'

header() { echo -e "\n${CYAN}══════════════════════════════════════${NC}"; echo -e "${CYAN}  $1${NC}"; echo -e "${CYAN}══════════════════════════════════════${NC}"; }
ok()     { echo -e "${GREEN}✓ $1${NC}"; }
warn()   { echo -e "${YELLOW}⚠ $1${NC}"; }
fail()   { echo -e "${RED}✗ $1${NC}"; }

conf_versions() { grep "^$1=" "$CONF" | cut -d= -f2 | tr ',' ' '; }

INTERACTIVE="${1:-}"
[[ "$INTERACTIVE" == "--interactive" ]] || INTERACTIVE=""
PASS=0; FAIL=0; SKIP=0

run_test() {
    local label="$1" script="$2"; shift 2
    echo ""
    echo -e "${CYAN}── Testing: $label${NC}"
    local rc=0
    bash "$script" "$@" || rc=$?
    if   [[ $rc -eq 0 ]]; then ok "$label"; PASS=$((PASS + 1))
    elif [[ $rc -eq 2 ]]; then warn "$label — skipped (tool not available)"; SKIP=$((SKIP + 1))
    else fail "$label"; FAIL=$((FAIL + 1))
    fi
}

header "PipeWire Audio Control Center — Package Installation Tests"

if [[ -n "$INTERACTIVE" ]]; then
    echo ""
    echo "  1) Tarball installer"
    echo "  2) AppImage"
    echo "  3) Fedora RPMs"
    echo "  4) openSUSE RPMs"
    echo "  5) Debian .debs"
    echo "  6) Ubuntu .debs"
    echo "  7) Arch package"
    echo "  a) All"
    echo ""
    echo -e "${YELLOW}Select tests to run (e.g. 1 3 or a):${NC}"
    read -r choices
    [[ "$choices" == "a" ]] && choices="1 2 3 4 5 6 7"
else
    choices="1 2 3 4 5 6 7"
fi

# ── Tarball installer ─────────────────────────────────────────────────────────
if [[ "$choices" == *"1"* ]]; then
    header "Tarball installer"
    pkg="$(ls "$OUTPUT"/pipewire-controller-*-linux.tar.gz 2>/dev/null | head -1)"
    if [[ -z "$pkg" ]]; then
        warn "No tarball found in $OUTPUT — skipping"
        SKIP=$((SKIP + 1))
    else
        for ver in $(conf_versions "fedora-versions"); do
            run_test "Tarball on Fedora $ver" "$TESTS/test-tarball.sh" "$pkg" "fedora:$ver" "Fedora $ver"
        done
        for ver in $(conf_versions "opensuse-versions"); do
            case "$ver" in
                tumbleweed) img="opensuse/tumbleweed" ;;
                *)          img="opensuse/leap:$ver" ;;
            esac
            run_test "Tarball on openSUSE $ver" "$TESTS/test-tarball.sh" "$pkg" "$img" "openSUSE $ver"
        done
        for ver in $(conf_versions "debian-versions"); do
            run_test "Tarball on Debian $ver" "$TESTS/test-tarball.sh" "$pkg" "debian:$ver" "Debian $ver"
        done
        for ver in $(conf_versions "ubuntu-versions"); do
            run_test "Tarball on Ubuntu $ver" "$TESTS/test-tarball.sh" "$pkg" "ubuntu:$ver" "Ubuntu $ver"
        done
        run_test "Tarball on Arch" "$TESTS/test-tarball.sh" "$pkg" "archlinux:latest" "Arch"
    fi
fi

# ── AppImage ──────────────────────────────────────────────────────────────────
if [[ "$choices" == *"2"* ]]; then
    header "AppImage"
    pkg="$(ls "$OUTPUT"/PipeWireController-*.AppImage 2>/dev/null | head -1)"
    if [[ -n "$pkg" ]]; then
        run_test "AppImage" "$TESTS/test-appimage.sh" "$pkg"
    else
        warn "No AppImage found in $OUTPUT — skipping"
        SKIP=$((SKIP + 1))
    fi
fi

# ── Fedora RPMs ───────────────────────────────────────────────────────────────
if [[ "$choices" == *"3"* ]]; then
    header "Fedora RPMs"
    for ver in $(conf_versions "fedora-versions"); do
        pkg="$(ls "$OUTPUT"/pipewire-controller-*.fc${ver}.noarch.rpm 2>/dev/null | head -1)"
        if [[ -n "$pkg" ]]; then
            run_test "Fedora $ver RPM" "$TESTS/test-fedora-rpm.sh" "$pkg" "$ver"
        else
            warn "No Fedora $ver RPM found in $OUTPUT — skipping"
            SKIP=$((SKIP + 1))
        fi
    done
fi

# ── openSUSE RPMs ─────────────────────────────────────────────────────────────
if [[ "$choices" == *"4"* ]]; then
    header "openSUSE RPMs"
    for ver in $(conf_versions "opensuse-versions"); do
        pkg="$(ls "$OUTPUT"/pipewire-controller-*.opensuse*.noarch.rpm 2>/dev/null | head -1)"
        if [[ -n "$pkg" ]]; then
            run_test "openSUSE $ver RPM" "$TESTS/test-opensuse-rpm.sh" "$pkg" "$ver"
        else
            warn "No openSUSE RPM found in $OUTPUT — skipping"
            SKIP=$((SKIP + 1))
        fi
    done
fi

# ── Debian .debs ──────────────────────────────────────────────────────────────
if [[ "$choices" == *"5"* ]]; then
    header "Debian .debs"
    for ver in $(conf_versions "debian-versions"); do
        pkg="$(ls "$OUTPUT"/pipewire-controller_*~${ver}.deb 2>/dev/null | head -1)"
        if [[ -n "$pkg" ]]; then
            run_test "Debian $ver .deb" "$TESTS/test-deb.sh" "$pkg" "$ver"
        else
            warn "No Debian $ver .deb found in $OUTPUT — skipping"
            SKIP=$((SKIP + 1))
        fi
    done
fi

# ── Ubuntu .debs ──────────────────────────────────────────────────────────────
if [[ "$choices" == *"6"* ]]; then
    header "Ubuntu .debs"
    for ver in $(conf_versions "ubuntu-versions"); do
        pkg="$(ls "$OUTPUT"/pipewire-controller_*~${ver}.deb 2>/dev/null | head -1)"
        if [[ -n "$pkg" ]]; then
            run_test "Ubuntu $ver .deb" "$TESTS/test-deb.sh" "$pkg" "$ver"
        else
            warn "No Ubuntu $ver .deb found in $OUTPUT — skipping"
            SKIP=$((SKIP + 1))
        fi
    done
fi

# ── Arch package ──────────────────────────────────────────────────────────────
if [[ "$choices" == *"7"* ]]; then
    header "Arch package"
    pkg="$(ls "$OUTPUT"/arch/pipewire-controller-*.pkg.tar.zst 2>/dev/null | head -1)"
    if [[ -n "$pkg" ]]; then
        run_test "Arch package" "$TESTS/test-arch-pkg.sh" "$pkg"
    else
        warn "No Arch package found in $OUTPUT/arch — skipping"
        SKIP=$((SKIP + 1))
    fi
fi

# ── Summary ───────────────────────────────────────────────────────────────────
header "Results"
echo -e "  ${GREEN}Passed:  $PASS${NC}"
echo -e "  ${RED}Failed:  $FAIL${NC}"
echo -e "  ${YELLOW}Skipped: $SKIP${NC}"
echo ""
if [[ $FAIL -gt 0 ]]; then
    fail "$FAIL test(s) failed"; exit 1
elif [[ $PASS -eq 0 ]]; then
    fail "No packages found to test — run 'make packages' first"; exit 1
else
    ok "All tests passed"
fi
