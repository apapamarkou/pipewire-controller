#!/usr/bin/env bash
# Generate a PKGBUILD for Arch Linux and test it with makepkg in Docker.
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
VERSION="$(grep '^version' "$REPO_ROOT/pyproject.toml" | head -1 | sed 's/.*= *"\(.*\)"/\1/')"
OUTPUT="$REPO_ROOT/packaging/output"
PKGBUILD_DIR="$OUTPUT/arch"

mkdir -p "$PKGBUILD_DIR"

LOCAL_TARBALL="$PKGBUILD_DIR/pipewire-controller-$VERSION.tar.gz"
git -C "$REPO_ROOT" archive --format=tar.gz --prefix="pipewire-controller-$VERSION/" HEAD \
    -o "$LOCAL_TARBALL"
SHA256="$(sha256sum "$LOCAL_TARBALL" | cut -d' ' -f1)"

echo "→ Generating PKGBUILD for pipewire-controller $VERSION"
cat > "$PKGBUILD_DIR/PKGBUILD" << EOF
# Maintainer: Andrianos Papamarkou <andrianos@example.com>
pkgname=pipewire-controller
pkgver=$VERSION
pkgrel=1
pkgdesc="PipeWire Audio Control Center — DAW Companion for Linux"
arch=('any')
url="https://github.com/apapamarkou/pipewire-controller"
license=('GPL-3.0-or-later')
depends=('python>=3.10' 'python-pyqt6' 'python-numpy' 'pipewire' 'wireplumber')
makedepends=('python-pip' 'python-hatchling')
source=("https://github.com/apapamarkou/pipewire-controller/archive/refs/tags/v\${pkgver}.tar.gz")
sha256sums=('$SHA256')

build() {
    cd "\$srcdir/pipewire-controller-\$pkgver"
    python -m pip wheel --no-build-isolation --no-deps -w dist .
}

package() {
    cd "\$srcdir/pipewire-controller-\$pkgver"
    python -m pip install --no-deps --root="\$pkgdir" --prefix=/usr dist/pipewire_controller-*.whl
    install -Dm644 resources/icons/pipewire-controller.png \\
        "\$pkgdir/usr/share/icons/hicolor/512x512/apps/pipewire-controller.png"
    install -Dm644 resources/icons/pipewire-controller.dark.png \\
        "\$pkgdir/usr/share/icons/hicolor/128x128/apps/pipewire-controller.dark.png"
    install -Dm644 resources/icons/pipewire-controller.light.png \\
        "\$pkgdir/usr/share/icons/hicolor/128x128/apps/pipewire-controller.light.png"
    install -Dm644 packaging/specs/pipewire-controller.desktop \\
        "\$pkgdir/usr/share/applications/pipewire-controller.desktop"
    install -Dm644 LICENSE \\
        "\$pkgdir/usr/share/licenses/\$pkgname/LICENSE"
}
EOF

echo "✓ PKGBUILD written to $PKGBUILD_DIR/PKGBUILD"
echo "  sha256: $SHA256"
echo "  Note: update source= URL and sha256sums after pushing the GitHub tag."

if command -v docker >/dev/null 2>&1; then
    echo "→ Testing PKGBUILD with makepkg in Docker (archlinux)"
    docker run --rm \
        -v "$PKGBUILD_DIR:/build:z" \
        archlinux:latest \
        bash -euo pipefail -c "
            pacman -Sy --noconfirm base-devel python-pip python-hatchling 2>/dev/null
            useradd -m builder
            cp /build/PKGBUILD /home/builder/
            cp /build/pipewire-controller-$VERSION.tar.gz /home/builder/
            chown -R builder /home/builder/
            cd /home/builder
            sed -i 's|source=(.*)|source=(\"pipewire-controller-$VERSION.tar.gz\")|' PKGBUILD
            sudo -u builder makepkg --noconfirm --nodeps -f
            find /home/builder -name '*.pkg.tar.zst' -exec cp {} /build/ \;
        "
    echo "✓ Arch package in $PKGBUILD_DIR/"
else
    echo "⚠ Docker not found — PKGBUILD generated but not tested"
    echo "  To build: cd $PKGBUILD_DIR && makepkg -si"
fi
