"""Tests for PipeWire client — pw_client.py."""

import json
import subprocess
from unittest.mock import patch

from pipewire_controller.pipewire import pw_client
from pipewire_controller.pipewire.model import NodeDirection

# ── Fixtures ──────────────────────────────────────────────────────────────────

_PW_DUMP_SAMPLE = json.dumps(
    [
        {
            "id": 60,
            "type": "PipeWire:Interface:Node",
            "info": {
                "state": "running",
                "props": {
                    "media.class": "Audio/Sink",
                    "node.name": "alsa_output.pci-0000_03_00.6",
                    "node.description": "Ryzen HD Audio Speaker",
                    "audio.channels": 2,
                    "audio.position": "[ FL, FR ]",
                    "alsa.card_name": "HD Audio Generic",
                    "device.id": 66,
                },
                "params": {
                    "EnumFormat": [
                        {
                            "mediaType": "audio",
                            "mediaSubtype": "raw",
                            "rate": 48000,
                            "channels": 2,
                        }
                    ]
                },
            },
        },
        {
            "id": 113,
            "type": "PipeWire:Interface:Node",
            "info": {
                "state": "idle",
                "props": {
                    "media.class": "Audio/Source",
                    "node.name": "alsa_input.pci-0000_03_00.6",
                    "node.description": "Ryzen HD Audio Microphone",
                    "audio.channels": 2,
                    "audio.position": "[ FL, FR ]",
                    "alsa.card_name": "HD Audio Generic",
                    "device.id": 66,
                },
                "params": {
                    "EnumFormat": [
                        {
                            "mediaType": "audio",
                            "mediaSubtype": "raw",
                            "rate": {"default": 48000, "min": 44100, "max": 192000},
                            "channels": 2,
                        }
                    ]
                },
            },
        },
        # Non-audio node — should be ignored
        {
            "id": 78,
            "type": "PipeWire:Interface:Node",
            "info": {
                "state": "running",
                "props": {"media.class": "Video/Source", "node.name": "v4l2_input"},
                "params": {},
            },
        },
    ]
)

_WPCTL_STATUS_SAMPLE = """
PipeWire 'pipewire-0' [1.6.8]
Audio
 ├─ Sinks:
 │  *   60. Ryzen HD Audio Speaker   [vol: 0.75]
 │
 ├─ Sources:
 │  *  113. Ryzen HD Audio Microphone [vol: 1.00]
"""

_PW_METADATA_SAMPLE = """
Found "settings" metadata 32
update: id:0 key:'clock.rate' value:'48000' type:''
update: id:0 key:'clock.allowed-rates' value:'[ 48000 ]' type:''
update: id:0 key:'clock.quantum' value:'1024' type:''
update: id:0 key:'clock.min-quantum' value:'32' type:''
update: id:0 key:'clock.max-quantum' value:'2048' type:''
update: id:0 key:'clock.force-quantum' value:'0' type:''
update: id:0 key:'clock.force-rate' value:'0' type:''
"""


def _mock_run_check(cmd, **kwargs):
    if cmd[0] == "pw-dump":
        return _PW_DUMP_SAMPLE
    if cmd[0] == "wpctl" and cmd[1] == "status":
        return _WPCTL_STATUS_SAMPLE
    if cmd[0] == "wpctl" and cmd[1] == "get-volume":
        return "Volume: 0.75\n"
    if cmd[0] == "pw-metadata":
        return _PW_METADATA_SAMPLE
    return ""


# ── Tests ─────────────────────────────────────────────────────────────────────


class TestGetGraph:
    def test_returns_graph_with_nodes(self):
        with patch.object(pw_client, "_run_check", side_effect=_mock_run_check):
            graph = pw_client.get_graph()
        assert graph is not None
        assert len(graph.nodes) == 2

    def test_sinks_and_sources(self):
        with patch.object(pw_client, "_run_check", side_effect=_mock_run_check):
            graph = pw_client.get_graph()
        assert len(graph.sinks) == 1
        assert len(graph.sources) == 1

    def test_sink_properties(self):
        with patch.object(pw_client, "_run_check", side_effect=_mock_run_check):
            graph = pw_client.get_graph()
        sink = graph.sinks[0]
        assert sink.id == 60
        assert sink.name == "alsa_output.pci-0000_03_00.6"
        assert sink.description == "Ryzen HD Audio Speaker"
        assert sink.direction == NodeDirection.OUTPUT
        assert sink.channel_count == 2
        assert sink.channel_positions == ["FL", "FR"]

    def test_source_rate_range(self):
        with patch.object(pw_client, "_run_check", side_effect=_mock_run_check):
            graph = pw_client.get_graph()
        source = graph.sources[0]
        assert source.rate_range == (44100, 192000)
        assert 48000 in source.native_rates
        assert 96000 in source.native_rates

    def test_default_ids(self):
        with patch.object(pw_client, "_run_check", side_effect=_mock_run_check):
            graph = pw_client.get_graph()
        assert graph.default_sink_id == 60
        assert graph.default_source_id == 113

    def test_returns_none_when_pw_unavailable(self):
        with patch.object(
            pw_client,
            "_run_check",
            side_effect=subprocess.CalledProcessError(1, "pw-dump"),
        ):
            graph = pw_client.get_graph()
        assert graph is None

    def test_video_nodes_excluded(self):
        with patch.object(pw_client, "_run_check", side_effect=_mock_run_check):
            graph = pw_client.get_graph()
        names = [n.name for n in graph.nodes]
        assert "v4l2_input" not in names


