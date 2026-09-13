# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2024 Andrianos Papamarkou
"""
Application controller — wires PipeWire services to the UI.

Responsibilities:
- Periodic graph refresh (poll-based, non-blocking)
- Routing UI signals to PipeWire operations
- Routing PipeWire state to UI updates
- No direct PipeWire calls from UI widgets
- No Qt layout code here
"""

from __future__ import annotations

import subprocess
import threading

from PyQt6.QtCore import QTimer

from .config import active_preset, save, save_preset
from .log import get_logger
from .metering import ChannelMeter
from .pipewire import pw_client
from .pipewire.model import GraphSettings, PipeWireGraph
from .ui.panel import ControlPanel
from .ui.sections.config_section import ConfigSection
from .ui.sections.devices import DevicesSection
from .ui.sections.latency import LatencySection
from .ui.sections.master_meter import MasterMeterSection
from .ui.sections.meters import InputMeterSection, OutputMeterSection
from .ui.sections.samplerate import SampleRateSection

log = get_logger("controller")

_REFRESH_MS = 2000
_METER_MS = 100
_CAPTURE_RATE = 48000
_CAPTURE_FRAMES = 512


def _with_force_rate(s: GraphSettings, rate: int) -> GraphSettings:
    """Return a copy of settings with force_rate overridden."""
    from dataclasses import replace

    return replace(s, force_rate=rate)


def _with_force_quantum(s: GraphSettings, quantum: int) -> GraphSettings:
    """Return a copy of settings with force_quantum overridden."""
    from dataclasses import replace

    return replace(s, force_quantum=quantum)


