# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2024 Andrianos Papamarkou
"""
Input / Output meter sections.

These sections display real-time level meters for audio channels.
In Phase 7, meters are populated from the device model.
Real-time audio capture via PyAudio is wired in the controller.

The GUI receives pre-processed meter snapshots — it never performs
audio analysis itself.
"""

from __future__ import annotations

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import (
    QComboBox,
    QHBoxLayout,
    QLabel,
    QMenu,
    QPushButton,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from ...metering import ChannelMeter
from ..components.meter_bar import MeterBar
from ..theme import C_ERROR, TEXT_DIM, TEXT_LABEL, TEXT_PRIMARY

_LABEL_STYLE = (
    f"color: {TEXT_LABEL}; font-size: 10px; font-weight: bold; "
    f"background: transparent; letter-spacing: 0.5px;"
)
_DIM_STYLE = f"color: {TEXT_DIM}; font-size: 10px; background: transparent;"
_VALUE_STYLE = f"color: {TEXT_PRIMARY}; font-size: 10px; background: transparent;"
_OVER_STYLE = f"color: {C_ERROR}; font-size: 10px; font-weight: bold; background: transparent;"


class ChannelMeterWidget(QWidget):
    """
    Compact channel meter: bar + name + level value + over indicator.
    Right-click to rename.
    """

    rename_requested = pyqtSignal(str)  # channel name

    def __init__(self, meter: ChannelMeter, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._meter = meter
        self._build_ui()

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(2, 2, 2, 2)
        layout.setSpacing(2)
        layout.setAlignment(Qt.AlignmentFlag.AlignHCenter)

        self._bar = MeterBar()
        layout.addWidget(self._bar, 1)

        self._name_lbl = QLabel(self._meter.name or "—")
        self._name_lbl.setStyleSheet(_DIM_STYLE)
        self._name_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._name_lbl.setMaximumWidth(40)
        layout.addWidget(self._name_lbl)

        self._level_lbl = QLabel("—")
        self._level_lbl.setStyleSheet(_VALUE_STYLE)
        self._level_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self._level_lbl)

        self._over_lbl = QLabel("OVR")
        self._over_lbl.setStyleSheet(_OVER_STYLE)
        self._over_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._over_lbl.setVisible(False)
        layout.addWidget(self._over_lbl)

        self.setToolTip(self._make_tooltip())
        self.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.customContextMenuRequested.connect(self._show_context_menu)

    def _make_tooltip(self) -> str:
        m = self._meter
        parts = [f"Channel: {m.name or '?'}"]
        if m.node_name:
            parts.append(f"Node: {m.node_name}")
        if m.port_name:
            parts.append(f"Port: {m.port_name}")
        if m.channel_number:
            parts.append(f"Ch#: {m.channel_number}")
        return "\n".join(parts)

    def update_from_snapshot(self, snap: dict) -> None:
        self._bar.set_level(snap["peak_dbfs"], snap["peak_hold_dbfs"], snap["over"])
        db = snap["peak_dbfs"]
        self._level_lbl.setText(f"{db:.1f}" if db > -120 else "—")
        self._over_lbl.setVisible(snap["over"])
        self._name_lbl.setText(snap["name"] or "—")

    def _show_context_menu(self, pos) -> None:
        menu = QMenu(self)
        rename_action = menu.addAction("Rename…")
        rename_action.triggered.connect(lambda: self.rename_requested.emit(self._meter.name))
        menu.exec(self.mapToGlobal(pos))


class MeterSection(QWidget):
    """
    Base class for Input/Output meter sections.

    Displays a row of ChannelMeterWidgets with mode selector and clear button.
    """

    clear_requested = pyqtSignal()

    def __init__(self, title: str, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._title = title
        self._channel_widgets: list[ChannelMeterWidget] = []
        self._build_ui()

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(6, 4, 6, 4)
        layout.setSpacing(4)

        # Controls row
        ctrl = QHBoxLayout()
        lbl = QLabel(self._title)
        lbl.setStyleSheet(_LABEL_STYLE)
        ctrl.addWidget(lbl)
        ctrl.addStretch()

        self._mode_combo = QComboBox()
        self._mode_combo.addItems(["Peak", "RMS"])
        self._mode_combo.setFixedWidth(60)
        ctrl.addWidget(self._mode_combo)

        clear_btn = QPushButton("CLEAR")
        clear_btn.setFixedWidth(50)
        clear_btn.clicked.connect(self._on_clear)
        ctrl.addWidget(clear_btn)
        layout.addLayout(ctrl)

        # Meter bars in a scroll area
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll.setFixedHeight(120)

        self._meters_widget = QWidget()
        self._meters_layout = QHBoxLayout(self._meters_widget)
        self._meters_layout.setContentsMargins(0, 0, 0, 0)
        self._meters_layout.setSpacing(2)
        self._meters_layout.addStretch()

        scroll.setWidget(self._meters_widget)
        layout.addWidget(scroll)

        self._empty_lbl = QLabel("No channels available")
        self._empty_lbl.setStyleSheet(_DIM_STYLE)
        layout.addWidget(self._empty_lbl)

    def set_channels(self, meters: list[ChannelMeter]) -> None:
        """Rebuild channel widgets from a list of ChannelMeter objects."""
        # Clear existing
        while self._meters_layout.count() > 1:
            item = self._meters_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        self._channel_widgets.clear()

        for m in meters:
            w = ChannelMeterWidget(m)
            self._meters_layout.insertWidget(self._meters_layout.count() - 1, w)
            self._channel_widgets.append(w)

        self._empty_lbl.setVisible(len(meters) == 0)

    def update_meters(self, snapshots: list[dict]) -> None:
        """Update meter displays from pre-processed snapshots. Call from GUI thread."""
        mode = self._mode_combo.currentText()
        for i, snap in enumerate(snapshots):
            if i >= len(self._channel_widgets):
                break
            if mode == "RMS":
                # Substitute peak with RMS for display
                display_snap = dict(snap)
                display_snap["peak_dbfs"] = snap["rms_dbfs"]
                self._channel_widgets[i].update_from_snapshot(display_snap)
            else:
                self._channel_widgets[i].update_from_snapshot(snap)

    def _on_clear(self) -> None:
        self.clear_requested.emit()


class InputMeterSection(MeterSection):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__("INPUTS", parent)


class OutputMeterSection(MeterSection):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__("OUTPUTS", parent)
