# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2024 Andrianos Papamarkou
"""
Stereo analysis widgets: CorrelationMeterWidget and GoniometerWidget.

Both widgets receive pre-processed values from the audio thread — no DSP
is performed inside paintEvent().
"""

from __future__ import annotations

import math

import numpy as np
from PyQt6.QtCore import QTimer
from PyQt6.QtGui import QColor, QPainter, QPen
from PyQt6.QtWidgets import QSizePolicy, QWidget

from ..theme import (
    BG_WIDGET,
    BORDER,
    C_ERROR,
    C_METER_LOW,
    C_METER_MID,
    C_OK,
    TEXT_DIM,
    TEXT_LABEL,
)

# ── Correlation meter ─────────────────────────────────────────────────────────

_CORR_BG = QColor(BG_WIDGET)
_CORR_BORDER = QColor(BORDER)
_CORR_NEG = QColor(C_ERROR)  # red  — anti-correlated
_CORR_ZERO = QColor(C_METER_MID)  # amber — uncorrelated
_CORR_POS = QColor(C_METER_LOW)  # green — correlated
_CORR_PEAK = QColor("#ffffff")
_CORR_LABEL = QColor(TEXT_LABEL)
_CORR_DIM = QColor(TEXT_DIM)

_SMOOTH = 0.25  # IIR smoothing coefficient (lower = smoother)


def _lerp_color(a: QColor, b: QColor, t: float) -> QColor:
    t = max(0.0, min(1.0, t))
    return QColor(
        int(a.red() + (b.red() - a.red()) * t),
        int(a.green() + (b.green() - a.green()) * t),
        int(a.blue() + (b.blue() - a.blue()) * t),
    )


def _corr_color(value: float) -> QColor:
    """Map correlation [-1, +1] to a color: red → amber → green."""
    if value < 0.0:
        return _lerp_color(_CORR_NEG, _CORR_ZERO, value + 1.0)
    return _lerp_color(_CORR_ZERO, _CORR_POS, value)


class CorrelationMeterWidget(QWidget):
    """
    Horizontal stereo phase correlation meter.

    Scale: -1 (left) to +1 (right), 0 at center.
    Color: red (anti-phase) → amber (uncorrelated) → green (in-phase).
    White tick shows minimum-hold (worst correlation seen recently).
    """

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._value: float = 0.0  # smoothed display value
        self._raw: float = 0.0  # latest raw value
        self._peak_min: float = 0.0  # minimum hold (worst correlation)
        self._peak_min_timer = 0  # countdown frames before releasing hold
        self._HOLD_FRAMES = 60  # ~2s at 30fps
        self.setMinimumSize(60, 18)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.setFixedHeight(22)

    # ── Public API ────────────────────────────────────────────────────────────

    def set_correlation(self, value: float) -> None:
        """Update correlation value. Call from GUI thread (via QTimer)."""
        self._raw = max(-1.0, min(1.0, value))
        # IIR smoothing
        self._value += _SMOOTH * (self._raw - self._value)
        # Minimum hold (tracks worst/most negative correlation)
        if self._raw < self._peak_min:
            self._peak_min = self._raw
            self._peak_min_timer = self._HOLD_FRAMES
        elif self._peak_min_timer > 0:
            self._peak_min_timer -= 1
        else:
            # Slowly release toward current value
            self._peak_min += 0.02
            self._peak_min = min(self._peak_min, self._value)
        self.update()

    def set_peak(self, value: float) -> None:
        """Manually set the peak/hold indicator."""
        self._peak_min = max(-1.0, min(1.0, value))
        self._peak_min_timer = self._HOLD_FRAMES
        self.update()

    def reset(self) -> None:
        self._value = 0.0
        self._raw = 0.0
        self._peak_min = 0.0
        self._peak_min_timer = 0
        self.update()

    # ── Rendering ─────────────────────────────────────────────────────────────

    def paintEvent(self, event) -> None:  # noqa: N802
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing, False)
        w, h = self.width(), self.height()

        # Background + border
        p.fillRect(0, 0, w, h, _CORR_BG)
        p.setPen(QPen(_CORR_BORDER, 1))
        p.drawRect(0, 0, w - 1, h - 1)

        inner_w = w - 2
        inner_h = h - 2
        cx = w // 2  # pixel position of 0

        # Fill bar from center to current value
        val_x = int((self._value + 1.0) / 2.0 * inner_w) + 1
        bar_color = _corr_color(self._value)

        if val_x < cx:
            p.fillRect(val_x, 1, cx - val_x, inner_h, bar_color)
        elif val_x > cx:
            p.fillRect(cx, 1, val_x - cx, inner_h, bar_color)

        # Center line
        p.setPen(QPen(_CORR_LABEL, 1))
        p.drawLine(cx, 1, cx, h - 2)

        # Tick marks at -1, -0.5, 0, +0.5, +1
        p.setPen(QPen(_CORR_DIM, 1))
        for tick in (-1.0, -0.5, 0.0, 0.5, 1.0):
            tx = int((tick + 1.0) / 2.0 * inner_w) + 1
            p.drawLine(tx, h - 4, tx, h - 2)

        # Minimum-hold tick (white)
        if self._peak_min < self._value - 0.02:
            ph_x = int((self._peak_min + 1.0) / 2.0 * inner_w) + 1
            ph_x = max(1, min(w - 2, ph_x))
            p.setPen(QPen(_CORR_PEAK, 2))
            p.drawLine(ph_x, 1, ph_x, h - 2)

        p.end()