class AppController:
    """
    Coordinates PipeWire state and UI panel.

    Created by TrayApp after the panel is initialized.
    """

    def __init__(self, panel: ControlPanel, config: dict) -> None:
        self._panel = panel
        self._config = config
        self._graph: PipeWireGraph | None = None

        # User intent — independent of what PipeWire reports back.
        # PipeWire may silently reset force-rate/quantum if unsupported;
        # we keep the user's choice until they explicitly click Auto.
        self._user_force_rate: int | None = None  # None = user wants auto
        self._user_force_quantum: int | None = None  # None = user wants auto

        self._devices_section: DevicesSection | None = None
        self._rate_section: SampleRateSection | None = None
        self._latency_section: LatencySection | None = None
        self._input_meter_section: InputMeterSection | None = None
        self._output_meter_section: OutputMeterSection | None = None
        self._master_meter_section: MasterMeterSection | None = None
        self._config_section: ConfigSection | None = None

        # Audio capture state
        self._output_meters: list[ChannelMeter] = []
        self._input_meters: list[ChannelMeter] = []
        self._capture_out_proc: subprocess.Popen | None = None
        self._capture_out_thread: threading.Thread | None = None
        # per source node: node_id -> (proc, thread, [ChannelMeter, ...])
        self._capture_in_procs: dict[int, tuple[subprocess.Popen, threading.Thread]] = {}
        self._all_procs: list[subprocess.Popen] = []  # every proc ever launched
        self._capture_lock = threading.Lock()

        self._build_sections()
        self._connect_signals()

        self._refresh_timer = QTimer()
        self._refresh_timer.timeout.connect(self._refresh_graph)
        self._refresh_timer.start(_REFRESH_MS)

        self._meter_timer = QTimer()
        self._meter_timer.timeout.connect(self._push_meter_snapshots)
        self._meter_timer.start(_METER_MS)

        # Initial load
        self._refresh_graph()
        self._apply_auto_load()

    def _apply_auto_load(self) -> None:
        """Apply active preset force settings on startup if auto_load is enabled."""
        preset = active_preset(self._config)
        # Always restore master meter mode + channel map from preset
        w = self._config.setdefault("window", {})
        w.setdefault("master_mode", preset.get("master_mode", "Stereo"))
        w.setdefault("master_channel_map", preset.get("master_channel_map", {}))
        self._restore_meter_modes()
        if not self._config.get("window", {}).get("auto_load", False):
            return
        if preset.get("force_rate"):
            rate = preset.get("samplerate")
            self._user_force_rate = rate
            pw_client.set_force_rate(rate)
        else:
            pw_client.clear_force_rate()
        if preset.get("force_quantum"):
            quantum = preset.get("quantum")
            self._user_force_quantum = quantum
            pw_client.set_force_quantum(quantum)
        else:
            pw_client.clear_force_quantum()

    def _restore_meter_modes(self) -> None:
        w = self._config.get("window", {})
        self._input_meter_section.set_mode(w.get("input_meter_mode", "Peak"))
        self._output_meter_section.set_mode(w.get("output_meter_mode", "Peak"))
        self._master_meter_section.set_mode(w.get("master_mode", "Stereo"))
        channel_map = w.get("master_channel_map", {})
        if channel_map:
            self._master_meter_section.set_channel_map(channel_map)

    def _build_sections(self) -> None:
        # Devices / I/O
        dev_accordion = self._panel.add_section("devices", "Devices / I/O")
        self._devices_section = DevicesSection()
        dev_accordion.add_widget(self._devices_section)

        # Sample Rate / Quantum
        rate_accordion = self._panel.add_section("samplerate", "Sample Rate / Quantum")
        self._rate_section = SampleRateSection()
        rate_accordion.add_widget(self._rate_section)

        # Latency
        lat_accordion = self._panel.add_section("latency", "Latency")
        self._latency_section = LatencySection()
        lat_accordion.add_widget(self._latency_section)

        # Input meters
        in_accordion = self._panel.add_section("input_meters", "Input Meters")
        self._input_meter_section = InputMeterSection()
        in_accordion.add_widget(self._input_meter_section)

        # Output meters
        out_accordion = self._panel.add_section("output_meters", "Output Meters")
        self._output_meter_section = OutputMeterSection()
        out_accordion.add_widget(self._output_meter_section)

        # Master meter
        master_accordion = self._panel.add_section("master_meter", "Master Meter")
        self._master_meter_section = MasterMeterSection()
        master_accordion.add_widget(self._master_meter_section)

        # Configuration
        cfg_accordion = self._panel.add_section("configuration", "Configuration")
        self._config_section = ConfigSection()
        cfg_accordion.add_widget(self._config_section)
        self._populate_config_section()

    def _connect_signals(self) -> None:
        ds = self._devices_section
        rs = self._rate_section
        ls = self._latency_section
        cs = self._config_section

        ds.default_sink_changed.connect(self._on_default_sink_changed)
        ds.default_source_changed.connect(self._on_default_source_changed)
        ds.volume_changed.connect(self._on_volume_changed)
        ds.mute_changed.connect(self._on_mute_changed)

        rs.rate_force_requested.connect(self._on_force_rate)
        rs.rate_auto_requested.connect(self._on_auto_rate)
        rs.quantum_force_requested.connect(self._on_force_quantum)
        rs.quantum_auto_requested.connect(self._on_auto_quantum)

        ls.measure_requested.connect(self._on_measure_latency)

        cs.save_requested.connect(self._on_save_config)
        cs.manage_requested.connect(self._on_manage_config)
        cs.preset_selected.connect(self._on_preset_selected)

        self._input_meter_section.mode_changed.connect(
            lambda m: self._config.setdefault("window", {}).__setitem__("input_meter_mode", m)
        )
        self._output_meter_section.mode_changed.connect(
            lambda m: self._config.setdefault("window", {}).__setitem__("output_meter_mode", m)
        )
        self._master_meter_section.mode_changed.connect(
            lambda m: self._config.setdefault("window", {}).__setitem__("master_mode", m)
        )
        self._master_meter_section.channel_map_changed.connect(
            lambda cm: self._config.setdefault("window", {}).__setitem__("master_channel_map", cm)
        )

    def _refresh_graph(self) -> None:
        graph = pw_client.get_graph()
        if graph is None:
            log.warning("PipeWire unavailable — graph refresh skipped")
            return

        self._graph = graph

        # Update available rates from discovered hardware
        all_rates: set[int] = set()
        for node in graph.nodes:
            all_rates.update(node.native_rates)
        if all_rates:
            self._rate_section.update_available_rates(sorted(all_rates))

        # Overlay user intent: if the user has forced rate/quantum, preserve
        # that in the UI even if PipeWire silently reset the metadata value
        # (e.g. device doesn't support the requested rate).
        settings = graph.settings
        if self._user_force_rate is not None:
            settings = _with_force_rate(settings, self._user_force_rate)
        if self._user_force_quantum is not None:
            settings = _with_force_quantum(settings, self._user_force_quantum)
        self._devices_section.update_graph(graph, settings)
        self._rate_section.update_settings(settings)
        self._latency_section.update_settings(settings)
        self._update_meter_channels(graph)

    # ── Meter channel population + capture ───────────────────────────────────

    def _update_meter_channels(self, graph) -> None:
        # One meter per channel per node — flat list matching capture interleave order
        input_meters = [
            ChannelMeter(name=pos, node_name=n.display_name, channel_number=i)
            for n in graph.sources
            for i, pos in enumerate(
                n.channel_positions if n.channel_positions else ["L", "R"][: n.channel_count]
            )
        ]
        output_meters = [
            ChannelMeter(name=pos, node_name=n.display_name, channel_number=i)
            for n in graph.sinks
            for i, pos in enumerate(
                n.channel_positions if n.channel_positions else ["L", "R"][: n.channel_count]
            )
        ]

        in_key = [(m.node_name, m.name) for m in input_meters]
        out_key = [(m.node_name, m.name) for m in output_meters]
        if in_key != getattr(self, "_last_in_key", None):
            self._input_meter_section.set_channels(input_meters)
            with self._capture_lock:
                self._input_meters = input_meters
            self._last_in_key = in_key
            self._restart_input_capture(graph.sources)
        if out_key != getattr(self, "_last_out_key", None):
            self._output_meter_section.set_channels(output_meters)
            with self._capture_lock:
                self._output_meters = output_meters
            self._last_out_key = out_key
            self._restart_output_capture()

        # Per-channel names for master meter: "Device FL", "Device FR", etc.
        output_channel_names = [
            f"{n.display_name} {pos}"
            for n in graph.sinks
            for pos in (
                n.channel_positions if n.channel_positions else ["L", "R"][: n.channel_count]
            )
        ]
        self._master_meter_section.update_available_outputs(output_channel_names)

    def _restart_output_capture(self) -> None:
        if self._capture_out_proc is not None:
            try:
                self._capture_out_proc.terminate()
                self._capture_out_proc.wait(timeout=2)
            except Exception:
                pass
            self._capture_out_proc = None

        if self._graph is None:
            return
        meter_offset = 0
        for node in self._graph.sinks:
            ch_count = node.channel_count or 2
            proc = self._launch_pw_record(
                name=f"pipewire-controller-out-{node.id}",
                channels=ch_count,
                target=str(node.id),
                extra_props={
                    "stream.capture.sink": "true",
                    "node.passive": "true",
                    "node.dont-reconnect": "true",
                },
            )
            if proc is None:
                meter_offset += ch_count
                continue
            offset = meter_offset
            t = threading.Thread(
                target=self._capture_loop_channels,
                args=(proc, ch_count, offset, "out"),
                daemon=True,
            )
            t.start()
            meter_offset += ch_count

    def _restart_input_capture(self, sources) -> None:
        for proc, _ in self._capture_in_procs.values():
            try:
                proc.terminate()
                proc.wait(timeout=2)
            except Exception:
                pass
        self._capture_in_procs.clear()

        meter_offset = 0
        for node in sources:
            ch_count = node.channel_count or 2
            target = str(node.props.get("object.serial") or node.id)
            proc = self._launch_pw_record(
                name=f"pipewire-controller-in-{node.id}",
                channels=ch_count,
                target=target,
                extra_props={
                    "node.passive": "true",
                },
            )
            if proc is None:
                meter_offset += ch_count
                continue
            offset = meter_offset
            t = threading.Thread(
                target=self._capture_loop_channels,
                args=(proc, ch_count, offset, "in"),
                daemon=True,
            )
            self._capture_in_procs[node.id] = (proc, t)
            t.start()
            meter_offset += ch_count

    def _launch_pw_record(
        self,
        name: str,
        channels: int,
        target: str = "auto",
        extra_props: dict | None = None,
    ) -> subprocess.Popen | None:
        import json as _json

        props = {"node.name": name, "media.name": name}
        if extra_props:
            props.update(extra_props)
        try:
            proc = subprocess.Popen(
                [
                    "pw-record",
                    "--target",
                    target,
                    "--channels",
                    str(channels),
                    "--rate",
                    str(_CAPTURE_RATE),
                    "--format",
                    "f32",
                    "--latency",
                    "512",
                    "-P",
                    _json.dumps(props),
                    "-",
                ],
                stdout=subprocess.PIPE,
                stderr=subprocess.DEVNULL,
            )
            self._all_procs.append(proc)
            return proc
        except FileNotFoundError:
            log.warning("pw-record not found — meters disabled")
            return None

    def _stop_capture(self) -> None:
        if self._capture_out_proc is not None:
            try:
                self._capture_out_proc.terminate()
                self._capture_out_proc.wait(timeout=2)
            except Exception:
                pass
            self._capture_out_proc = None
        for proc, _ in list(self._capture_in_procs.values()):
            try:
                proc.terminate()
                proc.wait(timeout=2)
            except Exception:
                pass
        self._capture_in_procs.clear()

    def shutdown(self) -> None:
        """Clean up all capture processes. Call before app exit."""
        self._refresh_timer.stop()
        self._meter_timer.stop()
        for proc in self._all_procs:
            try:
                if proc.poll() is None:
                    proc.terminate()
            except Exception:
                pass
        for proc in self._all_procs:
            try:
                proc.wait(timeout=2)
            except Exception:
                pass
        self._all_procs.clear()
        self._capture_in_procs.clear()
        self._capture_out_proc = None
        log.info("Controller shutdown complete")

    def _capture_loop_channels(
        self,
        proc: subprocess.Popen,
        ch_count: int,
        meter_offset: int,
        direction: str,  # "in" or "out"
    ) -> None:
        import numpy as np

        bytes_per_frame = ch_count * 4
        chunk = bytes_per_frame * _CAPTURE_FRAMES
        # After this many consecutive silent blocks, force meters to zero.
        # At 100ms meter interval and 512 frames @ 48kHz (~10ms/block) that’s ~0.5s of silence.
        _SILENCE_BLOCKS = 50
        silent_count = 0

        def _meters():
            lst = self._input_meters if direction == "in" else self._output_meters
            with self._capture_lock:
                return lst[meter_offset : meter_offset + ch_count]

        def _reset():
            for meter in _meters():
                meter.peak_linear = 0.0
                meter.rms_linear = 0.0

        while proc.poll() is None:
            data = proc.stdout.read(chunk)
            if not data:
                break
            n_frames = len(data) // bytes_per_frame
            if n_frames == 0:
                continue
            samples = np.frombuffer(data[: n_frames * bytes_per_frame], dtype=np.float32)
            samples = samples.reshape(-1, ch_count)
            # Detect silence: all samples below noise floor
            if np.max(np.abs(samples)) < 1e-6:
                silent_count += 1
                if silent_count >= _SILENCE_BLOCKS:
                    _reset()
                    silent_count = 0
                continue
            silent_count = 0
            for i, meter in enumerate(_meters()):
                meter.process_block(samples[:, i])

        # Process ended — reset to silence
        _reset()

    def _push_meter_snapshots(self) -> None:
        with self._capture_lock:
            out_snaps = [m.snapshot() for m in self._output_meters]
            in_snaps = [m.snapshot() for m in self._input_meters]
        if out_snaps:
            self._output_meter_section.update_meters(out_snaps)
            self._master_meter_section.update_levels(
                peaks_db=[s["peak_dbfs"] for s in out_snaps],
                rms_db=[s["rms_dbfs"] for s in out_snaps],
                peak_holds_db=[s["peak_hold_dbfs"] for s in out_snaps],
                overs=[s["over"] for s in out_snaps],
            )
        if in_snaps:
            self._input_meter_section.update_meters(in_snaps)

    # ── Device handlers ───────────────────────────────────────────────────────

    def _on_default_sink_changed(self, node_id: int) -> None:
        if pw_client.set_default_sink(node_id):
            log.info("Default sink set to %d", node_id)
            self._refresh_graph()
        else:
            log.error("Failed to set default sink to %d", node_id)

    def _on_default_source_changed(self, node_id: int) -> None:
        if pw_client.set_default_source(node_id):
            log.info("Default source set to %d", node_id)
            self._refresh_graph()
        else:
            log.error("Failed to set default source to %d", node_id)

    def _on_volume_changed(self, node_id: int, volume: float) -> None:
        pw_client.set_volume(node_id, volume)

    def _on_mute_changed(self, node_id: int, muted: bool) -> None:
        pw_client.set_mute(node_id, muted)

    # ── Sample rate / quantum handlers ────────────────────────────────────────

    def _on_force_rate(self, rate: int) -> None:
        self._user_force_rate = rate
        if not pw_client.set_force_rate(rate):
            log.error("Failed to force rate %d", rate)
        else:
            log.info("Forced rate: %d Hz", rate)
        self._refresh_graph()

    def _on_auto_rate(self) -> None:
        self._user_force_rate = None
        if pw_client.clear_force_rate():
            log.info("Rate returned to auto")
        self._refresh_graph()

    def _on_force_quantum(self, quantum: int) -> None:
        self._user_force_quantum = quantum
        if not pw_client.set_force_quantum(quantum):
            log.error("Failed to force quantum %d", quantum)
        else:
            log.info("Forced quantum: %d", quantum)
        self._refresh_graph()

    def _on_auto_quantum(self) -> None:
        self._user_force_quantum = None
        if pw_client.clear_force_quantum():
            log.info("Quantum returned to auto")
        self._refresh_graph()

    # ── Latency ───────────────────────────────────────────────────────────────

    def _on_measure_latency(self) -> None:
        from .ui.dialogs import LatencyWizardDialog

        dlg = LatencyWizardDialog(self._panel)
        dlg.measurement_complete.connect(self._on_latency_measured)
        dlg.exec()

    def _on_latency_measured(self, sw_ms: float, hw_ms: float | None) -> None:
        self._latency_section.set_measured_sw_rtl(sw_ms)
        self._latency_section.set_measured_hw_rtl(hw_ms)

    # ── Configuration ─────────────────────────────────────────────────────────

    def _populate_config_section(self) -> None:
        presets = list(self._config.get("presets", {}).keys())
        active = self._config.get("active_preset", "Default")
        self._config_section.populate_presets(presets, active)
        preset = active_preset(self._config)
        self._config_section.set_description(preset.get("description", ""))

    def _on_save_config(self) -> None:
        preset = active_preset(self._config)
        if self._graph:
            s = self._graph.settings
            preset["samplerate"] = self._user_force_rate or s.rate
            preset["quantum"] = self._user_force_quantum or s.quantum
            preset["force_rate"] = self._user_force_rate is not None
            preset["force_quantum"] = self._user_force_quantum is not None
        preset["panel_width"] = self._panel.width()
        # Persist master meter state into preset
        w = self._config.get("window", {})
        preset["master_mode"] = w.get("master_mode", "Stereo")
        preset["master_channel_map"] = w.get("master_channel_map", {})
        save_preset(self._config, preset)
        save(self._config)
        log.info("Configuration saved: %s", preset.get("name"))

    def _on_manage_config(self) -> None:
        from .ui.dialogs import ConfigManagerDialog

        dlg = ConfigManagerDialog(self._config, self._panel)
        dlg.config_loaded.connect(self._on_config_loaded)
        dlg.exec()
        self._populate_config_section()

    def _on_preset_selected(self, name: str) -> None:
        self._config["active_preset"] = name
        preset = active_preset(self._config)
        self._config_section.set_description(preset.get("description", ""))

    def _on_config_loaded(self, name: str) -> None:
        self._config["active_preset"] = name
        save(self._config)
        self._populate_config_section()
        preset = active_preset(self._config)
        if preset.get("force_rate"):
            rate = preset.get("samplerate")
            self._user_force_rate = rate
            pw_client.set_force_rate(rate)
        else:
            self._user_force_rate = None
            pw_client.clear_force_rate()
        if preset.get("force_quantum"):
            quantum = preset.get("quantum")
            self._user_force_quantum = quantum
            pw_client.set_force_quantum(quantum)
        else:
            self._user_force_quantum = None
            pw_client.clear_force_quantum()
        # Restore master meter mode + channel map from preset into window state
        w = self._config.setdefault("window", {})
        w["master_mode"] = preset.get("master_mode", "Stereo")
        w["master_channel_map"] = preset.get("master_channel_map", {})
        self._refresh_graph()
        self._restore_meter_modes()
        log.info("Loaded configuration: %s", name)
