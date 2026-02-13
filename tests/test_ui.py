"""UI tests for system tray application with mocked PipeWire commands."""

import pytest
import json
from unittest.mock import Mock, patch, call
from PyQt6.QtWidgets import QMenu
from PyQt6.QtCore import Qt

from pipewire_controller.ui.tray import TrayApplication


@pytest.fixture
def mock_pw_dump_json():
    """Sample pw-dump JSON output with device capabilities."""
    return json.dumps([
        {
            "type": "PipeWire:Interface:Node",
            "info": {
                "props": {"media.class": "Audio/Sink"},
                "params": {
                    "EnumFormat": [
                        {"rate": 48000},
                        {"rate": 96000},
                        {"rate": 192000}
                    ]
                }
            }
        }
    ])


@pytest.fixture
def mock_subprocess(mocker, mock_pw_dump_json):
    """Mock all subprocess calls."""
    mock_run = mocker.patch("subprocess.run")
    
    def subprocess_side_effect(cmd, **kwargs):
        if "pw-dump" in cmd:
            return Mock(stdout=mock_pw_dump_json, returncode=0)
        elif "pw-metadata" in cmd:
            if "clock.force-rate" in cmd:
                return Mock(stdout="", returncode=0)
            elif "clock.force-quantum" in cmd:
                return Mock(stdout="", returncode=0)
            else:
                return Mock(stdout="", returncode=0)
        elif "wpctl" in cmd:
            return Mock(stdout="* 52. USB DAC [Audio/Sink]", returncode=0)
        return Mock(stdout="", returncode=0)
    
    mock_run.side_effect = subprocess_side_effect
    return mock_run


@pytest.fixture
def mock_process_manager(mocker):
    """Mock process manager to avoid PID file operations."""
    mocker.patch("pipewire_controller.ui.tray.ProcessManager")


@pytest.fixture
def app(qapp, qtbot, mock_subprocess, mock_process_manager, tmp_path, mocker):
    """Create TrayApplication instance with mocked dependencies."""
    # Mock config directory
    mocker.patch("pathlib.Path.home", return_value=tmp_path)
    
    # Don't create new QApplication - reuse qapp from pytest-qt
    from pipewire_controller.ui.tray import TrayApplication
    from PyQt6.QtWidgets import QApplication
    
    # Patch QApplication to return existing instance
    original_init = TrayApplication.__init__
    
    def patched_init(self, argv):
        # Skip QApplication.__init__, just initialize our attributes
        self.config = mocker.MagicMock()
        self.config.load.return_value = {"samplerate": 48000, "buffer_size": 512}
        self.settings = self.config.load()
        self.pw_controller = mocker.MagicMock()
        self.hw_detector = mocker.MagicMock()
        self.hw_detector.get_supported_sample_rates.return_value = [48000, 96000, 192000]
        self.supported_rates = self.hw_detector.get_supported_sample_rates()
        
        from pipewire_controller.ui.tray import QSystemTrayIcon, QTimer
        self.tray_icon = QSystemTrayIcon()
        self._setup_icon()
        self.tray_icon.setContextMenu(self._create_menu())
        self.tray_icon.show()
        self.about_dialog = None
        self.timer = QTimer()
        self.timer.timeout.connect(lambda: None)
        self.timer.start(1000)
    
    mocker.patch.object(TrayApplication, '__init__', patched_init)
    test_app = TrayApplication([])
    
    yield test_app
    
    # Cleanup
    try:
        test_app.tray_icon.hide()
        test_app.timer.stop()
    except:
        pass


