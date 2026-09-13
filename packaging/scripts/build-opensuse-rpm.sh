#!/usr/bin/env bash
# Build openSUSE RPM inside a Docker container.
# Usage: build-opensuse-rpm.sh [tumbleweed|leap-version]
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
VERSION="$(grep '^version' "$REPO_ROOT/pyproject.toml" | head -1 | sed 's/.*= *"\(.*\)"/\1/')"
OUTPUT="$REPO_ROOT/packaging/output"
CONF="$REPO_ROOT/packaging/distro-versions.conf"

SUSE_VER="${1:-$(grep '^opensuse-versions=' "$CONF" | cut -d= -f2 | cut -d, -f1)}"
case "$SUSE_VER" in
    tumbleweed) IMAGE="opensuse/tumbleweed" ;;
    *)          IMAGE="opensuse/leap:$SUSE_VER" ;;
esac

command -v docker >/dev/null 2>&1 || { echo "⚠ docker not found — skipping"; exit 2; }

mkdir -p "$OUTPUT"

echo "→ Building openSUSE $SUSE_VER RPM in Docker"

WHEEL_DIR="$(mktemp -d)"
python3 -m pip wheel "$REPO_ROOT" --no-deps -w "$WHEEL_DIR" -q

docker run --rm \
    -v "$REPO_ROOT:/src:ro,z" \
    -v "$OUTPUT:/output:z" \
    -v "$WHEEL_DIR:/wheels:ro,z" \
    "$IMAGE" \
    bash -euo pipefail -c "
        zypper install -y rpm-build python3-pip git python3-rpm-macros
        git config --global --add safe.directory /src
        RPMBUILD=/tmp/rpmbuild
        mkdir -p \$RPMBUILD/{BUILD,RPMS,SOURCES,SPECS,SRPMS}
        git -C /src archive --format=tar.gz --prefix=pipewire-controller-$VERSION/ HEAD \
            -o \$RPMBUILD/SOURCES/pipewire-controller-$VERSION.tar.gz
        # Inject untracked icons into the source tarball
        cd \$RPMBUILD/SOURCES
        tar -xzf pipewire-controller-$VERSION.tar.gz
        cp /src/resources/icons/pipewire-controller.png      pipewire-controller-$VERSION/resources/icons/
        cp /src/resources/icons/pipewire-controller.dark.png  pipewire-controller-$VERSION/resources/icons/
        cp /src/resources/icons/pipewire-controller.light.png pipewire-controller-$VERSION/resources/icons/
        tar -czf pipewire-controller-$VERSION.tar.gz pipewire-controller-$VERSION/
        rm -rf pipewire-controller-$VERSION/
        cp /src/packaging/specs/pipewire-controller.spec \$RPMBUILD/SPECS/
        sed -i 's|python3 -m pip install --no-build-isolation --root=%{buildroot} --prefix=%{_prefix} .|pip3 install --no-deps --root=%{buildroot} --prefix=%{_prefix} /wheels/pipewire_controller-*.whl|' \$RPMBUILD/SPECS/pipewire-controller.spec
        sed -i 's|Requires:.*python3-pyqt6.*|Requires:       python3-qt6 >= 6.4|' \$RPMBUILD/SPECS/pipewire-controller.spec
        rpmbuild -ba \
            --define '_topdir '\$RPMBUILD \
            --define 'dist .opensuse${SUSE_VER}' \
            \$RPMBUILD/SPECS/pipewire-controller.spec
        find \$RPMBUILD/RPMS \$RPMBUILD/SRPMS -name '*.rpm' -exec cp {} /output/ \;
    "
rm -rf "$WHEEL_DIR"

echo "✓ openSUSE $SUSE_VER RPM in $OUTPUT/"
