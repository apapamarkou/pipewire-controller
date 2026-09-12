# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2024 Andrianos Papamarkou
"""Accordion section widget — collapsible panel section."""

from __future__ import annotations

from PyQt6.QtCore import pyqtSignal
from PyQt6.QtWidgets import QSizePolicy, QVBoxLayout, QWidget

from ..ui.components.flat_button import FlatButton
from .theme import SECTION_HEADER_STYLE


class AccordionSection(QWidget):
    """A collapsible section with a header button and content area."""

    toggled = pyqtSignal(bool)  # emits expanded state

    def __init__(self, title: str, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._expanded = True
        self._title = title

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        self._header = FlatButton(f"▾  {title.upper()}")
        self._header.setStyleSheet(SECTION_HEADER_STYLE)
        self._header.setCheckable(False)
        self._header.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self._header.clicked.connect(self._toggle)
        layout.addWidget(self._header)

        self._body = QWidget()
        body_layout = QVBoxLayout(self._body)
        body_layout.setContentsMargins(0, 0, 0, 0)
        body_layout.setSpacing(0)
        layout.addWidget(self._body)

        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Maximum)

    def set_content(self, widget: QWidget) -> None:
        self._body.layout().addWidget(widget)

    def add_widget(self, widget: QWidget) -> None:
        self._body.layout().addWidget(widget)

    def set_expanded(self, expanded: bool) -> None:
        self._expanded = expanded
        self._body.setVisible(expanded)
        arrow = "▾" if expanded else "▸"
        self._header.setText(f"{arrow}  {self._title.upper()}")

    def is_expanded(self) -> bool:
        return self._expanded

    def _toggle(self) -> None:
        self.set_expanded(not self._expanded)
        self.toggled.emit(self._expanded)
