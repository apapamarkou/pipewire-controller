# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2024 Andrianos Papamarkou
"""
Latency accordion section — display and measurement.

Displays:
- Configured graph period (quantum / rate)
- Estimated graph latency
- Measured software RTL (from wizard)
- Measured hardware RTL (from wizard)

The MEASURE button opens the latency wizard (Phase 6).
"""

from __future__ import annotations

from PyQt6.QtCore import pyqtSignal
from PyQt6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from ...pipewire.model import GraphSettings
from ..theme import TEXT_DIM, TEXT_LABEL, TEXT_PRIMARY

_LABEL_STYLE = (
    f"color: {TEXT_LABEL}; font-size: 10px; font-weight: bold; "
    f"background: transparent; letter-spacing: 0.5px;"
)
_VALUE_STYLE = f"color: {TEXT_PRIMARY}; font-size: 11px; background: transparent;"
_DIM_STYLE = f"color: {TEXT_DIM}; font-size: 10px; background: transparent;"
_NOTE_STYLE = f"color: {TEXT_DIM}; font-size: 9px; background: transparent; font-style: italic;"


def _row(label: str, value_widget: QWidget) -> QHBoxLayout:
    hl = QHBoxLayout()
    hl.setSpacing(6)
    lbl = QLabel(label)
    lbl.setStyleSheet(_LABEL_STYLE)
    lbl.setFixedWidth(80)
    hl.addWidget(lbl)
    hl.addWidget(value_widget, 1)
    return hl


class LatencySection(QWidget):
    """Content widget for the Latency accordion section."""

    measure_requested = pyqtSignal()

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._build_ui()

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 6, 8, 6)
        layout.setSpacing(4)

        # Configured
        cfg_lbl = QLabel("CONFIGURED")
        cfg_lbl.setStyleSheet(_LABEL_STYLE)
        layout.addWidget(cfg_lbl)

        self._rate_val = QLabel("—")
        self._rate_val.setStyleSheet(_VALUE_STYLE)
        layout.addLayout(_row("Rate:", self._rate_val))

        self._quantum_val = QLabel("—")
        self._quantum_val.setStyleSheet(_VALUE_STYLE)
        layout.addLayout(_row("Quantum:", self._quantum_val))

        self._period_val = QLabel("—")
        self._period_val.setStyleSheet(_VALUE_STYLE)
        layout.addLayout(_row("Period:", self._period_val))

        note = QLabel(
            "Note: Period = quantum / rate. This is the processing period,\n"
            "not the total round-trip latency."
        )
        note.setStyleSheet(_NOTE_STYLE)
        note.setWordWrap(True)
        layout.addWidget(note)

        layout.addSpacing(6)

        # Measured
        meas_lbl = QLabel("MEASURED")
        meas_lbl.setStyleSheet(_LABEL_STYLE)
        layout.addWidget(meas_lbl)

        self._sw_rtl_val = QLabel("—")
        self._sw_rtl_val.setStyleSheet(_VALUE_STYLE)
        layout.addLayout(_row("Software RTL:", self._sw_rtl_val))

        self._hw_rtl_val = QLabel("—")
        self._hw_rtl_val.setStyleSheet(_VALUE_STYLE)
        layout.addLayout(_row("Hardware RTL:", self._hw_rtl_val))

        measure_btn = QPushButton("MEASURE LATENCY…")
        measure_btn.clicked.connect(self.measure_requested)
        layout.addWidget(measure_btn)

    def update_settings(self, settings: GraphSettings) -> None:
        rate = settings.force_rate if settings.rate_is_forced else settings.rate
        quantum = settings.force_quantum if settings.quantum_is_forced else settings.quantum
        period_ms = (quantum / rate * 1000.0) if rate else 0.0
        self._rate_val.setText(f"{rate} Hz")
        self._quantum_val.setText(f"{quantum} frames")
        self._period_val.setText(f"{period_ms:.2f} ms")

    def set_measured_sw_rtl(self, ms: float | None) -> None:
        self._sw_rtl_val.setText(f"{ms:.2f} ms" if ms is not None else "—")

    def set_measured_hw_rtl(self, ms: float | None) -> None:
        self._hw_rtl_val.setText(f"{ms:.2f} ms" if ms is not None else "—")