class TestParseSettings:
    def test_parses_settings(self):
        with patch.object(pw_client, "_run_check", return_value=_PW_METADATA_SAMPLE):
            s = pw_client.get_settings()
        assert s.rate == 48000
        assert s.quantum == 1024
        assert s.force_rate == 0
        assert s.force_quantum == 0
        assert s.min_quantum == 32
        assert s.max_quantum == 2048

    def test_graceful_on_failure(self):
        with patch.object(
            pw_client,
            "_run_check",
            side_effect=subprocess.CalledProcessError(1, "pw-metadata"),
        ):
            s = pw_client.get_settings()
        # Should return defaults, not raise
        assert s.rate == 48000


class TestExtractRates:
    def test_single_rate(self):
        params = {"EnumFormat": [{"rate": 48000}]}
        rates, rng = pw_client._extract_rates(params)
        assert 48000 in rates
        assert rng is None

    def test_range_rate(self):
        params = {"EnumFormat": [{"rate": {"min": 44100, "max": 192000, "default": 48000}}]}
        rates, rng = pw_client._extract_rates(params)
        assert rng == (44100, 192000)
        assert 48000 in rates
        assert 96000 in rates

    def test_empty_params(self):
        rates, rng = pw_client._extract_rates({})
        assert rates == []
        assert rng is None


class TestParsePositions:
    def test_stereo(self):
        assert pw_client._parse_positions("[ FL, FR ]") == ["FL", "FR"]

    def test_surround(self):
        result = pw_client._parse_positions("[ FL, FR, FC, LFE, RL, RR ]")
        assert result == ["FL", "FR", "FC", "LFE", "RL", "RR"]

    def test_empty(self):
        assert pw_client._parse_positions("") == []


class TestSetForceRate:
    def test_success(self):
        with patch.object(pw_client, "_run_check", return_value="") as mock:
            result = pw_client.set_force_rate(96000)
        assert result is True
        mock.assert_called_once_with(
            ["pw-metadata", "-n", "settings", "0", "clock.force-rate", "96000"]
        )

    def test_failure_returns_false(self):
        with patch.object(
            pw_client,
            "_run_check",
            side_effect=subprocess.CalledProcessError(1, "pw-metadata"),
        ):
            result = pw_client.set_force_rate(96000)
        assert result is False

    def test_clear_force_rate(self):
        with patch.object(pw_client, "_run_check", return_value="") as mock:
            result = pw_client.clear_force_rate()
        assert result is True
        mock.assert_called_once_with(
            ["pw-metadata", "-n", "settings", "0", "clock.force-rate", "0"]
        )


class TestSetForceQuantum:
    def test_success(self):
        with patch.object(pw_client, "_run_check", return_value=""):
            result = pw_client.set_force_quantum(256)
        assert result is True

    def test_clear_force_quantum(self):
        with patch.object(pw_client, "_run_check", return_value="") as mock:
            result = pw_client.clear_force_quantum()
        assert result is True
        mock.assert_called_once_with(
            ["pw-metadata", "-n", "settings", "0", "clock.force-quantum", "0"]
        )


class TestSetVolume:
    def test_success(self):
        with patch.object(pw_client, "_run_check", return_value="") as mock:
            result = pw_client.set_volume(60, 0.75)
        assert result is True
        mock.assert_called_once_with(["wpctl", "set-volume", "60", "0.75"])

    def test_clamps_volume(self):
        with patch.object(pw_client, "_run_check", return_value="") as mock:
            pw_client.set_volume(60, -0.5)
        call_args = mock.call_args[0][0]
        assert call_args[3] == "0.00"

    def test_failure_returns_false(self):
        with patch.object(
            pw_client,
            "_run_check",
            side_effect=subprocess.CalledProcessError(1, "wpctl"),
        ):
            result = pw_client.set_volume(60, 0.5)
        assert result is False


class TestSetMute:
    def test_mute(self):
        with patch.object(pw_client, "_run_check", return_value="") as mock:
            result = pw_client.set_mute(60, True)
        assert result is True
        mock.assert_called_once_with(["wpctl", "set-mute", "60", "1"])

    def test_unmute(self):
        with patch.object(pw_client, "_run_check", return_value="") as mock:
            result = pw_client.set_mute(60, False)
        assert result is True
        mock.assert_called_once_with(["wpctl", "set-mute", "60", "0"])
