# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2024 Andrianos Papamarkou
"""
Level meter bar widget — vertical dBFS meter with peak hold.

Used by input/output meter sections and master meter.
"""

from __future__ import annotations

from PyQt6.QtGui import QColor, QPainter, QPen
from PyQt6.QtWidgets import QSizePolicy, QWidget

from ..theme import C_METER_BG, C_METER_CLIP, C_METER_LOW, C_METER_MID, C_METER_PEAK

_DB_MIN = -60.0
_DB_MAX = 0.0
_DB_CLIP = 0.0
_DB_WARN = -6.0  # yellow zone starts here


def _db_to_frac(db: float) -> float:
    """Map dBFS to 0.0–1.0 position on the meter bar."""
    db = max(_DB_MIN, min(_DB_MAX, db))
    return (db - _DB_MIN) / (_DB_MAX - _DB_MIN)


class MeterBar(QWidget):
    """
    Vertical level meter bar.

    Displays:
    - Green fill up to -6 dBFS
    - Yellow fill from -6 to 0 dBFS
    - Red fill / clip indicator at 0 dBFS
    - White peak-hold tick
    """

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._level_db: float = _DB_MIN
        self._peak_hold_db: float = _DB_MIN
        self._over: bool = False
        self.setMinimumWidth(8)
        self.setMinimumHeight(60)
        self.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Expanding)
        self.setFixedWidth(12)

    def set_level(self, level_db: float, peak_hold_db: float, over: bool) -> None:
        self._level_db = level_db
        self._peak_hold_db = peak_hold_db
        self._over = over
        self.update()

    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, False)

        w = self.width()
        h = self.height()

        # Background
        painter.fillRect(0, 0, w, h, QColor(C_METER_BG))

        # Level fill
        level_frac = _db_to_frac(self._level_db)
        fill_h = int(level_frac * h)
        fill_y = h - fill_h

        if fill_h > 0:
            warn_frac = _db_to_frac(_DB_WARN)
            warn_y = h - int(warn_frac * h)

            if self._over:
                painter.fillRect(0, fill_y, w, fill_h, QColor(C_METER_CLIP))
            elif fill_y < warn_y:
                # Split: green below warn, yellow above
                painter.fillRect(0, warn_y, w, h - warn_y, QColor(C_METER_LOW))
                painter.fillRect(0, fill_y, w, warn_y - fill_y, QColor(C_METER_MID))
            else:
                painter.fillRect(0, fill_y, w, fill_h, QColor(C_METER_LOW))

        # Peak hold tick
        if self._peak_hold_db > _DB_MIN:
            ph_frac = _db_to_frac(self._peak_hold_db)
            ph_y = h - int(ph_frac * h) - 1
            ph_y = max(0, min(h - 1, ph_y))
            painter.setPen(QPen(QColor(C_METER_PEAK), 1))
            painter.drawLine(0, ph_y, w - 1, ph_y)

        painter.end()