class TestTrayApplicationUI:
    """Test UI functionality with mocked PipeWire commands."""
    
    def test_menu_populated_with_hardware_rates(self, app, mock_subprocess):
        """Test that menu shows only hardware-supported sample rates."""
        menu = app.tray_icon.contextMenu()
        
        # Find sample rate submenu
        rate_menu = None
        for action in menu.actions():
            if action.menu() and action.text() == "Sample Rate":
                rate_menu = action.menu()
                break
        
        assert rate_menu is not None, "Sample Rate menu not found"
        
        # Get rate actions
        rate_actions = rate_menu.actions()
        rate_texts = [action.text() for action in rate_actions]
        
        # Should contain hardware-supported rates
        assert "48000 Hz" in rate_texts
        assert "96000 Hz" in rate_texts
        assert "192000 Hz" in rate_texts
    
    def test_clicking_rate_triggers_pw_metadata(self, app, mock_subprocess, qtbot):
        """Test that clicking a rate triggers correct pw-metadata command."""
        menu = app.tray_icon.contextMenu()
        
        # Find sample rate submenu
        rate_menu = None
        for action in menu.actions():
            if action.menu() and action.text() == "Sample Rate":
                rate_menu = action.menu()
                break
        
        # Find 96000 Hz action
        target_action = None
        for action in rate_menu.actions():
            if action.text() == "96000 Hz":
                target_action = action
                break
        
        assert target_action is not None
        
        # Trigger action
        target_action.trigger()
        qtbot.wait(100)
        
        # Verify pw-metadata was called with correct arguments
        calls = mock_subprocess.call_args_list
        pw_metadata_calls = [
            c for c in calls 
            if c[0][0][0] == "pw-metadata" and "clock.force-rate" in c[0][0]
        ]
        
        assert len(pw_metadata_calls) > 0
        assert "96000" in pw_metadata_calls[-1][0][0]
    
    def test_clicking_buffer_size_triggers_pw_metadata(self, app, mock_subprocess, qtbot):
        """Test that clicking buffer size triggers correct pw-metadata command."""
        menu = app.tray_icon.contextMenu()
        
        # Find buffer size submenu
        buffer_menu = None
        for action in menu.actions():
            if action.menu() and action.text() == "Buffer Size":
                buffer_menu = action.menu()
                break
        
        # Find 256 action
        target_action = None
        for action in buffer_menu.actions():
            if action.text() == "256":
                target_action = action
                break
        
        assert target_action is not None
        
        # Trigger action
        target_action.trigger()
        qtbot.wait(100)
        
        # Verify pw-metadata was called
        calls = mock_subprocess.call_args_list
        pw_quantum_calls = [
            c for c in calls 
            if c[0][0][0] == "pw-metadata" and "clock.force-quantum" in c[0][0]
        ]
        
        assert len(pw_quantum_calls) > 0
        assert "256" in pw_quantum_calls[-1][0][0]
    
    def test_menu_checkmarks_reflect_current_settings(self, app):
        """Test that menu checkmarks show current settings."""
        menu = app.tray_icon.contextMenu()
        
        # Find sample rate submenu
        rate_menu = None
        for action in menu.actions():
            if action.menu() and action.text() == "Sample Rate":
                rate_menu = action.menu()
                break
        
        # Check that current rate is checked
        checked_rates = [
            action.text() for action in rate_menu.actions() 
            if action.isCheckable() and action.isChecked()
        ]
        
        assert len(checked_rates) == 1
        assert str(app.settings["samplerate"]) in checked_rates[0]
    
    def test_tooltip_shows_current_settings(self, app):
        """Test that tooltip displays current sample rate and buffer size."""
        tooltip = app.tray_icon.toolTip()
        
        assert str(app.settings["samplerate"]) in tooltip
        assert str(app.settings["buffer_size"]) in tooltip
    
    def test_about_dialog_opens(self, app, qtbot):
        """Test that About dialog can be opened."""
        menu = app.tray_icon.contextMenu()
        
        # Find About action
        about_action = None
        for action in menu.actions():
            if action.text() == "About":
                about_action = action
                break
        
        assert about_action is not None
        
        # Trigger action
        about_action.trigger()
        qtbot.wait(100)
        
        # Check dialog exists and is visible
        assert app.about_dialog is not None
        assert app.about_dialog.isVisible()


