# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2024 Andrianos Papamarkou
"""
Master / Surround meter section.

Supports Mono, Stereo, 2.1, Quadro, 5.1, 7.1, Custom channel configurations.
Displays Peak, RMS, LUFS-M, LUFS-S, LUFS-I per the ITU-R BS.1770-4 standard.
"""

from __future__ import annotations

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import (
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QVBoxLayout,
    QWidget,
)

from ..components.combo_box import NoScrollComboBox
from ..components.combo_box import NoScrollComboBox as QComboBox
from ..components.meter_bar import MeterBar
from ..theme import TEXT_DIM, TEXT_LABEL, TEXT_PRIMARY

# Standard channel configurations: name → (channel_count, labels)
MASTER_MODES: dict[str, tuple[int, list[str]]] = {
    "Mono": (1, ["M"]),
    "Stereo": (2, ["L", "R"]),
    "2.1": (3, ["L", "R", "LFE"]),
    "Quadro": (4, ["L", "R", "Ls", "Rs"]),
    "5.1": (6, ["L", "R", "C", "LFE", "Ls", "Rs"]),
    "7.1": (8, ["L", "R", "C", "LFE", "Lb", "Rb", "Ls", "Rs"]),
    "Custom": (0, []),  # user-defined
}

_LABEL_STYLE = (
    f"color: {TEXT_LABEL}; font-size: 10px; font-weight: bold; "
    f"background: transparent; letter-spacing: 0.5px;"
)
_DIM_STYLE = f"color: {TEXT_DIM}; font-size: 10px; background: transparent;"
_VALUE_STYLE = f"color: {TEXT_PRIMARY}; font-size: 11px; background: transparent;"


