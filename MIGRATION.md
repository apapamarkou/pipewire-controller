# Migration Guide: v1.0 → v2.0

## Overview

Version 2.0 is a complete rewrite with modern Python packaging, PyQt6, and hardware detection. This guide helps you migrate from the old script-based version.

## Key Changes

### 1. **PyQt5 → PyQt6**
- All Qt imports updated to PyQt6
- Signal/slot syntax modernized
- Enum access updated (e.g., `Qt.AlignCenter` → `Qt.AlignmentFlag.AlignCenter`)

### 2. **Package Structure**
```
OLD: Single script (pipewire-controller.py)
NEW: Proper Python package (src/pipewire_controller/)
```

### 3. **Installation Method**
```bash
# OLD
wget -qO- https://raw.githubusercontent.com/.../pipewire-controller-git-install | bash

# NEW
pip install pipewire-controller
# or
pip install .
```

### 4. **Configuration Location**
```
OLD: ~/.config/pipewire-controller/pipewire-controller.settings
NEW: ~/.config/pipewire-controller/settings.json
```

Settings are automatically migrated on first run.

### 5. **New Features**
- ✅ Hardware-aware sample rate detection
- ✅ Comprehensive test suite
- ✅ Better error handling
- ✅ Modern packaging with pyproject.toml

## Migration Steps

### Step 1: Uninstall Old Version

```bash
# If installed via script
wget -qO- https://raw.githubusercontent.com/apapamarkou/pipewire-controller/main/src/pipewire-controller-git-uninstall | bash

# Or manually
rm ~/.local/bin/pipewire-controller
rm ~/.local/share/applications/pipewire-controller.desktop
rm ~/.local/share/icons/pipewire-controller.py.png
```

### Step 2: Install Dependencies

```bash
# Arch/Manjaro
sudo pacman -S python-pyqt6 pipewire

# Fedora
sudo dnf install python3-pyqt6 pipewire

# Ubuntu/Debian
sudo apt install python3-pyqt6 pipewire-bin
```

### Step 3: Install v2.0

```bash
# From source
git clone https://github.com/apapamarkou/pipewire-controller.git
cd pipewire-controller
pip install .

# Or from PyPI (when published)
pip install pipewire-controller
```

### Step 4: Verify Installation

```bash
pipewire-controller --version
pipewire-controller
```

### Step 5: Update Autostart (if used)

```bash
# Update desktop entry
cat > ~/.config/autostart/pipewire-controller.desktop << EOF
[Desktop Entry]
Type=Application
Name=PipeWire Controller
Exec=pipewire-controller
Icon=audio-card
Terminal=false
Categories=AudioVideo;Audio;
EOF
```

## Configuration Migration

Your old settings will be automatically detected and migrated. If you need to manually migrate:

```bash
# Old format
cat ~/.config/pipewire-controller/pipewire-controller.settings
{"samplerate": 48000, "buffer_size": 512}

# New format (same structure, different filename)
cat ~/.config/pipewire-controller/settings.json
{
  "samplerate": 48000,
  "buffer_size": 512
}
```

## API Changes (for developers)

### Old Code (v1.0)
```python
from PyQt5.QtWidgets import QApplication
from PyQt5.QtCore import Qt

# Direct script execution
if __name__ == "__main__":
    app = TrayIconApp(sys.argv)
    sys.exit(app.exec_())
```

### New Code (v2.0)
```python
from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import Qt
from pipewire_controller.ui.tray import run

# Package entry point
if __name__ == "__main__":
    run()
```

## Troubleshooting

### Issue: "No module named 'PyQt6'"
```bash
pip install PyQt6
```

### Issue: "Command 'pipewire-controller' not found"
```bash
# Ensure pip bin directory is in PATH
export PATH="$HOME/.local/bin:$PATH"

# Or use module syntax
python -m pipewire_controller
```

### Issue: Settings not loading
```bash
# Check config directory
ls -la ~/.config/pipewire-controller/

# Manually create if needed
mkdir -p ~/.config/pipewire-controller
echo '{"samplerate": 48000, "buffer_size": 512}' > ~/.config/pipewire-controller/settings.json
```

## Rollback (if needed)

If you need to revert to v1.0:

```bash
# Uninstall v2.0
pip uninstall pipewire-controller

# Reinstall v1.0
QT_PLATFORM=5 wget -qO- https://raw.githubusercontent.com/apapamarkou/pipewire-controller/v1.0/src/pipewire-controller-git-install | bash
```

## Questions?

Open an issue: https://github.com/apapamarkou/pipewire-controller/issues
