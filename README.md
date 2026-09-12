# PipeWire Audio Control Center

[![CI](https://img.shields.io/github/actions/workflow/status/apapamarkou/pipewire-controller/ci.yml?style=for-the-badge&label=CI)](https://github.com/apapamarkou/pipewire-controller/actions)
[![License](https://img.shields.io/github/license/apapamarkou/pipewire-controller?style=for-the-badge)](LICENSE)
[![Python](https://img.shields.io/badge/Python-3.10%2B-blue?style=for-the-badge)](https://python.org)

A professional Linux desktop application for controlling and monitoring PipeWire,
designed specifically for DAW and audio-production workflows.

---

## Features

- **System tray application** — always accessible, minimal footprint
- **Docked / floating panel** — dock to screen edge or float freely
- **Device / I/O management** — discover inputs and outputs, set defaults, control volume and mute
- **Sample rate control** — Force or Auto mode with `clock.force-rate`
- **Quantum / buffer control** — Force or Auto mode with `clock.force-quantum`
- **Native rate detection** — shows ✓ Native / ⚠ Resampling / ? Unknown per device
- **Latency display** — configured period, estimated graph latency, measured RTL
- **Latency measurement** — cross-correlation-based software round-trip measurement
- **Input / output meters** — Peak and RMS with peak hold, over detection, clear
- **Master / surround meter** — Mono, Stereo, 2.1, Quadro, 5.1, 7.1, Custom
- **LUFS metering** — LUFS-M, LUFS-S, LUFS-I per ITU-R BS.1770-4
- **Named configurations** — save, load, edit, delete presets
- **Friendly names** — user-visible device and channel renaming
- **Dark studio UI** — professional compact audio-oriented appearance
- **Keyboard shortcuts** — Ctrl+Shift+P to show/hide panel

---

## Requirements

| Component | Minimum |
|-----------|---------|
| Python | 3.10 |
| PyQt6 | 6.4 |
| numpy | 1.24 |
| PipeWire | Any recent version with `pw-metadata`, `pw-dump` |
| WirePlumber | Recommended for device management |
| Linux | Any distribution with system tray support |

---

## Installation

### One-command install

```bash
wget -qO /tmp/install.sh https://raw.githubusercontent.com/apapamarkou/pipewire-controller/main/install
bash /tmp/install.sh
```

Automatically detects your distribution and installs dependencies.

### From tarball

Download the latest `pipewire-controller-*-linux.tar.gz` from Releases, then:

```bash
tar -xzf pipewire-controller-*-linux.tar.gz
cd pipewire-controller-*-linux
bash install
```

### From source

```bash
git clone https://github.com/apapamarkou/pipewire-controller.git
cd pipewire-controller
pip install .
```

### Development

```bash
git clone https://github.com/apapamarkou/pipewire-controller.git
cd pipewire-controller
pip install -e ".[dev]"
```

---

## Distribution-specific dependencies

**Arch Linux / Manjaro:**
```bash
sudo pacman -S python-pyqt6 python-numpy pipewire wireplumber
```

**Fedora / RHEL:**
```bash
sudo dnf install python3-pyqt6 python3-numpy pipewire pipewire-utils wireplumber
```

**Debian / Ubuntu:**
```bash
sudo apt install python3-pyqt6 python3-numpy pipewire pipewire-bin wireplumber
```

**openSUSE Tumbleweed:**
```bash
sudo zypper install python3-qt6 python3-numpy pipewire pipewire-tools wireplumber
```

---

## Uninstall

```bash
bash uninstall          # remove application
bash uninstall --wipe   # also remove configuration
```

---

## Running

```bash
pipewire-controller          # from PATH after installation
python -m pipewire_controller  # from source
make run                     # development
```

---

## Configuration

Settings are stored in `~/.config/pipewire-controller/config.json`.

Named configurations (presets) can be saved, loaded, edited and deleted
from the Configuration section in the panel.

Each preset stores:
- Sample rate and quantum settings
- Force/Auto state
- Panel geometry and accordion state
- Device friendly names and channel names
- Meter settings and master channel mapping

---

## Latency — important concepts

### Processing period

```
period = quantum / sample_rate
```

For example: 1024 frames at 48000 Hz = **21.33 ms**

This is the **processing period** — the time between audio processing callbacks.
It is **not** the total round-trip latency.

### Graph latency

The estimated graph latency includes the processing period plus any additional
buffering in the PipeWire graph. It depends on the number of processing nodes
in the signal path.

### Software round-trip latency (RTL)

The time from audio output to audio input through the software graph.
Measured by the latency wizard using cross-correlation of a test signal.

### Hardware round-trip latency

The time from DAC output through physical cables to ADC input.
Requires a hardware loopback connection (output → input).
Includes analog signal path, converter latency, and cable delay.

**`quantum / sample_rate` is NOT the total round-trip latency.**

---

## Sample rate support indicators

| Symbol | Meaning |
|--------|---------|
| ✓ Native | The device natively supports the current graph rate |
| ⚠ Resampling | PipeWire will resample — quality may be affected |
| ? Unknown | Cannot determine native rate support |

"Not advertised as native" does not mean "cannot operate" — PipeWire can
resample for most devices. The indicator shows whether resampling is occurring.

---

## Device / channel renaming

Friendly names are stored in the application configuration and displayed
in the panel. Where supported, `node.nick` is set via `pw-metadata` so
PipeWire-aware applications also see the friendly name.

**Limitations:**
- ALSA applications that access hardware directly will still see original names
- Not all applications respect `node.nick`
- `node.name` (the stable technical identifier) is never modified

---

## Keyboard shortcuts

| Shortcut | Action |
|----------|--------|
| Ctrl+Shift+P | Show / hide panel |
| Escape | Hide panel |

For global shortcuts (accessible from any application), configure your
desktop environment or window manager to run:
```bash
pipewire-controller --toggle
```

---

## Troubleshooting

### Tray icon not showing

- **GNOME**: Install `gnome-shell-extension-appindicator`
- **KDE Plasma**: Built-in support
- **i3/Sway**: Use `waybar` or `i3status` with tray support

### PipeWire commands not found

```bash
which pw-metadata pw-dump wpctl
sudo pacman -S pipewire wireplumber  # Arch example
```

### Settings not persisting

```bash
ls -la ~/.config/pipewire-controller/
```

### Application shows "PipeWire unavailable"

Check that PipeWire is running:
```bash
systemctl --user status pipewire
systemctl --user status wireplumber
```

---

## Development

### Project structure

```
pipewire-controller/
├── src/pipewire_controller/
│   ├── __init__.py          # version
│   ├── __main__.py          # entry point
│   ├── config.py            # named presets, persistence
│   ├── controller.py        # application controller (wires PW ↔ UI)
│   ├── detection.py         # PipeWire/WirePlumber/JACK detection
│   ├── friendly_names.py    # device/channel renaming
│   ├── latency.py           # signal analysis (chirp, cross-correlation)
│   ├── log.py               # structured logging
│   ├── metering.py          # Peak/RMS/LUFS analysis engine
│   ├── shortcuts.py         # keyboard shortcut abstraction
│   ├── pipewire/
│   │   ├── model.py         # AudioNode, GraphSettings, PipeWireGraph
│   │   └── pw_client.py     # pw-dump/pw-metadata/wpctl interface
│   └── ui/
│       ├── accordion.py     # collapsible section widget
│       ├── dialogs.py       # About, SystemInfo, ConfigManager, LatencyWizard
│       ├── panel.py         # ControlPanel (docked/floating)
│       ├── theme.py         # dark studio color constants + stylesheets
│       ├── components/
│       │   ├── flat_button.py
│       │   └── meter_bar.py # vertical dBFS meter bar
│       └── sections/
│           ├── devices.py       # Devices / I/O section
│           ├── samplerate.py    # Sample Rate / Quantum section
│           ├── latency.py       # Latency section
│           ├── meters.py        # Input/Output meter sections
│           ├── master_meter.py  # Master/Surround meter section
│           └── config_section.py # Configuration section
├── tests/                   # pytest test suite
├── packaging/
│   ├── scripts/
│   │   ├── build-tarball.sh
│   │   └── test-tarball.sh
│   └── specs/
│       └── pipewire-controller.desktop
├── resources/icons/
├── .github/workflows/ci.yml
├── install
├── uninstall
├── Makefile
└── pyproject.toml
```

### Architecture

```
UI (Qt widgets)
    ↓ signals
AppController
    ↓ calls
PipeWire services (pw_client.py)
    ↓ subprocess
pw-dump / pw-metadata / wpctl

Audio analysis (metering.py, latency.py)
    ↓ numpy arrays
ChannelMeter / LUFSMeter / LatencyMeasurement
    ↓ snapshots
UI meter widgets
```

The UI thread never performs blocking PipeWire or audio-analysis operations.

### Running tests

```bash
make test           # run test suite
make lint           # check code style
make lint-fix       # auto-fix code style
```

### Building a package

```bash
make package        # build tar.gz
make package-test   # test the package (no Docker required)
```

---

## License

GNU General Public License v3.0 — see [LICENSE](LICENSE).

## Author

Andrianos Papamarkou — [GitHub](https://github.com/apapamarkou/pipewire-controller)
