# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2024 Andrianos Papamarkou
"""
Devices / I/O accordion section.

Shows input and output audio nodes grouped by direction.
Each node shows: description, volume slider, mute, default selector,
sample-rate capability status, and channel info.
"""

from __future__ import annotations

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import (
    QCheckBox,
    QHBoxLayout,
    QLabel,
    QSlider,
    QToolButton,
    QVBoxLayout,
    QWidget,
)

from ...log import get_logger
from ...pipewire.model import AudioNode, PipeWireGraph, SampleRateSupport
from ..theme import (
    BG_SECTION,
    BG_WIDGET,
    BORDER,
    C_OK,
    C_WARN,
    TEXT_DIM,
    TEXT_PRIMARY,
    TEXT_SECONDARY,
)

log = get_logger("ui.devices")

_SECTION_LABEL_STYLE = (
    f"color: {TEXT_DIM}; font-size: 10px; font-weight: bold; "
    f"letter-spacing: 1px; background: transparent; padding: 4px 8px 2px 8px;"
)
_NODE_WIDGET_STYLE = (
    f"QWidget#nodeWidget {{ background: {BG_WIDGET}; border-bottom: 1px solid {BORDER}; }}"
    f"QWidget#nodeWidget:hover {{ background: {BG_SECTION}; }}"
)


class NodeWidget(QWidget):
    """Compact row for a single audio node."""

    default_changed = pyqtSignal(int, bool)  # node_id, is_default
    volume_changed = pyqtSignal(int, float)  # node_id, volume
    mute_changed = pyqtSignal(int, bool)  # node_id, muted

    def __init__(self, node: AudioNode, graph_rate: int, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("nodeWidget")
        self.setStyleSheet(_NODE_WIDGET_STYLE)
        self._node = node
        self._graph_rate = graph_rate
        self._build_ui()

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 4, 8, 4)
        layout.setSpacing(2)

        # Top row: icon + name + default checkbox
        top = QHBoxLayout()
        top.setSpacing(4)

        icon = "🔊" if self._node.is_sink else "🎙"
        icon_lbl = QLabel(icon)
        icon_lbl.setFixedWidth(18)
        icon_lbl.setStyleSheet("background: transparent;")

        name_lbl = QLabel(self._node.display_name)
        name_lbl.setStyleSheet(f"color: {TEXT_PRIMARY}; background: transparent; font-size: 12px;")
        name_lbl.setToolTip(
            f"Technical name: {self._node.name}\n"
            f"Media class: {self._node.media_class}\n"
            f"Device: {self._node.device_name}\n"
            f"Channels: {self._node.channel_count} ({', '.join(self._node.channel_positions)})\n"
            f"State: {self._node.state}"
        )

        self._default_cb = QCheckBox("Default")
        self._default_cb.setChecked(self._node.is_default)
        self._default_cb.setStyleSheet(
            f"color: {TEXT_SECONDARY}; font-size: 10px; background: transparent;"
        )
        self._default_cb.toggled.connect(lambda v: self.default_changed.emit(self._node.id, v))

        top.addWidget(icon_lbl)
        top.addWidget(name_lbl, 1)
        top.addWidget(self._default_cb)
        layout.addLayout(top)

        # Volume row
        vol_row = QHBoxLayout()
        vol_row.setSpacing(4)

        self._mute_btn = QToolButton()
        self._mute_btn.setText("🔇" if self._node.muted else "🔊")
        self._mute_btn.setFixedSize(18, 18)
        self._mute_btn.setStyleSheet(
            "QToolButton { background: transparent; border: none; font-size: 11px; }"
        )
        self._mute_btn.clicked.connect(self._toggle_mute)

        self._vol_slider = QSlider(Qt.Orientation.Horizontal)
        self._vol_slider.setRange(0, 100)
        self._vol_slider.setValue(int(self._node.volume * 100))
        self._vol_slider.setFixedHeight(14)
        self._vol_slider.valueChanged.connect(
            lambda v: self.volume_changed.emit(self._node.id, v / 100.0)
        )

        self._vol_label = QLabel(f"{int(self._node.volume * 100)}%")
        self._vol_label.setFixedWidth(32)
        self._vol_label.setStyleSheet(
            f"color: {TEXT_DIM}; font-size: 10px; background: transparent;"
        )
        self._vol_slider.valueChanged.connect(lambda v: self._vol_label.setText(f"{v}%"))

        vol_row.addWidget(self._mute_btn)
        vol_row.addWidget(self._vol_slider, 1)
        vol_row.addWidget(self._vol_label)
        layout.addLayout(vol_row)

        # Rate support indicator
        support = self._node.rate_support(self._graph_rate)
        rate_lbl = self._make_rate_label(support)
        layout.addWidget(rate_lbl)

    def _make_rate_label(self, support: SampleRateSupport) -> QLabel:
        if support == SampleRateSupport.NATIVE:
            text = f"✓ Native {self._graph_rate} Hz"
            color = C_OK
            tip = "This device natively supports the current graph sample rate."
        elif support == SampleRateSupport.RESAMPLED:
            native = ", ".join(str(r) for r in self._node.native_rates[:4])
            text = "⚠ Resampling required"
            color = C_WARN
            tip = (
                f"The current graph rate ({self._graph_rate} Hz) is not natively supported.\n"
                f"PipeWire will resample. Native rates: {native or 'unknown'}"
            )
        else:
            text = "? Rate unknown"
            color = TEXT_DIM
            tip = "Cannot determine native sample rate support for this device."

        lbl = QLabel(text)
        lbl.setStyleSheet(f"color: {color}; font-size: 10px; background: transparent;")
        lbl.setToolTip(tip)
        return lbl

    def _toggle_mute(self) -> None:
        new_muted = not self._node.muted
        self._node.muted = new_muted
        self._mute_btn.setText("🔇" if new_muted else "🔊")
        self.mute_changed.emit(self._node.id, new_muted)

    def update_node(self, node: AudioNode, graph_rate: int) -> None:
        self._node = node
        self._graph_rate = graph_rate
        self._default_cb.blockSignals(True)
        self._default_cb.setChecked(node.is_default)
        self._default_cb.blockSignals(False)
        self._vol_slider.blockSignals(True)
        self._vol_slider.setValue(int(node.volume * 100))
        self._vol_slider.blockSignals(False)
        self._mute_btn.setText("🔇" if node.muted else "🔊")


