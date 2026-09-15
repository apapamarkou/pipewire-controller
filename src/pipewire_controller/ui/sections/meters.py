# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2024 Andrianos Papamarkou
"""
Input / Output meter sections.

These sections display real-time level meters for audio channels.
The GUI receives pre-processed meter snapshots — it never performs
audio analysis itself.
"""

from __future__ import annotations

from PyQt6.QtCore import Qt, QTimer, pyqtSignal
from PyQt6.QtWidgets import (
    QHBoxLayout,
    QInputDialog,
    QLabel,
    QMenu,
    QPushButton,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from ...metering import ChannelMeter
from ..components.combo_box import NoScrollComboBox
from ..components.meter_bar import MeterBar
from ..theme import C_ERROR, TEXT_DIM, TEXT_LABEL, TEXT_PRIMARY

_LABEL_STYLE = (
    f"color: {TEXT_LABEL}; font-size: 10px; font-weight: bold; "
    f"background: transparent; letter-spacing: 0.5px;"
)
_DIM_STYLE = f"color: {TEXT_DIM}; font-size: 10px; background: transparent;"
_VALUE_STYLE = f"color: {TEXT_PRIMARY}; font-size: 10px; background: transparent;"
_OVER_STYLE = f"color: {C_ERROR}; font-size: 10px; font-weight: bold; background: transparent;"

_BAR_HEIGHT = 70  # fixed px — prevents collapse inside QScrollArea
_WIDGET_WIDTH = 20  # bar(12) + 4px padding each side
_LABEL_HOLD_DB = -120.0  # below this, show "—"
_LABEL_LAZY_MS = 3000  # ms before label drops to a lower level


class ChannelMeterWidget(QWidget):
    """
    Compact channel meter: bar + name + level value + over indicator.

    The numeric level label is "lazy": it updates immediately when the level
    rises, but only drops to a lower value after _LABEL_LAZY_MS of no higher
    reading (3 seconds by default).

    Right-click to rename.
    """

    rename_requested = pyqtSignal(str)  # channel name

    def __init__(self, meter: ChannelMeter, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._meter = meter
        self._displayed_db: float = _LABEL_HOLD_DB  # value currently shown
        self._pending_db: float = _LABEL_HOLD_DB  # lower candidate waiting for timer
        self._lazy_timer = QTimer(self)
        self._lazy_timer.setSingleShot(True)
        self._lazy_timer.setInterval(_LABEL_LAZY_MS)
        self._lazy_timer.timeout.connect(self._apply_pending_db)
        self._build_ui()

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(2, 2, 2, 2)
        layout.setSpacing(2)
        layout.setAlignment(Qt.AlignmentFlag.AlignHCenter)
        self.setFixedWidth(_WIDGET_WIDTH)

        self._bar = MeterBar()
        self._bar.setFixedHeight(_BAR_HEIGHT)
        layout.addWidget(self._bar)

        self._name_lbl = QLabel(self._meter.name or "—")
        self._name_lbl.setStyleSheet(_DIM_STYLE)
        self._name_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._name_lbl.setFixedWidth(_WIDGET_WIDTH - 4)
        layout.addWidget(self._name_lbl)

        self._level_lbl = QLabel("—")
        self._level_lbl.setStyleSheet(_VALUE_STYLE)
        self._level_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._level_lbl.setFixedWidth(_WIDGET_WIDTH - 4)
        layout.addWidget(self._level_lbl)

        self._over_lbl = QLabel("OVR")
        self._over_lbl.setStyleSheet(_OVER_STYLE)
        self._over_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._over_lbl.setVisible(False)
        layout.addWidget(self._over_lbl)

        self.setToolTip(self._make_tooltip())
        self.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.customContextMenuRequested.connect(self._show_context_menu)

    def _make_tooltip(self, snap: dict | None = None) -> str:
        m = self._meter
        parts = []
        if m.node_name:
            parts.append(f"Device: {m.node_name}")
        parts.append(f"Channel: {m.name or '?'}")
        if m.channel_number is not None:
            parts.append(f"Ch#: {m.channel_number}")
        if snap:
            parts.append(f"Peak: {snap['peak_dbfs']:.1f} dBFS")
            parts.append(f"RMS:  {snap['rms_dbfs']:.1f} dBFS")
            parts.append(f"Hold: {snap['peak_hold_dbfs']:.1f} dBFS")
            if snap["over"]:
                parts.append("⚠ OVER")
        return "\n".join(parts)

    def update_from_snapshot(self, snap: dict) -> None:
        self._bar.set_level(snap["peak_dbfs"], snap["peak_hold_dbfs"], snap["over"])
        db = snap["peak_dbfs"]
        self._over_lbl.setVisible(snap["over"])
        self._name_lbl.setText(snap["name"] or "—")
        self.setToolTip(self._make_tooltip(snap))
        self._update_label_lazy(db)

    def _update_label_lazy(self, db: float) -> None:
        """Update the level label: immediate on rise, 3s hold before drop."""
        if db >= self._displayed_db:
            # Level rose or stayed — update immediately, cancel any pending drop
            self._displayed_db = db
            self._pending_db = db
            self._lazy_timer.stop()
            self._level_lbl.setText(f"{db:.1f}" if db > _LABEL_HOLD_DB else "—")
        else:
            # Level fell — track the new low as a candidate but don't display yet
            self._pending_db = db
            if not self._lazy_timer.isActive():
                self._lazy_timer.start()

    def _apply_pending_db(self) -> None:
        """Called after the hold timeout — drop displayed value to current pending."""
        self._displayed_db = self._pending_db
        db = self._pending_db
        self._level_lbl.setText(f"{db:.1f}" if db > _LABEL_HOLD_DB else "—")

    def mousePressEvent(self, event) -> None:
        super().mousePressEvent(event)

    def _show_context_menu(self, pos) -> None:
        menu = QMenu(self)
        rename_action = menu.addAction("Rename…")
        rename_action.triggered.connect(self._do_rename)
        menu.exec(self.mapToGlobal(pos))

    def _do_rename(self) -> None:
        new_name, ok = QInputDialog.getText(
            self, "Rename Channel", "Channel name:", text=self._meter.name
        )
        if ok and new_name.strip():
            self._meter.name = new_name.strip()
            self._name_lbl.setText(self._meter.name)
            self.setToolTip(self._make_tooltip())
            self.rename_requested.emit(self._meter.name)


class MeterSection(QWidget):
    """
    Base class for Input/Output meter sections.

    Displays a row of ChannelMeterWidgets with mode selector and clear button.
    One widget per node (showing the node's peak across all its channels).
    """

    clear_requested = pyqtSignal()
    mode_changed = pyqtSignal(str)

    def __init__(self, title: str, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._title = title
        self._channel_widgets: list[ChannelMeterWidget] = []
        self._build_ui()

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(6, 4, 6, 4)
        layout.setSpacing(4)

        ctrl = QHBoxLayout()
        lbl = QLabel(self._title)
        lbl.setStyleSheet(_LABEL_STYLE)
        ctrl.addWidget(lbl)
        ctrl.addStretch()

        self._mode_combo = NoScrollComboBox()
        self._mode_combo.addItems(["Peak", "RMS"])
        self._mode_combo.setFixedWidth(60)
        self._mode_combo.currentTextChanged.connect(self.mode_changed)
        ctrl.addWidget(self._mode_combo)

        clear_btn = QPushButton("CLEAR")
        clear_btn.clicked.connect(self._on_clear)
        ctrl.addWidget(clear_btn)
        layout.addLayout(ctrl)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll.setFixedHeight(_BAR_HEIGHT + 50)  # bar + labels

        self._meters_widget = QWidget()
        self._meters_layout = QHBoxLayout(self._meters_widget)
        self._meters_layout.setContentsMargins(0, 0, 0, 0)
        self._meters_layout.setSpacing(2)
        self._meters_layout.addStretch()

        scroll.setWidget(self._meters_widget)
        layout.addWidget(scroll)
        self._scroll = scroll

        self._empty_lbl = QLabel("No audio devices found")
        self._empty_lbl.setStyleSheet(_DIM_STYLE)
        layout.addWidget(self._empty_lbl)
        self._empty_lbl.setVisible(True)

    def set_mode(self, mode: str) -> None:
        self._mode_combo.blockSignals(True)
        self._mode_combo.setCurrentText(mode)
        self._mode_combo.blockSignals(False)

    def set_channels(self, meters: list[ChannelMeter]) -> None:
        """Rebuild channel widgets. One ChannelMeter = one bar (one per node)."""
        while self._meters_layout.count() > 1:
            item = self._meters_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        self._channel_widgets.clear()

        for m in meters:
            w = ChannelMeterWidget(m)
            self._meters_layout.insertWidget(self._meters_layout.count() - 1, w)
            self._channel_widgets.append(w)

        has = len(meters) > 0
        self._empty_lbl.setVisible(not has)
        self._scroll.setVisible(has)

    def update_meters(self, snapshots: list[dict]) -> None:
        """Update meter displays from pre-processed snapshots. Call from GUI thread."""
        mode = self._mode_combo.currentText()
        for i, snap in enumerate(snapshots):
            if i >= len(self._channel_widgets):
                break
            if mode == "RMS":
                display_snap = dict(snap)
                display_snap["peak_dbfs"] = snap["rms_dbfs"]
                self._channel_widgets[i].update_from_snapshot(display_snap)
            else:
                self._channel_widgets[i].update_from_snapshot(snap)

    def _on_clear(self) -> None:
        for w in self._channel_widgets:
            w._meter.clear()
            w._bar.set_level(-120.0, -120.0, False)
            w._level_lbl.setText("—")
            w._over_lbl.setVisible(False)
            w._displayed_db = _LABEL_HOLD_DB
            w._pending_db = _LABEL_HOLD_DB
            w._lazy_timer.stop()
        self.clear_requested.emit()


class InputMeterSection(MeterSection):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__("INPUTS", parent)


class OutputMeterSection(MeterSection):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__("OUTPUTS", parent)
