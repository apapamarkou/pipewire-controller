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

from PyQt6.QtCore import QTimer

from .config import active_preset, save, save_preset
from .log import get_logger
from .pipewire import pw_client
from .pipewire.model import PipeWireGraph
from .ui.panel import ControlPanel
from .ui.sections.config_section import ConfigSection
from .ui.sections.devices import DevicesSection
from .ui.sections.latency import LatencySection
from .ui.sections.samplerate import SampleRateSection

log = get_logger("controller")

_REFRESH_MS = 2000  # graph refresh interval


class AppController:
    """
    Coordinates PipeWire state and UI panel.

    Created by TrayApp after the panel is initialized.
    """

    def __init__(self, panel: ControlPanel, config: dict) -> None:
        self._panel = panel
        self._config = config
        self._graph: PipeWireGraph | None = None

        self._devices_section: DevicesSection | None = None
        self._rate_section: SampleRateSection | None = None
        self._latency_section: LatencySection | None = None
        self._config_section: ConfigSection | None = None

        self._build_sections()
        self._connect_signals()

        self._refresh_timer = QTimer()
        self._refresh_timer.timeout.connect(self._refresh_graph)
        self._refresh_timer.start(_REFRESH_MS)

        # Initial load
        self._refresh_graph()

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

        self._devices_section.update_graph(graph)
        self._rate_section.update_settings(graph.settings)
        self._latency_section.update_settings(graph.settings)

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
        if pw_client.set_force_rate(rate):
            log.info("Forced rate: %d Hz", rate)
            QTimer.singleShot(500, self._refresh_graph)
        else:
            log.error("Failed to force rate %d", rate)

    def _on_auto_rate(self) -> None:
        if pw_client.clear_force_rate():
            log.info("Rate returned to auto")
            QTimer.singleShot(500, self._refresh_graph)

    def _on_force_quantum(self, quantum: int) -> None:
        if pw_client.set_force_quantum(quantum):
            log.info("Forced quantum: %d", quantum)
            QTimer.singleShot(500, self._refresh_graph)
        else:
            log.error("Failed to force quantum %d", quantum)

    def _on_auto_quantum(self) -> None:
        if pw_client.clear_force_quantum():
            log.info("Quantum returned to auto")
            QTimer.singleShot(500, self._refresh_graph)

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
            preset["samplerate"] = self._graph.settings.rate
            preset["quantum"] = self._graph.settings.quantum
            preset["force_rate"] = self._graph.settings.rate_is_forced
            preset["force_quantum"] = self._graph.settings.quantum_is_forced
        preset["panel_width"] = self._panel.width()
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
        log.info("Loaded configuration: %s", name)
