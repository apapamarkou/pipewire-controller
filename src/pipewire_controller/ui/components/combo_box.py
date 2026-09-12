# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2024 Andrianos Papamarkou
"""QComboBox that ignores mouse wheel events."""

from __future__ import annotations

from PyQt6.QtWidgets import QComboBox


class NoScrollComboBox(QComboBox):
    def wheelEvent(self, event) -> None:
        event.ignore()
