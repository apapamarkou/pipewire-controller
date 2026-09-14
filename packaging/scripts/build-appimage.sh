#!/usr/bin/env bash
# Build a self-contained AppImage inside Ubuntu 26.04 Docker.
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
VERSION="$(grep '^version' "$REPO_ROOT/pyproject.toml" | head -1 | sed 's/.*= *"\(.*\)"/\1/')"
OUTPUT="$REPO_ROOT/packaging/output"
FINAL="$OUTPUT/PipeWireController-${VERSION}-x86_64.AppImage"

command -v docker >/dev/null 2>&1 || { echo "⚠ docker not found — skipping"; exit 2; }

mkdir -p "$OUTPUT"
rm -f "$FINAL"

# Build wheel on host
WHEEL_DIR="$(mktemp -d)"
trap 'rm -rf "$WHEEL_DIR"' EXIT
python3 -m pip wheel "$REPO_ROOT" --no-deps -w "$WHEEL_DIR" -q
WHEEL_NAME="$(basename "$WHEEL_DIR"/pipewire_controller-*.whl)"

# python-appimage names the AppImage after the requirements file basename.
# A file with no extension -> "PipeWireController-x86_64.AppImage"
mkdir -p "$WHEEL_DIR/appbuild"
printf 'PyQt6>=6.4\nnumpy>=1.24\n' > "$WHEEL_DIR/appbuild/PipeWireController"

sed 's/^Name=.*/Name=PipeWireController/' \
    "$REPO_ROOT/packaging/specs/pipewire-controller.desktop" \
    > "$WHEEL_DIR/pipewire-controller.desktop"
cp "$REPO_ROOT/resources/icons/pipewire-controller.png" "$WHEEL_DIR/pipewire-controller.png"

# Write AppRun entry point as a file (avoids quoting issues inside Docker -c string)
cat > "$WHEEL_DIR/AppRun" << 'APPRUNEOF'
#!/bin/bash
export LD_LIBRARY_PATH="${APPDIR}/usr/lib${LD_LIBRARY_PATH:+:$LD_LIBRARY_PATH}"
export QT_QPA_PLATFORM=xcb
exec "${APPDIR}/opt/python3.10/bin/python3.10" -m pipewire_controller "$@"
APPRUNEOF
cat > "$WHEEL_DIR/appimage_offset.py" << 'PYEOF'
#!/usr/bin/env python3
"""Print the byte offset where the squashfs filesystem starts in an AppImage."""
import struct, sys

path = sys.argv[1]
with open(path, "rb") as f:
    hdr = f.read(64)

assert hdr[:4] == b"\x7fELF", f"Not an ELF binary: {hdr[:4]!r}"

bits = hdr[4]  # 1 = 32-bit, 2 = 64-bit
if bits == 2:
    e_shoff     = struct.unpack_from("<Q", hdr, 40)[0]
    e_shentsize = struct.unpack_from("<H", hdr, 58)[0]
    e_shnum     = struct.unpack_from("<H", hdr, 60)[0]
else:
    e_shoff     = struct.unpack_from("<I", hdr, 32)[0]
    e_shentsize = struct.unpack_from("<H", hdr, 46)[0]
    e_shnum     = struct.unpack_from("<H", hdr, 48)[0]

end = e_shoff + e_shentsize * e_shnum
end = (end + 3) & ~3  # squashfs is 4-byte aligned

with open(path, "rb") as f:
    f.seek(end)
    sig = f.read(4)

if sig not in (b"hsqs", b"sqsh"):
    # Scan forward for the squashfs magic
    with open(path, "rb") as f:
        data = f.read()
    for m in (b"hsqs", b"sqsh"):
        idx = data.find(m, end)
        if idx != -1:
            end = idx
            break
    else:
        sys.exit(f"ERROR: squashfs magic not found after offset {end}")

print(end)
PYEOF

echo "→ Building AppImage in Docker (ubuntu:26.04)"