class MasterMeterSection(QWidget):
    """Content widget for the Master Meter accordion section."""

    channel_source_changed = pyqtSignal(int, str)  # channel_idx, source_name
    mode_changed = pyqtSignal(str)
    channel_map_changed = pyqtSignal(dict)  # {channel_idx: source_name}

    def __init__(
        self, available_outputs: list[str] | None = None, parent: QWidget | None = None
    ) -> None:
        super().__init__(parent)
        self._available_outputs: list[str] = available_outputs or []
        self._mode = "Stereo"
        self._channel_combos: list[QComboBox] = []
        self._meter_bars: list[MeterBar] = []
        self._build_ui()

    def _build_ui(self) -> None:
        self._layout = QVBoxLayout(self)
        self._layout.setContentsMargins(8, 6, 8, 6)
        self._layout.setSpacing(6)

        # Mode selector row with Clear button
        mode_row = QHBoxLayout()
        mode_lbl = QLabel("Mode:")
        mode_lbl.setStyleSheet(_LABEL_STYLE)
        self._mode_combo = NoScrollComboBox()
        self._mode_combo.addItems(list(MASTER_MODES.keys()))
        self._mode_combo.setCurrentText("Stereo")
        self._mode_combo.currentTextChanged.connect(self._on_mode_changed)
        mode_row.addWidget(mode_lbl)
        mode_row.addWidget(self._mode_combo)
        mode_row.addStretch()

        from PyQt6.QtWidgets import QPushButton

        clear_btn = QPushButton("CLEAR")
        clear_btn.clicked.connect(self.clear)
        mode_row.addWidget(clear_btn)
        self._layout.addLayout(mode_row)

        # Channel mapping + meters (rebuilt on mode change)
        self._channels_widget = QWidget()
        self._channels_layout = QVBoxLayout(self._channels_widget)
        self._channels_layout.setContentsMargins(0, 0, 0, 0)
        self._channels_layout.setSpacing(4)
        self._layout.addWidget(self._channels_widget)

        # LUFS display
        lufs_grid = QGridLayout()
        lufs_grid.setSpacing(4)
        for row, (label, attr) in enumerate(
            [
                ("Peak:", "_peak_lbl"),
                ("RMS:", "_rms_lbl"),
                ("LUFS-M:", "_lufsm_lbl"),
                ("LUFS-S:", "_lufss_lbl"),
                ("LUFS-I:", "_lufsi_lbl"),
            ]
        ):
            lbl = QLabel(label)
            lbl.setStyleSheet(_LABEL_STYLE)
            val = QLabel("—")
            val.setStyleSheet(_VALUE_STYLE)
            setattr(self, attr, val)
            lufs_grid.addWidget(lbl, row, 0)
            lufs_grid.addWidget(val, row, 1)
        self._layout.addLayout(lufs_grid)

        self._rebuild_channels()

    def _rebuild_channels(self) -> None:
        # Clear existing channel widgets
        while self._channels_layout.count():
            item = self._channels_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        self._channel_combos.clear()
        self._meter_bars.clear()

        count, labels = MASTER_MODES.get(self._mode, (0, []))
        if self._mode == "Custom":
            count = max(2, len(self._channel_combos))
            labels = [f"Ch{i+1}" for i in range(count)]

        # Meter bars row
        bars_row = QHBoxLayout()
        bars_row.setSpacing(4)
        for i in range(count):
            col = QVBoxLayout()
            col.setSpacing(2)
            col.setAlignment(Qt.AlignmentFlag.AlignHCenter)

            bar = MeterBar()
            col.addWidget(bar)

            ch_lbl = QLabel(labels[i] if i < len(labels) else f"Ch{i+1}")
            ch_lbl.setStyleSheet(_DIM_STYLE)
            ch_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
            col.addWidget(ch_lbl)

            self._meter_bars.append(bar)
            bars_row.addLayout(col)

        bars_row.addStretch()
        bars_widget = QWidget()
        bars_widget.setLayout(bars_row)
        bars_widget.setFixedHeight(100)
        self._channels_layout.addWidget(bars_widget)

        # Channel source selectors
        for i in range(count):
            row = QHBoxLayout()
            lbl_text = labels[i] if i < len(labels) else f"Ch{i+1}"
            lbl = QLabel(f"{lbl_text}:")
            lbl.setStyleSheet(_DIM_STYLE)
            lbl.setFixedWidth(30)

            combo = NoScrollComboBox()
            combo.addItem("— None —")
            for out in self._available_outputs:
                combo.addItem(out)
            combo.currentTextChanged.connect(
                lambda text, idx=i: self._on_channel_source_changed(idx, text)
            )
            row.addWidget(lbl)
            row.addWidget(combo, 1)
            self._channel_combos.append(combo)
            self._channels_layout.addLayout(row)

    def _on_channel_source_changed(self, idx: int, text: str) -> None:
        self.channel_source_changed.emit(idx, text)
        self.channel_map_changed.emit(self.get_channel_map())

    def get_channel_map(self) -> dict:
        return {i: c.currentText() for i, c in enumerate(self._channel_combos)}

    def set_channel_map(self, channel_map: dict) -> None:
        """Restore combo selections by index. Silently skips missing entries."""
        for i, combo in enumerate(self._channel_combos):
            text = channel_map.get(str(i)) or channel_map.get(i)
            if text:
                idx = combo.findText(text)
                if idx >= 0:
                    combo.blockSignals(True)
                    combo.setCurrentIndex(idx)
                    combo.blockSignals(False)

    def set_mode(self, mode: str) -> None:
        self._mode_combo.blockSignals(True)
        self._mode_combo.setCurrentText(mode)
        self._mode_combo.blockSignals(False)
        self._mode = mode
        self._rebuild_channels()

    def _on_mode_changed(self, mode: str) -> None:
        self._mode = mode
        self._rebuild_channels()
        self.mode_changed.emit(mode)

    def update_available_outputs(self, outputs: list[str]) -> None:
        self._available_outputs = outputs
        for combo in self._channel_combos:
            current = combo.currentText()
            combo.blockSignals(True)
            combo.clear()
            combo.addItem("— None —")
            for out in outputs:
                combo.addItem(out)
            idx = combo.findText(current)
            if idx >= 0:
                combo.setCurrentIndex(idx)
            combo.blockSignals(False)

    def update_levels(
        self,
        peaks_db: list[float],
        rms_db: list[float],
        peak_holds_db: list[float],
        overs: list[bool],
        lufs_m: float | None = None,
        lufs_s: float | None = None,
        lufs_i: float | None = None,
    ) -> None:
        """Update all meter bars and LUFS display. Call from GUI thread."""
        active_peaks: list[float] = []
        active_rms: list[float] = []
        for i, bar in enumerate(self._meter_bars):
            selected = (
                self._channel_combos[i].currentText() if i < len(self._channel_combos) else ""
            )
            if selected == "— None —" or not selected:
                bar.set_level(-120.0, -120.0, False)
                continue
            # Find the index of the selected channel name in available outputs
            try:
                src_idx = self._available_outputs.index(selected)
            except ValueError:
                bar.set_level(-120.0, -120.0, False)
                continue
            if src_idx < len(peaks_db):
                bar.set_level(
                    peaks_db[src_idx],
                    peak_holds_db[src_idx] if src_idx < len(peak_holds_db) else peaks_db[src_idx],
                    overs[src_idx] if src_idx < len(overs) else False,
                )
                active_peaks.append(peaks_db[src_idx])
                if src_idx < len(rms_db):
                    active_rms.append(rms_db[src_idx])

        if active_peaks:
            self._peak_lbl.setText(f"{max(active_peaks):.1f} dBFS")
        if active_rms:
            self._rms_lbl.setText(f"{max(active_rms):.1f} dBFS")

        self._lufsm_lbl.setText(f"{lufs_m:.1f} LUFS" if lufs_m is not None else "—")
        self._lufss_lbl.setText(f"{lufs_s:.1f} LUFS" if lufs_s is not None else "—")
        self._lufsi_lbl.setText(f"{lufs_i:.1f} LUFS" if lufs_i is not None else "—")

    @property
    def current_mode(self) -> str:
        return self._mode

    @property
    def channel_count(self) -> int:
        count, _ = MASTER_MODES.get(self._mode, (len(self._meter_bars), []))
        return count if self._mode != "Custom" else len(self._meter_bars)

    def clear(self) -> None:
        """Reset all meter bars and LUFS labels to idle state."""
        for bar in self._meter_bars:
            bar.set_level(-120.0, -120.0, False)
        self._peak_lbl.setText("\u2014")
        self._rms_lbl.setText("\u2014")
        self._lufsm_lbl.setText("\u2014")
        self._lufss_lbl.setText("\u2014")
        self._lufsi_lbl.setText("\u2014")
