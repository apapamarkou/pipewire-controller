# Contributing to PipeWire Controller

Thank you for considering contributing to PipeWire Controller! This document provides guidelines and instructions for contributing.

## Code of Conduct

- Be respectful and inclusive
- Focus on constructive feedback
- Help others learn and grow

## How to Contribute

### Reporting Bugs

1. Check if the bug is already reported in [Issues](https://github.com/apapamarkou/pipewire-controller/issues)
2. Use the bug report template
3. Include:
   - OS and desktop environment
   - Python version (`python --version`)
   - PipeWire version (`pw-cli --version`)
   - Steps to reproduce
   - Expected vs actual behavior
   - Relevant logs

### Suggesting Features

1. Check existing feature requests
2. Open a new issue with `[Feature Request]` prefix
3. Describe:
   - Use case and motivation
   - Proposed solution
   - Alternative approaches considered

### Pull Requests

#### Setup Development Environment

```bash
# Fork and clone
git clone https://github.com/YOUR_USERNAME/pipewire-controller.git
cd pipewire-controller

# Create virtual environment
python -m venv venv
source venv/bin/activate  # or `venv\Scripts\activate` on Windows

# Install in development mode
pip install -e ".[dev]"
```

#### Development Workflow

1. **Create a branch**
   ```bash
   git checkout -b feature/your-feature-name
   ```

2. **Make changes**
   - Write code following style guidelines
   - Add tests for new functionality
   - Update documentation

3. **Run tests**
   ```bash
   pytest
   pytest --cov=src/pipewire_controller
   ```

4. **Format code**
   ```bash
   black src/ tests/
   ruff check src/ tests/
   ```

5. **Commit changes**
   ```bash
   git add .
   git commit -m "feat: add hardware detection for USB DACs"
   ```

6. **Push and create PR**
   ```bash
   git push origin feature/your-feature-name
   ```

#### Commit Message Convention

Follow [Conventional Commits](https://www.conventionalcommits.org/):

- `feat:` New feature
- `fix:` Bug fix
- `docs:` Documentation changes
- `test:` Test additions/changes
- `refactor:` Code refactoring
- `style:` Formatting changes
- `chore:` Maintenance tasks

Examples:
```
feat: add support for 384kHz sample rates
fix: handle missing pw-dump gracefully
docs: update installation instructions for Fedora
test: add tests for hardware detection
```

## Code Style

### Python Style Guide

- Follow [PEP 8](https://pep8.org/)
- Use [Black](https://black.readthedocs.io/) for formatting (line length: 100)
- Use [Ruff](https://docs.astral.sh/ruff/) for linting
- Write docstrings for public APIs (Google style)

### Example

```python
"""Module for hardware detection."""

from typing import List, Optional


class HardwareDetector:
    """Detects audio hardware capabilities.
    
    This class queries PipeWire to determine supported sample rates
    and buffer sizes for connected audio devices.
    """
    
    def get_supported_rates(self) -> List[int]:
        """Get list of supported sample rates.
        
        Returns:
            Sorted list of sample rates in Hz.
            
        Raises:
            PipeWireError: If PipeWire is not running.
        """
        pass
```

### Type Hints

Use type hints for function signatures:

```python
def set_sample_rate(rate: int) -> bool:
    """Set sample rate."""
    pass

def get_devices() -> List[Dict[str, Any]]:
    """Get device list."""
    pass
```

## Testing

### Writing Tests

- Place tests in `tests/` directory
- Name test files `test_*.py`
- Use descriptive test names
- Mock external dependencies (subprocess, file I/O)

### Example Test

```python
import pytest
from unittest.mock import Mock
from pipewire_controller.core.pipewire import PipeWireController


def test_set_sample_rate_success(mock_subprocess_run):
    """Test successful sample rate change."""
    mock_subprocess_run.return_value = Mock(returncode=0)
    
    result = PipeWireController.set_sample_rate(48000)
    
    assert result is True
    mock_subprocess_run.assert_called_once()
```

### Running Tests

```bash
# All tests
pytest

# Specific file
pytest tests/test_pipewire.py

# Specific test
pytest tests/test_pipewire.py::test_set_sample_rate_success

# With coverage
pytest --cov=src/pipewire_controller --cov-report=html
```

## Documentation

### Docstrings

Use Google-style docstrings:

```python
def complex_function(param1: str, param2: int = 0) -> bool:
    """Short description.
    
    Longer description explaining the function's purpose,
    behavior, and any important details.
    
    Args:
        param1: Description of param1.
        param2: Description of param2. Defaults to 0.
        
    Returns:
        True if successful, False otherwise.
        
    Raises:
        ValueError: If param1 is empty.
        RuntimeError: If operation fails.
        
    Example:
        >>> complex_function("test", 42)
        True
    """
    pass
```

### README Updates

Update README.md when adding:
- New features
- New dependencies
- New configuration options
- Breaking changes

## Project Structure

```
pipewire-controller/
├── src/pipewire_controller/
│   ├── __init__.py          # Package metadata
│   ├── __main__.py          # Entry point
│   ├── core/                # Core functionality
│   │   ├── pipewire.py      # PipeWire interface
│   │   └── hardware.py      # Hardware detection
│   ├── ui/                  # User interface
│   │   ├── tray.py          # System tray
│   │   └── dialogs.py       # Dialogs
│   └── utils/               # Utilities
│       ├── config.py        # Configuration
│       └── process.py       # Process management
├── tests/                   # Test suite
├── pyproject.toml           # Package config
└── README.md
```

## Review Process

1. **Automated Checks**: CI runs tests and linting
2. **Code Review**: Maintainer reviews code
3. **Discussion**: Address feedback and questions
4. **Approval**: Maintainer approves and merges

## Getting Help

- **Questions**: Open a [Discussion](https://github.com/apapamarkou/pipewire-controller/discussions)
- **Bugs**: Open an [Issue](https://github.com/apapamarkou/pipewire-controller/issues)
- **Chat**: Join our community (link TBD)

## Recognition

Contributors are recognized in:
- README.md acknowledgments
- Release notes
- Git commit history

Thank you for contributing! 🎉