docker run --rm --privileged \
    -v "$OUTPUT:/output:z" \
    -v "$WHEEL_DIR:/meta:ro,z" \
    -e VERSION="$VERSION" \
    -e WHEEL_NAME="$WHEEL_NAME" \
    ubuntu:26.04 \
    bash -euo pipefail -c '
        export DEBIAN_FRONTEND=noninteractive
        apt-get update -qq
        apt-get install -y -qq \
            python3 python3-pip wget file squashfs-tools fuse \
            libxcb-cursor0 libxcb-util1 libxcb-render-util0 libxcb-image0 \
            libxcb-icccm4 libxcb-keysyms1 libxcb-shape0 libxcb-randr0 \
            libxcb-xfixes0 libxcb-sync1 libxcb-xkb1 libxcb-glx0 \
            libxcb-render0 libxcb-shm0 libxcb1 \
            libxkbcommon0 libxkbcommon-x11-0

        python3 -m pip install -q --break-system-packages python-appimage

        WORKDIR="$(mktemp -d)"
        cp /meta/appbuild/PipeWireController \
           /meta/pipewire-controller.desktop \
           /meta/pipewire-controller.png \
           "$WORKDIR/"

        cd "$WORKDIR"

        # Step 1: use python-appimage to get a bundled Python 3.10 AppImage.
        # We pass an empty requirements file — deps are installed manually below
        # because python-appimage fails to resolve binary wheels like PyQt6.
        printf "" > "$WORKDIR/PipeWireController"
        python3 -m python_appimage build app -p 3.10 PipeWireController

        BUILT="$(find "$WORKDIR" -maxdepth 1 -name "PipeWireController*.AppImage" | head -1)"
        if [[ -z "$BUILT" ]]; then
            echo "✗ python-appimage did not produce PipeWireController*.AppImage"
            ls -la "$WORKDIR/"
            exit 1
        fi
        echo "  produced: $(basename "$BUILT")"

        # Step 2: find squashfs offset and extract without FUSE
        chmod +x "$BUILT"
        APPDIR="$WORKDIR/squashfs-root"
        OFFSET="$(python3 /meta/appimage_offset.py "$BUILT")"
        echo "  squashfs offset: $OFFSET"
        unsquashfs -no-xattrs -o "$OFFSET" -d "$APPDIR" "$BUILT" >/dev/null
        [[ -d "$APPDIR" ]] || { echo "✗ unsquashfs failed"; exit 1; }

        # Step 3: install ALL deps + the app wheel into the bundled Python.
        # python-appimage places the real interpreter at opt/python3.10/bin/python3.10
        # usr/bin/python3.10 is just a shell wrapper — do not use it for pip.
        BUNDLED_PY="$(find "$APPDIR/opt" -name "python3.10" -type f | head -1)"
        if [[ -z "$BUNDLED_PY" ]]; then
            echo "✗ bundled Python not found under $APPDIR/opt"
            find "$APPDIR" -name "python3*" -type f | head -10 || true
            exit 1
        fi
        echo "  bundled Python: $BUNDLED_PY"

        # Install deps using the bundled pip. Skip platform flags - let pip
        # resolve the correct wheel for the container glibc version.
        # Upgrade pip first to ensure modern dependency resolution.
        "$BUNDLED_PY" -m pip install -q --upgrade pip
        "$BUNDLED_PY" -m pip install -q "PyQt6>=6.4" "PyQt6-Qt6>=6.4" "PyQt6-sip" "numpy>=1.24"

        # Install our app wheel (pure Python, no platform tags needed)
        "$BUNDLED_PY" -m pip install -q --no-deps "/meta/${WHEEL_NAME}"
        echo "  installed all packages into bundled Python"

        # Step 4: replace AppRun to launch our app via the real Python binary
        # APPDIR is set by the AppImage runtime before invoking AppRun
        cp /meta/AppRun "$APPDIR/AppRun"
        chmod +x "$APPDIR/AppRun"

        # Step 5: bundle xcb/xkb libs for portability on older distros
        LIBDIR="$APPDIR/usr/lib"
        mkdir -p "$LIBDIR"
        for lib in \
            libxcb-cursor.so.0 libxcb-util.so.1 libxcb-render-util.so.0 \
            libxcb-image.so.0 libxcb-icccm.so.4 libxcb-keysyms.so.1 \
            libxcb-shape.so.0 libxcb-randr.so.0 libxcb-xfixes.so.0 \
            libxcb-sync.so.1 libxcb-xkb.so.1 libxcb-glx.so.0 \
            libxcb-render.so.0 libxcb-shm.so.0 libxcb.so.1 \
            libxkbcommon.so.0 libxkbcommon-x11.so.0; do
            [[ -f "$LIBDIR/$lib" ]] && continue
            src="$(ldconfig -p 2>/dev/null | grep -F "$lib" | grep -o "=> .*" | awk "{print \$2}" | head -1 || true)"
            if [[ -n "$src" && -f "$src" ]]; then
                cp -L "$src" "$LIBDIR/$lib"
                echo "  bundled $lib"
            fi
        done

        # Step 6: repack manually — avoids appimagetool FUSE requirement.
        # AppImage Type 2 = ELF runtime + squashfs concatenated.
        wget -q "https://github.com/AppImage/type2-runtime/releases/download/continuous/runtime-x86_64" \
            -O "$WORKDIR/runtime-x86_64"

        # Ubuntu 26.04 mksquashfs only supports zstd
        mksquashfs "$APPDIR" "$WORKDIR/app.squashfs" \
            -root-owned -noappend -no-xattrs \
            -comp zstd -Xcompression-level 19 >/dev/null

        OUT="/output/PipeWireController-${VERSION}-x86_64.AppImage"
        cat "$WORKDIR/runtime-x86_64" "$WORKDIR/app.squashfs" > "$OUT"
        chmod +x "$OUT"
        echo "  written: $(basename "$OUT")"
    '

if [ -f "$FINAL" ]; then
    echo "✓ $FINAL"
else
    echo "✗ AppImage not found in output"
    exit 1
fi
