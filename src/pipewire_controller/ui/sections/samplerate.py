# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2024 Andrianos Papamarkou
"""
Sample Rate / Quantum accordion section.

Provides:
- Sample rate selector (populated from discovered hardware rates)
- Quantum/buffer size selector
- Force / Auto radio buttons
- Actual state display (requested vs actual PipeWire state)
"""

from __future__ import annotations

from PyQt6.QtCore import pyqtSignal
from PyQt6.QtWidgets import (
    QButtonGroup,
    QComboBox,
    QHBoxLayout,
    QLabel,
    QRadioButton,
    QVBoxLayout,
    QWidget,
)

from ...log import get_logger
from ...pipewire.model import GraphSettings
from ..theme import C_OK, TEXT_DIM, TEXT_LABEL, TEXT_PRIMARY, TEXT_SECONDARY

log = get_logger("ui.samplerate")

_QUANTUM_VALUES = [32, 64, 128, 256, 512, 1024, 2048, 4096]
_FALLBACK_RATES = [44100, 48000, 88200, 96000, 176400, 192000]

_LABEL_STYLE = f"color: {TEXT_LABEL}; font-size: 10px; font-weight: bold; background: transparent; letter-spacing: 0.5px;"
_VALUE_STYLE = f"color: {TEXT_PRIMARY}; font-size: 11px; background: transparent;"
_DIM_STYLE = f"color: {TEXT_DIM}; font-size: 10px; background: transparent;"


