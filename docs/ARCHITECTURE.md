# Architecture - Logic-First Design

## Overview

PipeWire Controller uses a **logic-first architecture** that separates business logic from UI, enabling reliable testing and maintainability.

## Design Principles

1. **Separation of Concerns** - Logic and UI are completely decoupled
2. **Testability** - Engine has zero GUI dependencies, fully testable
3. **Simplicity** - UI is thin, just calls engine methods
4. **Reliability** - No segfaults, no Qt issues in tests

## Component Architecture

```
┌─────────────────────────────────────────────────────────┐
│                    UI Layer (PyQt6)                     │
│                  TrayApplication                        │
│  - Menu rendering                                       │
│  - User interaction                                     │
│  - Settings display                                     │
└────────────┬────────────────────────────────────────────┘
             │
             │ Calls methods
             │
             ▼
┌─────────────────────────────────────────────────────────┐
│                  Logic Layer (Pure Python)              │
│                   PipewireEngine                        │
│                                                         │
│  - set_sample_rate(rate)                               │
│  - set_buffer_size(size)                               │
│  - get_supported_sample_rates()                        │
│  - get_current_rate()                                  │
│  - get_current_quantum()                               │
│  - get_device_info()                                   │
└────────────┬────────────────────────────────────────────┘
             │
             │ Executes commands
             │
             ▼
┌─────────────────────────────────────────────────────────┐
│              PipeWire CLI Tools                         │
│  pw-metadata  |  pw-dump  |  wpctl                     │
└─────────────────────────────────────────────────────────┘
```

## Key Components

### PipewireEngine (`engine.py`)

**Pure logic class with NO GUI dependencies.**

```python
class PipewireEngine:
    def set_sample_rate(self, rate: int) -> bool:
        """Set sample rate via pw-metadata."""
        
    def get_supported_sample_rates(self) -> List[int]:
        """Query hardware via pw-dump."""
```

**Responsibilities:**
- Execute PipeWire commands
- Parse JSON from pw-dump
- Handle errors and timeouts
- Provide fallback values

**No imports from:** PyQt6, Qt, GUI libraries

### TrayApplication (`ui/tray.py`)

**Thin UI layer that delegates to engine.**

```python
class TrayApplication(QApplication):
    def __init__(self, argv):
        super().__init__(argv)
        self.engine = PipewireEngine()  # Use engine
        
    def _change_sample_rate(self, rate: int):
        if self.engine.set_sample_rate(rate):  # Delegate to engine
            self.settings["samplerate"] = rate
            self._update_menu()
```

**Responsibilities:**
- Display system tray icon
- Render menus
- Handle user clicks
- Update UI state

**Does NOT:**
- Execute subprocess commands
- Parse PipeWire output
- Contain business logic

## Data Flow

### User Changes Sample Rate

```
1. User clicks "96000 Hz" in menu
2. TrayApplication._change_sample_rate(96000)
3. engine.set_sample_rate(96000)
4. subprocess.run(["pw-metadata", ...])
5. Return success/failure to UI
6. UI updates menu and saves settings
```

### Application Startup

```
1. TrayApplication.__init__()
2. engine = PipewireEngine()
3. rates = engine.get_supported_sample_rates()
4. subprocess.run(["pw-dump"])
5. Parse JSON, extract rates
6. UI creates menu with detected rates
7. engine.set_sample_rate(saved_rate)
8. Apply saved settings
```

## Testing Strategy

### Engine Tests (Primary)

Test pure logic without GUI:

```python
def test_set_sample_rate(mocker):
    mock_run = mocker.patch("subprocess.run")
    engine = PipewireEngine()
    result = engine.set_sample_rate(48000)
    
    assert result is True
    mock_run.assert_called_with([...])
```

**Benefits:**
- Fast (no GUI initialization)
- Reliable (no Qt issues)
- Simple (standard pytest)
- Portable (runs anywhere)

### UI Testing (Manual)

UI is thin enough for manual testing:
- Click menu items
- Verify settings persist
- Check tooltip updates

## Error Handling

### Engine Layer

```python
def set_sample_rate(self, rate: int) -> bool:
    try:
        subprocess.run([...], timeout=5)
        return True
    except (CalledProcessError, TimeoutExpired):
        return False  # Graceful failure
```

### UI Layer

```python
def _change_sample_rate(self, rate: int):
    if self.engine.set_sample_rate(rate):
        # Success - update UI
        self.settings["samplerate"] = rate
    else:
        # Failure - UI stays unchanged
        pass
```

## Benefits of This Architecture

### 1. Testability
- Engine fully testable without GUI
- No segfaults or Qt issues
- Fast test execution

### 2. Maintainability
- Clear separation of concerns
- Easy to understand
- Simple to modify

### 3. Reliability
- Logic tested independently
- UI is thin and simple
- Fewer bugs

### 4. Portability
- Engine can be used in CLI tools
- Logic reusable in other projects
- No GUI lock-in

## Migration from Old Architecture

### Before (Tightly Coupled)

```python
class TrayApplication(QApplication):
    def _change_sample_rate(self, rate):
        # Direct subprocess call in UI
        subprocess.run(["pw-metadata", ...])
```

**Problems:**
- Can't test without GUI
- Segfaults in tests
- Logic mixed with UI

### After (Decoupled)

```python
class TrayApplication(QApplication):
    def __init__(self):
        self.engine = PipewireEngine()
        
    def _change_sample_rate(self, rate):
        # Delegate to engine
        self.engine.set_sample_rate(rate)
```

**Benefits:**
- Test engine independently
- No segfaults
- Clean separation

## File Organization

```
src/pipewire_controller/
├── engine.py              # Pure logic (testable)
├── ui/
│   ├── tray.py           # GUI (thin layer)
│   └── dialogs.py        # Dialogs
├── utils/
│   ├── config.py         # Settings
│   └── process.py        # PID management
└── core/                 # Legacy (deprecated)
```

## Future Enhancements

With this architecture, we can easily add:

1. **CLI Tool** - Use engine directly
2. **Web API** - Expose engine via REST
3. **Alternative UIs** - GTK, web interface
4. **Plugins** - Extend engine functionality

All without touching the core logic!
