"""Tests for system detection."""

from unittest.mock import patch

from pipewire_controller.detection import (
    ComponentStatus,
    SystemStatus,
    detect_system,
)


class TestComponentStatus:
    def test_ok_when_installed_and_running(self):
        c = ComponentStatus("PipeWire", installed=True, running=True)
        assert c.ok is True
        assert c.symbol == "✓"

    def test_not_ok_when_not_installed(self):
        c = ComponentStatus("PipeWire", installed=False, running=False)
        assert c.ok is False
        assert c.symbol == "✕"

    def test_warn_when_installed_not_running(self):
        c = ComponentStatus("PipeWire", installed=True, running=False)
        assert c.ok is False
        assert c.symbol == "⚠"

    def test_ok_when_running_is_none(self):
        # running=None means "not a service" — installed is sufficient
        c = ComponentStatus("PipeWire JACK", installed=True, running=None)
        assert c.ok is True
        assert c.symbol == "✓"

    def test_not_ok_when_not_installed_running_none(self):
        c = ComponentStatus("PipeWire JACK", installed=False, running=None)
        assert c.ok is False


class TestSystemStatus:
    def _make_status(self, pw_ok=True, wp_ok=True, jack=True):
        return SystemStatus(
            pipewire=ComponentStatus("PipeWire", installed=pw_ok, running=pw_ok),
            wireplumber=ComponentStatus("WirePlumber", installed=wp_ok, running=wp_ok),
            pipewire_jack=ComponentStatus("PipeWire JACK", installed=jack, running=None),
        )

    def test_pipewire_available(self):
        s = self._make_status(pw_ok=True)
        assert s.pipewire_available is True

    def test_pipewire_not_available(self):
        s = self._make_status(pw_ok=False)
        assert s.pipewire_available is False

    def test_fully_operational(self):
        s = self._make_status(pw_ok=True, wp_ok=True)
        assert s.fully_operational is True

    def test_not_fully_operational_without_wireplumber(self):
        s = self._make_status(pw_ok=True, wp_ok=False)
        assert s.fully_operational is False


class TestDetectSystem:
    def test_returns_system_status(self):
        with (
            patch("pipewire_controller.detection._cmd_exists", return_value=True),
            patch("pipewire_controller.detection._service_active", return_value=True),
            patch("pipewire_controller.detection._pipewire_version", return_value="1.0"),
            patch("pipewire_controller.detection._jack_installed", return_value=True),
        ):
            status = detect_system()
        assert isinstance(status, SystemStatus)
        assert status.pipewire.installed is True
        assert status.pipewire.running is True
        assert status.wireplumber.installed is True
        assert status.pipewire_jack.installed is True

    def test_graceful_when_nothing_installed(self):
        with (
            patch("pipewire_controller.detection._cmd_exists", return_value=False),
            patch("pipewire_controller.detection._service_active", return_value=False),
            patch("pipewire_controller.detection._pipewire_version", return_value=None),
            patch("pipewire_controller.detection._jack_installed", return_value=False),
        ):
            status = detect_system()
        assert status.pipewire.installed is False
        assert status.pipewire_available is False

    def test_never_raises(self):
        with patch("pipewire_controller.detection._cmd_exists", side_effect=RuntimeError("boom")):
            status = detect_system()
        assert isinstance(status, SystemStatus)
