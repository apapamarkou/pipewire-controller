# Testing Guide

## Overview

This project uses **pytest** with **pytest-qt** for comprehensive testing, including headless GUI testing suitable for CI/CD environments.

## Test Structure

```
tests/
├── conftest.py           # Shared fixtures and Qt configuration
├── test_pipewire.py      # PipeWire controller tests (mocked)
├── test_hardware.py      # Hardware detection tests (mocked)
└── test_ui.py            # UI/GUI tests with pytest-qt (NEW)
```

## Running Tests

### Local Testing (with display)

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov

# Run specific test file
pytest tests/test_ui.py

# Run specific test
pytest tests/test_ui.py::TestTrayApplicationUI::test_menu_populated_with_hardware_rates
```

### Headless Testing (no display)

```bash
# Using xvfb (recommended for CI)
xvfb-run -a pytest

# Using Qt offscreen platform
QT_QPA_PLATFORM=offscreen pytest

# Using provided script
./run-tests-headless.sh
```

## Test Categories

### 1. Core Functionality Tests (`test_pipewire.py`, `test_hardware.py`)

Tests PipeWire interaction and hardware detection with mocked subprocess calls:

- ✅ Sample rate changes
- ✅ Buffer size changes
- ✅ Hardware detection via pw-dump
- ✅ Error handling (timeouts, failures)

### 2. UI/GUI Tests (`test_ui.py`)

Tests PyQt6 interface with pytest-qt:

- ✅ Menu population with hardware rates
- ✅ Click actions trigger correct commands
- ✅ Settings persistence
- ✅ Error handling in UI
- ✅ Tooltip updates
- ✅ Dialog opening

## Key Testing Features

### Mocked System Calls

All subprocess calls are mocked to avoid requiring actual PipeWire:

```python
@pytest.fixture
def mock_subprocess(mocker, mock_pw_dump_json):
    """Mock all subprocess calls."""
    mock_run = mocker.patch("subprocess.run")
    
    def subprocess_side_effect(cmd, **kwargs):
        if "pw-dump" in cmd:
            return Mock(stdout=mock_pw_dump_json, returncode=0)
        elif "pw-metadata" in cmd:
            return Mock(stdout="", returncode=0)
        return Mock(stdout="", returncode=0)
    
    mock_run.side_effect = subprocess_side_effect
    return mock_run
```

### Headless GUI Testing

Tests run without a display using Qt's offscreen platform:

```python
# In conftest.py
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
```

### pytest-qt Integration

Uses `qtbot` fixture for GUI interaction:

```python
def test_clicking_rate_triggers_pw_metadata(app, mock_subprocess, qtbot):
    """Test that clicking a rate triggers correct pw-metadata command."""
    # Find menu action
    target_action = find_action(app, "96000 Hz")
    
    # Trigger action
    target_action.trigger()
    qtbot.wait(100)
    
    # Verify command was called
    assert "96000" in mock_subprocess.call_args_list[-1][0][0]
```

## GitHub Actions CI/CD

The `.github/workflows/tests.yml` workflow:

1. **Installs system dependencies** (xvfb, Qt6 libraries)
2. **Runs tests in headless mode** with xvfb-run
3. **Tests multiple Python versions** (3.10, 3.11, 3.12)
4. **Uploads coverage** to Codecov
5. **Runs linting** (ruff, black)

### Required System Dependencies

For headless testing on Ubuntu/Debian:

```bash
sudo apt-get install -y \
  xvfb \
  libxcb-xinerama0 \
  libxcb-icccm4 \
  libxcb-image0 \
  libxcb-keysyms1 \
  libxcb-randr0 \
  libxcb-render-util0 \
  libxcb-shape0 \
  libxcb-xfixes0 \
  libxcb-xkb1 \
  libxkbcommon-x11-0 \
  libxkbcommon0 \
  libdbus-1-3 \
  libegl1 \
  libfontconfig1 \
  libglib2.0-0 \
  libgl1
```

## Test Examples

### Testing Menu Population

```python
def test_menu_populated_with_hardware_rates(app, mock_subprocess):
    """Test that menu shows only hardware-supported sample rates."""
    menu = app.tray_icon.contextMenu()
    
    # Find sample rate submenu
    rate_menu = find_submenu(menu, "Sample Rate")
    rate_texts = [action.text() for action in rate_menu.actions()]
    
    # Should contain hardware-supported rates
    assert "48000 Hz" in rate_texts
    assert "96000 Hz" in rate_texts
```

### Testing Click Actions

```python
def test_clicking_rate_triggers_pw_metadata(app, mock_subprocess, qtbot):
    """Test that clicking a rate triggers correct pw-metadata command."""
    action = find_action(app, "96000 Hz")
    action.trigger()
    qtbot.wait(100)
    
    # Verify pw-metadata was called
    calls = [c for c in mock_subprocess.call_args_list 
             if "pw-metadata" in c[0][0]]
    assert "96000" in calls[-1][0][0]
```

### Testing Error Handling

```python
def test_pw_metadata_failure_handled_gracefully(qtbot, mocker):
    """Test that non-zero exit code from pw-metadata is handled."""
    mock_run = mocker.patch("subprocess.run")
    mock_run.side_effect = CalledProcessError(1, "pw-metadata")
    
    app = TrayApplication([])
    initial_rate = app.settings["samplerate"]
    app._change_sample_rate(96000)
    
    # Settings should not change on failure
    assert app.settings["samplerate"] == initial_rate
```

## Coverage Goals

- **Core modules**: 90%+ coverage
- **UI modules**: 80%+ coverage
- **Overall**: 85%+ coverage

## Troubleshooting

### Tests fail with "cannot connect to X server"

Use headless mode:
```bash
QT_QPA_PLATFORM=offscreen pytest
```

### Tests hang or timeout

Increase timeout in qtbot.wait():
```python
qtbot.wait(500)  # Wait 500ms instead of 100ms
```

### Import errors in tests

Ensure package is installed:
```bash
pip install -e ".[dev]"
```

Or use PYTHONPATH:
```bash
PYTHONPATH=src pytest
```

### Qt platform plugin errors

Install required Qt libraries:
```bash
# Arch
sudo pacman -S qt6-base

# Ubuntu/Debian
sudo apt install libqt6gui6
```

## Best Practices

1. **Always mock subprocess calls** - Never call actual PipeWire commands
2. **Use qtbot.wait()** - Allow time for Qt event processing
3. **Test both success and failure paths** - Include error handling tests
4. **Keep tests isolated** - Each test should be independent
5. **Use descriptive test names** - Clearly state what is being tested

## Running in Docker

```dockerfile
FROM python:3.11-slim

RUN apt-get update && apt-get install -y \
    xvfb libxcb-xinerama0 libxkbcommon-x11-0 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY . .
RUN pip install -e ".[dev]"

CMD ["xvfb-run", "-a", "pytest"]
```

## Continuous Integration

The GitHub Actions workflow automatically:

- ✅ Runs on every push and PR
- ✅ Tests Python 3.10, 3.11, 3.12
- ✅ Runs in headless mode with xvfb
- ✅ Generates coverage reports
- ✅ Checks code formatting
- ✅ Runs linting

View results at: `https://github.com/YOUR_USERNAME/pipewire-controller/actions`