class SampleRateSection(QWidget):
    """Content widget for the Sample Rate / Quantum accordion section."""

    rate_force_requested = pyqtSignal(int)  # force to this rate
    rate_auto_requested = pyqtSignal()  # clear force-rate
    quantum_force_requested = pyqtSignal(int)  # force to this quantum
    quantum_auto_requested = pyqtSignal()  # clear force-quantum

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._available_rates: list[int] = list(_FALLBACK_RATES)
        self._settings: GraphSettings | None = None
        self._rate_combo_connected = False
        self._quantum_combo_connected = False
        self._build_ui()

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 6, 8, 6)
        layout.setSpacing(6)

        # ── Sample Rate ───────────────────────────────────────────────────────
        layout.addWidget(self._make_label("SAMPLE RATE"))

        rate_row = QHBoxLayout()
        self._rate_combo = QComboBox()
        self._rate_combo.setMinimumWidth(100)
        self._populate_rates(_FALLBACK_RATES)
        rate_row.addWidget(self._rate_combo)
        rate_row.addStretch()
        layout.addLayout(rate_row)

        # Force / Auto
        mode_row = QHBoxLayout()
        self._rate_force_rb = QRadioButton("Force")
        self._rate_auto_rb = QRadioButton("Auto")
        self._rate_auto_rb.setChecked(True)
        self._rate_group = QButtonGroup(self)
        self._rate_group.addButton(self._rate_force_rb)
        self._rate_group.addButton(self._rate_auto_rb)
        for rb in (self._rate_force_rb, self._rate_auto_rb):
            rb.setStyleSheet(f"color: {TEXT_SECONDARY}; font-size: 11px; background: transparent;")
            mode_row.addWidget(rb)
        mode_row.addStretch()
        layout.addLayout(mode_row)

        self._rate_force_rb.toggled.connect(self._on_rate_mode_changed)

        # Actual state
        self._rate_actual_lbl = QLabel("")
        self._rate_actual_lbl.setStyleSheet(_DIM_STYLE)
        layout.addWidget(self._rate_actual_lbl)

        layout.addSpacing(4)

        # ── Quantum ───────────────────────────────────────────────────────────
        layout.addWidget(self._make_label("BUFFER / QUANTUM"))

        q_row = QHBoxLayout()
        self._quantum_combo = QComboBox()
        self._quantum_combo.setMinimumWidth(100)
        for q in _QUANTUM_VALUES:
            self._quantum_combo.addItem(str(q), q)
        q_row.addWidget(self._quantum_combo)
        q_row.addStretch()
        layout.addLayout(q_row)

        q_mode_row = QHBoxLayout()
        self._q_force_rb = QRadioButton("Force")
        self._q_auto_rb = QRadioButton("Auto")
        self._q_auto_rb.setChecked(True)
        self._quantum_group = QButtonGroup(self)
        self._quantum_group.addButton(self._q_force_rb)
        self._quantum_group.addButton(self._q_auto_rb)
        for rb in (self._q_force_rb, self._q_auto_rb):
            rb.setStyleSheet(f"color: {TEXT_SECONDARY}; font-size: 11px; background: transparent;")
            q_mode_row.addWidget(rb)
        q_mode_row.addStretch()
        layout.addLayout(q_mode_row)

        self._q_force_rb.toggled.connect(self._on_quantum_mode_changed)

        self._quantum_actual_lbl = QLabel("")
        self._quantum_actual_lbl.setStyleSheet(_DIM_STYLE)
        layout.addWidget(self._quantum_actual_lbl)

        # Period info
        layout.addSpacing(4)
        self._period_lbl = QLabel("")
        self._period_lbl.setStyleSheet(_DIM_STYLE)
        layout.addWidget(self._period_lbl)

    def _make_label(self, text: str) -> QLabel:
        lbl = QLabel(text)
        lbl.setStyleSheet(_LABEL_STYLE)
        return lbl

    def _populate_rates(self, rates: list[int]) -> None:
        self._rate_combo.blockSignals(True)
        current = self._rate_combo.currentData()
        self._rate_combo.clear()
        for r in sorted(set(rates)):
            self._rate_combo.addItem(f"{r} Hz", r)
        # Restore selection
        idx = self._rate_combo.findData(current)
        if idx >= 0:
            self._rate_combo.setCurrentIndex(idx)
        self._rate_combo.blockSignals(False)

    def update_available_rates(self, rates: list[int]) -> None:
        """Update the rate combo with hardware-discovered rates."""
        self._available_rates = rates
        self._populate_rates(rates)

    def update_settings(self, settings: GraphSettings) -> None:
        """Refresh UI to reflect actual PipeWire state."""
        self._settings = settings

        # Rate mode
        self._rate_force_rb.blockSignals(True)
        self._rate_auto_rb.blockSignals(True)
        if settings.rate_is_forced:
            self._rate_force_rb.setChecked(True)
            idx = self._rate_combo.findData(settings.force_rate)
            if idx >= 0:
                self._rate_combo.blockSignals(True)
                self._rate_combo.setCurrentIndex(idx)
                self._rate_combo.blockSignals(False)
        else:
            self._rate_auto_rb.setChecked(True)
        self._rate_force_rb.blockSignals(False)
        self._rate_auto_rb.blockSignals(False)

        # Actual rate display
        if settings.rate_is_forced:
            actual_matches = settings.rate == settings.force_rate
            if actual_matches:
                color = C_OK
                text = f"Active: {settings.rate} Hz"
            else:
                color = TEXT_DIM
                text = f"Forced: {settings.force_rate} Hz  (idle: {settings.rate} Hz)"
            self._rate_actual_lbl.setStyleSheet(
                f"color: {color}; font-size: 10px; background: transparent;"
            )
            self._rate_actual_lbl.setText(text)
        else:
            self._rate_actual_lbl.setText(f"Actual: {settings.rate} Hz (auto)")
            self._rate_actual_lbl.setStyleSheet(_DIM_STYLE)

        # Quantum mode
        self._q_force_rb.blockSignals(True)
        self._q_auto_rb.blockSignals(True)
        if settings.quantum_is_forced:
            self._q_force_rb.setChecked(True)
            idx = self._quantum_combo.findData(settings.force_quantum)
            if idx >= 0:
                self._quantum_combo.blockSignals(True)
                self._quantum_combo.setCurrentIndex(idx)
                self._quantum_combo.blockSignals(False)
        else:
            self._q_auto_rb.setChecked(True)
        self._q_force_rb.blockSignals(False)
        self._q_auto_rb.blockSignals(False)

        # Actual quantum display
        if settings.quantum_is_forced:
            actual_matches = settings.quantum == settings.force_quantum
            if actual_matches:
                color = C_OK
                text = f"Active: {settings.quantum}"
            else:
                color = TEXT_DIM
                text = f"Forced: {settings.force_quantum}  (idle: {settings.quantum})"
            self._quantum_actual_lbl.setStyleSheet(
                f"color: {color}; font-size: 10px; background: transparent;"
            )
            self._quantum_actual_lbl.setText(text)
        else:
            self._quantum_actual_lbl.setText(f"Actual: {settings.quantum} (auto)")
            self._quantum_actual_lbl.setStyleSheet(_DIM_STYLE)

        # Period
        self._period_lbl.setText(f"Period: {settings.period_ms:.2f} ms")

    def _on_rate_mode_changed(self, force: bool) -> None:
        if force:
            rate = self._rate_combo.currentData()
            if rate:
                self.rate_force_requested.emit(rate)
            if not self._rate_combo_connected:
                self._rate_combo.currentIndexChanged.connect(self._on_rate_combo_changed)
                self._rate_combo_connected = True
        else:
            if self._rate_combo_connected:
                self._rate_combo.currentIndexChanged.disconnect(self._on_rate_combo_changed)
                self._rate_combo_connected = False
            self.rate_auto_requested.emit()

    def _on_rate_combo_changed(self, _idx: int) -> None:
        if self._rate_force_rb.isChecked():
            rate = self._rate_combo.currentData()
            if rate:
                self.rate_force_requested.emit(rate)

    def _on_quantum_mode_changed(self, force: bool) -> None:
        if force:
            q = self._quantum_combo.currentData()
            if q:
                self.quantum_force_requested.emit(q)
            if not self._quantum_combo_connected:
                self._quantum_combo.currentIndexChanged.connect(self._on_quantum_combo_changed)
                self._quantum_combo_connected = True
        else:
            if self._quantum_combo_connected:
                self._quantum_combo.currentIndexChanged.disconnect(self._on_quantum_combo_changed)
                self._quantum_combo_connected = False
            self.quantum_auto_requested.emit()

    def _on_quantum_combo_changed(self, _idx: int) -> None:
        if self._q_force_rb.isChecked():
            q = self._quantum_combo.currentData()
            if q:
                self.quantum_force_requested.emit(q)
