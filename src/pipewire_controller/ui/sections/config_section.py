# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2024 Andrianos Papamarkou
"""Configuration accordion section — preset selector and manager launcher."""

from __future__ import annotations

from PyQt6.QtCore import pyqtSignal
from PyQt6.QtWidgets import (
    QComboBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from ..theme import TEXT_DIM, TEXT_LABEL

_LABEL_STYLE = (
    f"color: {TEXT_LABEL}; font-size: 10px; font-weight: bold; "
    f"background: transparent; letter-spacing: 0.5px;"
)
_DIM_STYLE = f"color: {TEXT_DIM}; font-size: 10px; background: transparent;"


class ConfigSection(QWidget):
    """Content widget for the Configuration accordion section."""

    save_requested = pyqtSignal()
    manage_requested = pyqtSignal()
    preset_selected = pyqtSignal(str)  # preset name

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._build_ui()

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 6, 8, 6)
        layout.setSpacing(6)

        lbl = QLabel("CONFIGURATION")
        lbl.setStyleSheet(_LABEL_STYLE)
        layout.addWidget(lbl)

        self._preset_combo = QComboBox()
        self._preset_combo.currentTextChanged.connect(self.preset_selected)
        layout.addWidget(self._preset_combo)

        desc_lbl = QLabel("Description:")
        desc_lbl.setStyleSheet(_DIM_STYLE)
        layout.addWidget(desc_lbl)

        self._desc_edit = QLineEdit()
        self._desc_edit.setPlaceholderText("Optional description…")
        self._desc_edit.setReadOnly(True)
        layout.addWidget(self._desc_edit)

        btn_row = QHBoxLayout()
        save_btn = QPushButton("Save")
        save_btn.clicked.connect(self.save_requested)
        manage_btn = QPushButton("Manage…")
        manage_btn.clicked.connect(self.manage_requested)
        btn_row.addWidget(save_btn)
        btn_row.addWidget(manage_btn)
        layout.addLayout(btn_row)

    def populate_presets(self, names: list[str], active: str) -> None:
        self._preset_combo.blockSignals(True)
        self._preset_combo.clear()
        for name in names:
            self._preset_combo.addItem(name)
        idx = self._preset_combo.findText(active)
        if idx >= 0:
            self._preset_combo.setCurrentIndex(idx)
        self._preset_combo.blockSignals(False)

    def set_description(self, text: str) -> None:
        self._desc_edit.setText(text)