class DevicesSection(QWidget):
    """Content widget for the Devices / I/O accordion section."""

    default_sink_changed = pyqtSignal(int)
    default_source_changed = pyqtSignal(int)
    volume_changed = pyqtSignal(int, float)
    mute_changed = pyqtSignal(int, bool)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._layout = QVBoxLayout(self)
        self._layout.setContentsMargins(0, 0, 0, 0)
        self._layout.setSpacing(0)
        self._node_widgets: dict[int, NodeWidget] = {}

    def update_graph(self, graph: PipeWireGraph) -> None:
        """Rebuild the device list from a graph snapshot."""
        graph_rate = graph.settings.rate

        while self._layout.count():
            item = self._layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        self._node_widgets.clear()

        if graph.sources:
            self._add_group_label("INPUTS")
            for node in graph.sources:
                self._add_node(node, graph_rate)

        if graph.sinks:
            self._add_group_label("OUTPUTS")
            for node in graph.sinks:
                self._add_node(node, graph_rate)

        if not graph.nodes:
            empty = QLabel("No audio devices found")
            empty.setStyleSheet(
                f"color: {TEXT_DIM}; font-size: 11px; padding: 8px; background: transparent;"
            )
            self._layout.addWidget(empty)

        self._layout.addStretch()

    def _add_group_label(self, text: str) -> None:
        lbl = QLabel(text)
        lbl.setStyleSheet(_SECTION_LABEL_STYLE)
        self._layout.addWidget(lbl)

    def _add_node(self, node: AudioNode, graph_rate: int) -> None:
        w = NodeWidget(node, graph_rate)
        w.default_changed.connect(self._on_default_changed)
        w.volume_changed.connect(self.volume_changed)
        w.mute_changed.connect(self.mute_changed)
        self._layout.addWidget(w)
        self._node_widgets[node.id] = w

    def _on_default_changed(self, node_id: int, is_default: bool) -> None:
        if not is_default:
            return
        for nid, w in self._node_widgets.items():
            if nid == node_id:
                if w._node.is_sink:
                    self.default_sink_changed.emit(node_id)
                else:
                    self.default_source_changed.emit(node_id)
                break
