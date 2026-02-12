# PipeWire Controller

[![License: GPL v3](https://img.shields.io/badge/License-GPLv3-blue.svg)](https://www.gnu.org/licenses/gpl-3.0)
[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![PyQt6](https://img.shields.io/badge/PyQt-6-green.svg)](https://www.riverbankcomputing.com/software/pyqt/)

A modern, production-ready system tray application for controlling PipeWire audio server settings on Linux.

![PipeWire Controller Screenshot](https://github.com/apapamarkou/pipewire_controller/assets/42995877/32536db2-a461-4078-896c-573e77dd7092)

## Features

- 🎛️ **Dynamic Sample Rate Control** - Automatically detects hardware-supported sample rates
- 🔧 **Buffer Size Management** - Adjust quantum/buffer size for latency optimization
- 💾 **Persistent Settings** - Automatically saves and restores your preferences
- 🖥️ **Desktop Integration** - System tray icon compatible with Wayland and X11
- 🔍 **Hardware Detection** - Queries connected DACs for supported capabilities
- 🧪 **Fully Tested** - Comprehensive test suite with pytest
- 📦 **Modern Packaging** - Standard Python package with pyproject.toml

## Requirements

- **Python**: 3.10 or higher
- **PipeWire**: Audio server with `pw-metadata`, `pw-dump`, and `wpctl` utilities
- **PyQt6**: Qt6 bindings for Python
- **Linux**: Any distribution with system tray support

## Installation

### From PyPI (Recommended)

```bash
pip install pipewire-controller
```

### From Source

```bash
git clone https://github.com/apapamarkou/pipewire-controller.git
cd pipewire-controller
pip install .
```

### Development Installation

```bash
git clone https://github.com/apapamarkou/pipewire-controller.git
cd pipewire-controller
pip install -e ".[dev]"
```

### Distribution-Specific Dependencies

**Arch Linux / Manjaro / Garuda:**
```bash
sudo pacman -S python-pyqt6 pipewire wireplumber
```

**Fedora / RHEL:**
```bash
sudo dnf install python3-pyqt6 pipewire pipewire-utils
```

**Debian / Ubuntu / Mint:**
```bash
sudo apt install python3-pyqt6 pipewire pipewire-bin wireplumber
```

**openSUSE:**
```bash
sudo zypper install python3-qt6 pipewire pipewire-tools
```

## Usage

### Running the Application

After installation, simply run:

```bash
pipewire-controller
```

Or as a Python module:

```bash
python -m pipewire_controller
```

### Autostart

To start automatically on login, create a desktop entry:

```bash
mkdir -p ~/.config/autostart
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

### Configuration

Settings are stored in `~/.config/pipewire-controller/settings.json`:

```json
{
  "samplerate": 48000,
  "buffer_size": 512
}
```

## Development

### Project Structure

```
pipewire-controller/
├── src/pipewire_controller/
│   ├── core/              # PipeWire interaction & hardware detection
│   ├── ui/                # PyQt6 interface components
│   └── utils/             # Configuration & process management
├── tests/                 # Pytest test suite
├── pyproject.toml         # Package configuration
└── README.md
```

### Running Tests

```bash
# Install development dependencies
pip install -e ".[dev]"

# Run tests
pytest

# Run with coverage
pytest --cov=src/pipewire_controller --cov-report=html
```

### Code Quality

```bash
# Format code
black src/ tests/

# Lint code
ruff check src/ tests/
```

## How It Works

1. **Hardware Detection**: Queries PipeWire via `pw-dump` to detect connected audio devices and their supported sample rates
2. **Dynamic UI**: Populates the system tray menu with only hardware-supported rates
3. **Settings Application**: Uses `pw-metadata` to apply sample rate and buffer size changes
4. **Persistence**: Saves settings to JSON and reapplies on startup

## Troubleshooting

### Tray Icon Not Showing

Ensure your desktop environment supports system tray icons:
- **GNOME**: Install `gnome-shell-extension-appindicator`
- **KDE Plasma**: Built-in support
- **i3/Sway**: Use `waybar` or `i3status`

### PipeWire Commands Not Found

Install PipeWire utilities:
```bash
# Check if installed
which pw-metadata pw-dump wpctl

# Install if missing (Arch example)
sudo pacman -S pipewire wireplumber
```

### Settings Not Persisting

Check permissions on config directory:
```bash
ls -la ~/.config/pipewire-controller/
```

## Contributing

Contributions are welcome! Please follow these guidelines:

1. **Fork** the repository
2. **Create** a feature branch (`git checkout -b feature/amazing-feature`)
3. **Write** tests for new functionality
4. **Ensure** tests pass (`pytest`)
5. **Format** code (`black src/ tests/`)
6. **Commit** changes (`git commit -m 'Add amazing feature'`)
7. **Push** to branch (`git push origin feature/amazing-feature`)
8. **Open** a Pull Request

### Code Style

- Follow PEP 8
- Use type hints where appropriate
- Write docstrings for public APIs
- Keep functions focused and testable

## Acknowledgments

Special thanks to:
- **[@ItzSelenux](https://github.com/ItzSelenux)** - Contributions and testing
- **[@Axel-Erfurt](https://github.com/Axel-Erfurt)** - UI improvements
- **PipeWire Team** - For the excellent audio server

## License

This project is licensed under the GNU General Public License v3.0 - see the [LICENSE](LICENSE) file for details.

## Support

- **Issues**: [GitHub Issues](https://github.com/apapamarkou/pipewire-controller/issues)
- **Discussions**: [GitHub Discussions](https://github.com/apapamarkou/pipewire-controller/discussions)

---

**Author**: Andrianos Papamarkou  
**Repository**: https://github.com/apapamarkou/pipewire-controller
