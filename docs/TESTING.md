# Testing Guide

## Overview

This project uses **pytest** for testing the PipeWire engine logic. Tests run without GUI dependencies, making them fast and reliable.

## Architecture

The project uses a **logic-first architecture**:

- **PipewireEngine** (`engine.py`) - Pure logic, no GUI dependencies
- **TrayApplication** (`ui/tray.py`) - GUI that calls engine methods
- **Tests** - Test engine logic only, no GUI testing needed

## Test Structure

```
tests/
├── conftest.py           # Shared fixtures
├── test_pipewire.py      # Legacy PipeWire tests
├── test_hardware.py      # Legacy hardware tests
└── test_engine.py        # Engine logic tests (primary)
```

## Running Tests

### Local Testing

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov

# Run specific test file
pytest tests/test_engine.py

# Run specific test
pytest tests/test_engine.py::TestPipewireEngine::test_set_sample_rate_success
```

### Using Make

```bash
make test              # Run all tests
make test-cov          # With coverage report
```

## Test Categories

### Engine Tests (`test_engine.py`)

Tests PipeWire logic with mocked subprocess calls:

- ✅ Sample rate setting (success/failure/timeout)
- ✅ Buffer size setting (success/failure/timeout)
- ✅ Hardware detection via pw-dump
- ✅ JSON parsing (valid/invalid/empty)
- ✅ Rate extraction (direct values and ranges)
- ✅ Device filtering (audio devices only)
- ✅ Current settings queries
- ✅ Error handling and fallbacks

### Legacy Tests

- `test_pipewire.py` - Original PipeWire controller tests
- `test_hardware.py` - Original hardware detection tests

## Key Testing Features

### Mocked System Calls

All subprocess calls are mocked - no actual PipeWire needed:

```python
def test_set_sample_rate_success(mocker):
    mock_run = mocker.patch("subprocess.run")
    mock_run.return_value = Mock(returncode=0)
    
    engine = PipewireEngine()
    result = engine.set_sample_rate(48000)
    
    assert result is True
    mock_run.assert_called_once_with(
        ["pw-metadata", "-n", "settings", "0", "clock.force-rate", "48000"],
        check=True,
        capture_output=True,
        timeout=5
    )
```

### No GUI Dependencies

Tests run in standard terminal - no xvfb or Qt libraries needed!

## GitHub Actions CI/CD

The `.github/workflows/tests.yml` workflow:

1. **Installs Python dependencies** only
2. **Runs tests** with simple `pytest` command
3. **Tests multiple Python versions** (3.10, 3.11, 3.12)
4. **Uploads coverage** to Codecov
5. **Runs linting** (ruff, black)

No system dependencies required!

## Test Examples

### Testing Command Generation

```python
def test_set_sample_rate_success(mocker):
    """Verify correct pw-metadata command is generated."""
    mock_run = mocker.patch("subprocess.run")
    engine = PipewireEngine()
    engine.set_sample_rate(48000)
    
    mock_run.assert_called_with(
        ["pw-metadata", "-n", "settings", "0", "clock.force-rate", "48000"],
        check=True, capture_output=True, timeout=5
    )
```

### Testing JSON Parsing

```python
def test_get_supported_rates_with_devices(mocker):
    """Verify JSON parsing of hardware rates."""
    pw_dump_output = json.dumps([{
        "type": "PipeWire:Interface:Node",
        "info": {
            "props": {"media.class": "Audio/Sink"},
            "params": {"EnumFormat": [{"rate": 48000}, {"rate": 96000}]}
        }
    }])
    
    mock_run = mocker.patch("subprocess.run")
    mock_run.return_value = Mock(stdout=pw_dump_output, returncode=0)
    
    engine = PipewireEngine()
    rates = engine.get_supported_sample_rates()
    
    assert 48000 in rates
    assert 96000 in rates
```

### Testing Error Handling

```python
def test_set_sample_rate_failure(mocker):
    """Verify graceful handling of command failures."""
    mock_run = mocker.patch("subprocess.run")
    mock_run.side_effect = subprocess.CalledProcessError(1, "pw-metadata")
    
    engine = PipewireEngine()
    result = engine.set_sample_rate(48000)
    
    assert result is False
```

## Coverage Goals

- **Engine module**: 95%+ coverage
- **Core modules**: 90%+ coverage
- **Overall**: 85%+ coverage

## Troubleshooting

### Import errors in tests

Ensure package is installed:

```bash
pip install -e ".[dev]"
```

Or use PYTHONPATH:

```bash
PYTHONPATH=src pytest
```

### Module not found

Install test dependencies:

```bash
pip install pytest pytest-mock pytest-cov
```

## Best Practices

1. **Always mock subprocess calls** - Never call actual PipeWire commands
2. **Test both success and failure paths** - Include error handling tests
3. **Keep tests isolated** - Each test should be independent
4. **Use descriptive test names** - Clearly state what is being tested
5. **Test the engine, not the UI** - UI just calls engine methods

## Continuous Integration

The GitHub Actions workflow automatically:

- ✅ Runs on every push and PR
- ✅ Tests Python 3.10, 3.11, 3.12
- ✅ Runs in standard environment (no xvfb needed)
- ✅ Generates coverage reports
- ✅ Checks code formatting
- ✅ Runs linting

View results at: `https://github.com/YOUR_USERNAME/pipewire-controller/actions`

## Why No GUI Testing?

The UI layer is thin - it just calls engine methods. By testing the engine thoroughly, we ensure the logic is correct. The UI is simple enough that manual testing suffices.

**Benefits:**

- ✅ Fast tests (no GUI initialization)
- ✅ No segfaults or Qt issues
- ✅ Simple CI/CD (no system dependencies)
- ✅ Easy to debug
- ✅ Runs anywhere
