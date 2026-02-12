# Architecture Overview

## Design Principles

1. **Separation of Concerns**: Core logic, UI, and utilities are separated
2. **Testability**: All components are mockable and testable
3. **Error Handling**: Graceful degradation when PipeWire commands fail
4. **Hardware Awareness**: Dynamic UI based on actual hardware capabilities

## Component Architecture

```
┌─────────────────────────────────────────────────────────┐
│                    System Tray UI                       │
│                  (ui/tray.py)                          │
│  - Menu rendering                                       │
│  - User interaction handling                            │
│  - Tooltip updates                                      │
└────────────┬────────────────────────────┬───────────────┘
             │                            │
             ▼                            ▼
┌────────────────────────┐   ┌──────────────────────────┐
│  PipeWire Controller   │   │   Hardware Detector      │
│  (core/pipewire.py)    │   │   (core/hardware.py)     │
│                        │   │                          │
│  - set_sample_rate()   │   │  - get_supported_rates() │
│  - set_buffer_size()   │   │  - get_device_info()     │
│  - get_current_rate()  │   │                          │
└────────┬───────────────┘   └──────────┬───────────────┘
         │                              │
         ▼                              ▼
┌─────────────────────────────────────────────────────────┐
│              PipeWire CLI Tools                         │
│  pw-metadata  |  pw-dump  |  wpctl                     │
└─────────────────────────────────────────────────────────┘

         ┌──────────────────────┐
         │   Configuration      │
         │   (utils/config.py)  │
         │                      │
         │  - load()            │
         │  - save()            │
         └──────────────────────┘

         ┌──────────────────────┐
         │  Process Manager     │
         │  (utils/process.py)  │
         │                      │
         │  - Single instance   │
         │  - PID management    │
         └──────────────────────┘
```

## Data Flow

### Startup Sequence

```
1. main() → ProcessManager.ensure_single_instance()
2. TrayApplication.__init__()
3. Config.load() → Load saved settings
4. HardwareDetector.get_supported_sample_rates() → Query hardware
5. PipeWireController.set_sample_rate() → Apply saved rate
6. PipeWireController.set_buffer_size() → Apply saved buffer
7. Create system tray icon and menu
8. Show tray icon
```

### User Changes Sample Rate

```
1. User clicks menu item (e.g., "96000 Hz")
2. TrayApplication._change_sample_rate(96000)
3. PipeWireController.set_sample_rate(96000)
4. subprocess.run(["pw-metadata", ...])
5. Update settings dict
6. Config.save(settings)
7. Update menu checkmarks
8. Update tooltip
```

### Hardware Detection Flow

```
1. HardwareDetector.get_supported_sample_rates()
2. subprocess.run(["pw-dump"])
3. Parse JSON output
4. Extract device info (type: PipeWire:Interface:Node)
5. Filter for Audio/Sink and Audio/Source
6. Extract rate parameters:
   - Direct rates: {"rate": 48000}
   - Range rates: {"rate": {"min": 44100, "max": 192000}}
7. Return sorted list of unique rates
8. Fallback to common rates on error
```

## Key Classes

### TrayApplication (ui/tray.py)

**Responsibilities:**
- System tray icon management
- Menu creation and updates
- User interaction handling
- Coordinating between components

**Key Methods:**
- `_create_menu()`: Build context menu with hardware-filtered rates
- `_change_sample_rate(rate)`: Handle rate change request
- `_change_buffer_size(size)`: Handle buffer change request
- `_update_menu()`: Update checkmarks after changes

### PipeWireController (core/pipewire.py)

**Responsibilities:**
- Interface to PipeWire via CLI tools
- Execute pw-metadata commands
- Query current settings

**Key Methods:**
- `set_sample_rate(rate: int) -> bool`: Set sample rate
- `set_buffer_size(size: int) -> bool`: Set buffer size
- `get_current_rate() -> Optional[int]`: Query current rate
- `get_current_quantum() -> Optional[int]`: Query current buffer

### HardwareDetector (core/hardware.py)

**Responsibilities:**
- Query PipeWire for device capabilities
- Parse pw-dump output
- Extract supported sample rates

**Key Methods:**
- `get_supported_sample_rates() -> List[int]`: Get hardware rates
- `_extract_rates_from_devices(devices) -> Set[int]`: Parse device data
- `get_current_device_info() -> Optional[str]`: Get device name

### Config (utils/config.py)

**Responsibilities:**
- Load/save settings to JSON
- Provide default settings
- Handle file I/O errors

**Key Methods:**
- `load() -> Dict[str, Any]`: Load settings from file
- `save(settings) -> bool`: Save settings to file

### ProcessManager (utils/process.py)

**Responsibilities:**
- Ensure single instance
- PID file management
- Cleanup on exit

**Key Methods:**
- `ensure_single_instance()`: Kill existing instance
- `cleanup()`: Remove PID file

## Error Handling Strategy

### Subprocess Errors

All subprocess calls use try/except with:
- `subprocess.CalledProcessError`: Command failed
- `subprocess.TimeoutExpired`: Command timed out (5s)
- Return `False` or fallback values on error

### File I/O Errors

Configuration file operations:
- Create directories if missing
- Return defaults if file doesn't exist
- Catch `IOError` and `json.JSONDecodeError`

### Hardware Detection Fallback

If hardware detection fails:
- Return common sample rates: [44100, 48000, 88200, 96000, 176400, 192000]
- Log error but continue operation
- User can still select rates (may fail if unsupported)

## Testing Strategy

### Unit Tests

- Mock all subprocess calls
- Test success and failure paths
- Verify correct command arguments
- Test error handling

### Integration Tests (Future)

- Test with actual PipeWire instance
- Verify settings persistence
- Test hardware detection with real devices

## Configuration Files

### Settings File
**Location**: `~/.config/pipewire-controller/settings.json`

```json
{
  "samplerate": 48000,
  "buffer_size": 512
}
```

### PID File
**Location**: `~/.config/pipewire-controller/app.pid`

Contains single line with process ID:
```
12345
```

## Dependencies

### Runtime
- **PyQt6**: GUI framework (>=6.4.0)
- **Python**: 3.10+ (for modern type hints)

### System
- **pw-metadata**: Set PipeWire metadata
- **pw-dump**: Query PipeWire state
- **wpctl**: Query device info (optional)

### Development
- **pytest**: Test framework
- **pytest-mock**: Mocking support
- **pytest-cov**: Coverage reporting
- **black**: Code formatting
- **ruff**: Linting

## Performance Considerations

- **Startup Time**: ~100-200ms (hardware detection)
- **Memory**: ~30-50MB (PyQt6 overhead)
- **CPU**: Minimal (event-driven)

## Future Enhancements

1. **Profile Support**: Save/load multiple configurations
2. **Device Selection**: Choose specific audio device
3. **Notification**: Show toast on rate change
4. **Hotkey Support**: Global shortcuts for common rates
5. **Advanced Settings**: More PipeWire parameters
6. **GUI Configuration**: Settings dialog instead of JSON