# ── Goniometer / Vectorscope ──────────────────────────────────────────────────

_GONIO_BG = QColor("#0a0a0a")
_GONIO_GRID = QColor("#1e1e1e")
_GONIO_AXIS = QColor("#2a2a2a")
_GONIO_DOT_BASE = QColor(C_OK)  # green dots
_GONIO_LABEL = QColor(TEXT_DIM)

_DECAY = 0.75  # per-frame fade factor for persistence image
_GONIO_REFRESH_MS = 33  # ~30 fps


class GoniometerWidget(QWidget):
    """
    Real-time stereo goniometer / vectorscope.

    Receives M/S point arrays from the audio thread via push_points().
    Maintains a fading persistence image — no per-sample Qt operations.

    Coordinate convention:
        x-axis = M (Mid)  — mono/center signal → vertical line
        y-axis = S (Side) — stereo width       → horizontal spread
    The display is rotated 45° so that:
        pure mono  → vertical line
        wide stereo → diagonal spread
        anti-phase  → horizontal line
    """

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._points: np.ndarray = np.empty((0, 2), dtype=np.float32)
        self._img_buf: np.ndarray | None = None  # RGBA accumulation buffer
        self._img_w = 0
        self._img_h = 0
        self.setMinimumSize(80, 80)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)

        self._timer = QTimer(self)
        self._timer.setInterval(_GONIO_REFRESH_MS)
        self._timer.timeout.connect(self._tick)
        self._timer.start()

    # ── Public API ────────────────────────────────────────────────────────────

    def push_points(self, xy: np.ndarray) -> None:
        """
        Receive new M/S points from the audio thread.
        xy: shape (N, 2) float32, column 0 = M, column 1 = S.
        """
        self._points = xy  # replace; _tick will consume

    def reset(self) -> None:
        self._points = np.empty((0, 2), dtype=np.float32)
        self._img_buf = None
        self.update()

    # ── Internal rendering ────────────────────────────────────────────────────

    def _ensure_buf(self) -> None:
        w, h = self.width(), self.height()
        if w < 4 or h < 4:
            return
        if self._img_buf is None or self._img_w != w or self._img_h != h:
            self._img_buf = np.zeros((h, w, 4), dtype=np.uint8)
            self._img_w = w
            self._img_h = h

    def _tick(self) -> None:
        """Advance persistence decay and paint new points."""
        self._ensure_buf()
        if self._img_buf is None:
            return

        w, h = self._img_w, self._img_h
        buf = self._img_buf

        # Decay: fade existing content toward black
        buf[:, :, :3] = (buf[:, :, :3].astype(np.uint16) * int(_DECAY * 256) >> 8).astype(np.uint8)
        buf[:, :, 3] = 255  # keep alpha opaque

        pts = self._points
        if len(pts) > 0:
            # Normalize: map M/S [-1,1] to pixel coords
            # M → x (center = w/2), S → y (center = h/2, inverted)
            # Scale so that ±1 reaches ~90% of half-size
            scale = min(w, h) * 0.45
            cx, cy = w / 2.0, h / 2.0

            # Rotate 45° for classic goniometer look:
            # display_x = (M - S) / sqrt2, display_y = (M + S) / sqrt2
            # but since M and S are already rotated from L/R, we just use M→x, S→y
            # and rotate the display 45° by swapping:
            #   px = cx + (M - S) * scale / sqrt2
            #   py = cy - (M + S) * scale / sqrt2
            sqrt2 = math.sqrt(2.0)
            m = pts[:, 0].astype(np.float64)
            s = pts[:, 1].astype(np.float64)
            px = (cx + (m - s) * scale / sqrt2).astype(np.int32)
            py = (cy - (m + s) * scale / sqrt2).astype(np.int32)

            # Clip to buffer bounds
            mask = (px >= 0) & (px < w) & (py >= 0) & (py < h)
            px, py = px[mask], py[mask]

            # Accumulate: add brightness to hit pixels
            np.add.at(buf[:, :, 1], (py, px), 80)  # green channel
            np.add.at(buf[:, :, 0], (py, px), 20)  # slight blue tint
            buf[:, :, :3] = np.clip(buf[:, :, :3], 0, 255)

        self.update()

    def paintEvent(self, event) -> None:  # noqa: N802
        p = QPainter(self)
        w, h = self.width(), self.height()

        p.fillRect(0, 0, w, h, _GONIO_BG)

        # Grid circles
        p.setPen(QPen(_GONIO_GRID, 1))
        cx, cy = w // 2, h // 2
        for r_frac in (0.33, 0.66, 1.0):
            r = int(min(w, h) * 0.45 * r_frac)
            p.drawEllipse(cx - r, cy - r, r * 2, r * 2)

        # Diagonal axes (L, R, M, S)
        p.setPen(QPen(_GONIO_AXIS, 1))
        half = int(min(w, h) * 0.45)
        p.drawLine(cx, cy - half, cx, cy + half)  # vertical (M axis)
        p.drawLine(cx - half, cy, cx + half, cy)  # horizontal (S axis)
        p.drawLine(cx - half, cy - half, cx + half, cy + half)  # L diagonal
        p.drawLine(cx - half, cy + half, cx + half, cy - half)  # R diagonal

        # Axis labels
        p.setPen(QPen(_GONIO_LABEL, 1))
        font = p.font()
        font.setPixelSize(9)
        p.setFont(font)
        p.drawText(cx + 2, cy - half + 10, "M")
        p.drawText(cx - half + 2, cy - 2, "L")
        p.drawText(cx + half - 10, cy - 2, "R")

        # Persistence image
        if self._img_buf is not None and self._img_w == w and self._img_h == h:
            from PyQt6.QtGui import QImage

            img = QImage(
                self._img_buf.data,
                w,
                h,
                w * 4,
                QImage.Format.Format_RGBA8888,
            )
            p.setCompositionMode(QPainter.CompositionMode.CompositionMode_Plus)
            p.drawImage(0, 0, img)

        p.end()

    def resizeEvent(self, event) -> None:  # noqa: N802
        self._img_buf = None  # force re-allocation on next tick
        super().resizeEvent(event)
