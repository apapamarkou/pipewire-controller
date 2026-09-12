# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2024 Andrianos Papamarkou
"""Reusable flat button without default QPushButton chrome."""

from __future__ import annotations

from PyQt6.QtWidgets import QPushButton, QWidget


class FlatButton(QPushButton):
    """QPushButton with no extra chrome — styled entirely by caller."""

    def __init__(self, text: str = "", parent: QWidget | None = None) -> None:
        super().__init__(text, parent)
        self.setFlat(True)
        self.setCursor(self.cursor())