class TestErrorHandling:
    """Test error handling when PipeWire commands fail."""
    
    def test_pw_metadata_failure_handled_gracefully(self, qtbot, mock_process_manager, tmp_path, mocker):
        """Test that non-zero exit code from pw-metadata is handled."""
        # Mock subprocess to fail on pw-metadata
        mock_run = mocker.patch("subprocess.run")
        
        def failing_subprocess(cmd, **kwargs):
            if "pw-dump" in cmd:
                return Mock(stdout="[]", returncode=0)
            elif "pw-metadata" in cmd and "clock.force-rate" in cmd:
                # Simulate failure
                from subprocess import CalledProcessError
                raise CalledProcessError(1, cmd)
            return Mock(stdout="", returncode=0)
        
        mock_run.side_effect = failing_subprocess
        mocker.patch("pathlib.Path.home", return_value=tmp_path)
        
        # Create app
        app = TrayApplication([])
        
        # Try to change rate
        initial_rate = app.settings["samplerate"]
        app._change_sample_rate(96000)
        qtbot.wait(100)
        
        # Settings should not change on failure
        assert app.settings["samplerate"] == initial_rate
        
        # Cleanup
        try:
            app.tray_icon.hide()
        except:
            pass
    
    def test_pw_dump_failure_uses_fallback_rates(self, qtbot, mock_process_manager, tmp_path, mocker):
        """Test that fallback rates are used when pw-dump fails."""
        # Mock subprocess to fail on pw-dump
        mock_run = mocker.patch("subprocess.run")
        
        def failing_subprocess(cmd, **kwargs):
            if "pw-dump" in cmd:
                from subprocess import CalledProcessError
                raise CalledProcessError(1, cmd)
            return Mock(stdout="", returncode=0)
        
        mock_run.side_effect = failing_subprocess
        mocker.patch("pathlib.Path.home", return_value=tmp_path)
        
        # Create app
        app = TrayApplication([])
        
        # Should have fallback rates
        assert len(app.supported_rates) > 0
        assert 44100 in app.supported_rates
        assert 48000 in app.supported_rates
        
        # Cleanup
        try:
            app.tray_icon.hide()
        except:
            pass
    
    def test_pw_dump_timeout_handled(self, qtbot, mock_process_manager, tmp_path, mocker):
        """Test that pw-dump timeout is handled gracefully."""
        from subprocess import TimeoutExpired
        
        mock_run = mocker.patch("subprocess.run")
        
        def timeout_subprocess(cmd, **kwargs):
            if "pw-dump" in cmd:
                raise TimeoutExpired(cmd, 5)
            return Mock(stdout="", returncode=0)
        
        mock_run.side_effect = timeout_subprocess
        mocker.patch("pathlib.Path.home", return_value=tmp_path)
        
        # Should not crash
        app = TrayApplication([])
        
        # Should have fallback rates
        assert len(app.supported_rates) > 0
        
        # Cleanup
        try:
            app.tray_icon.hide()
        except:
            pass


class TestSettingsPersistence:
    """Test that settings are saved and loaded correctly."""
    
    def test_settings_saved_after_rate_change(self, app, qtbot, tmp_path):
        """Test that changing rate saves settings to file."""
        app._change_sample_rate(96000)
        qtbot.wait(100)
        
        # Check settings file
        config_file = tmp_path / ".config" / "pipewire-controller" / "settings.json"
        assert config_file.exists()
        
        with open(config_file) as f:
            saved_settings = json.load(f)
        
        assert saved_settings["samplerate"] == 96000
    
    def test_settings_loaded_on_startup(self, qtbot, mock_subprocess, mock_process_manager, tmp_path, mocker):
        """Test that saved settings are loaded on startup."""
        mocker.patch("pathlib.Path.home", return_value=tmp_path)
        
        # Create settings file
        config_dir = tmp_path / ".config" / "pipewire-controller"
        config_dir.mkdir(parents=True)
        config_file = config_dir / "settings.json"
        
        with open(config_file, "w") as f:
            json.dump({"samplerate": 192000, "buffer_size": 1024}, f)
        
        # Create app
        app = TrayApplication([])
        
        # Should load saved settings
        assert app.settings["samplerate"] == 192000
        assert app.settings["buffer_size"] == 1024
        
        # Cleanup
        try:
            app.tray_icon.hide()
        except:
            pass
