# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2024 Andrianos Papamarkou
"""
Audio analysis engine — Peak, RMS, LUFS metering.

This module is completely independent of Qt and PipeWire.
All analysis functions operate on numpy arrays and can be tested
with synthetic signals without any hardware.

Metering standards:
- Peak: instantaneous sample maximum (linear and dBFS)
- RMS: root-mean-square over a window (power average)
- LUFS-M: momentary loudness (400ms window, K-weighting)
- LUFS-S: short-term loudness (3s window, K-weighting)
- LUFS-I: integrated loudness (gated, per ITU-R BS.1770-4)

K-weighting:
  Stage 1: High-shelf pre-filter (+4dB above ~2kHz)
  Stage 2: High-pass filter (100Hz, -3dB)
  Applied before mean-square calculation.

Note on LUFS-I gating (ITU-R BS.1770-4):
  - Absolute gate: -70 LUFS
  - Relative gate: -10 LU below ungated mean
  - Blocks: 400ms, 75% overlap
  Only blocks above both gates contribute to the integrated value.
  If insufficient gated blocks exist, LUFS-I is reported as None.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field

import numpy as np

_MINUS_INF_DBFS = -120.0
_LUFS_ABSOLUTE_GATE = -70.0  # dBFS equivalent
_LUFS_RELATIVE_GATE_OFFSET = -10.0  # LU below ungated mean


def linear_to_dbfs(linear: float) -> float:
    """Convert linear amplitude to dBFS. Returns -120.0 for silence."""
    if linear <= 0.0:
        return _MINUS_INF_DBFS
    return max(_MINUS_INF_DBFS, 20.0 * math.log10(linear))


def dbfs_to_linear(dbfs: float) -> float:
    """Convert dBFS to linear amplitude."""
    return 10.0 ** (dbfs / 20.0)


def peak_linear(samples: np.ndarray) -> float:
    """Peak amplitude of a block (linear, 0.0–1.0+)."""
    if len(samples) == 0:
        return 0.0
    return float(np.max(np.abs(samples)))


def peak_dbfs(samples: np.ndarray) -> float:
    """Peak amplitude in dBFS."""
    return linear_to_dbfs(peak_linear(samples))


def rms_linear(samples: np.ndarray) -> float:
    """RMS amplitude of a block (linear)."""
    if len(samples) == 0:
        return 0.0
    return float(np.sqrt(np.mean(samples.astype(np.float64) ** 2)))


def rms_dbfs(samples: np.ndarray) -> float:
    """RMS amplitude in dBFS."""
    return linear_to_dbfs(rms_linear(samples))


# ── K-weighting filters ───────────────────────────────────────────────────────
# Biquad coefficients for K-weighting at common sample rates.
# Pre-computed from ITU-R BS.1770-4 specification.
# Format: (b0, b1, b2, a1, a2) — direct form II transposed

_K_WEIGHT_COEFFS: dict[int, tuple[tuple, tuple]] = {
    # (stage1_shelf, stage2_highpass)
    48000: (
        (
            1.53512485958697,
            -2.69169618940638,
            1.19839281085285,
            -1.69065929318241,
            0.73248077421585,
        ),
        (1.0, -2.0, 1.0, -1.99004745483398, 0.99007225036621),
    ),
    44100: (
        (
            1.53512485958697,
            -2.69169618940638,
            1.19839281085285,
            -1.69065929318241,
            0.73248077421585,
        ),
        (1.0, -2.0, 1.0, -1.98916823196379, 0.98922328390007),
    ),
    96000: (
        (
            1.69065929318241,
            -2.86998072935865,
            1.21282249062498,
            -1.86005000000000,
            0.86005000000000,
        ),
        (1.0, -2.0, 1.0, -1.99502372741792, 0.99503700669784),
    ),
}


def _apply_biquad(samples: np.ndarray, b: tuple, a: tuple) -> np.ndarray:
    """Apply a biquad IIR filter (direct form II transposed)."""
    b0, b1, b2 = b[0], b[1], b[2]
    a1, a2 = a[0], a[1]
    out = np.zeros_like(samples, dtype=np.float64)
    x = samples.astype(np.float64)
    w1, w2 = 0.0, 0.0
    for i in range(len(x)):
        w0 = x[i] - a1 * w1 - a2 * w2
        out[i] = b0 * w0 + b1 * w1 + b2 * w2
        w2 = w1
        w1 = w0
    return out


def k_weight(samples: np.ndarray, sample_rate: int) -> np.ndarray:
    """
    Apply K-weighting filter to mono samples.

    If the sample rate is not in the pre-computed table, returns
    the unfiltered signal (conservative fallback — LUFS will be approximate).
    """
    coeffs = _K_WEIGHT_COEFFS.get(sample_rate)
    if coeffs is None:
        return samples.astype(np.float64)
    shelf_b, shelf_a = coeffs[0][:3], coeffs[0][3:]
    hp_b, hp_a = coeffs[1][:3], coeffs[1][3:]
    stage1 = _apply_biquad(samples, shelf_b, shelf_a)
    stage2 = _apply_biquad(stage1, hp_b, hp_a)
    return stage2


def mean_square_k_weighted(samples: np.ndarray, sample_rate: int) -> float:
    """Mean square of K-weighted signal (used for LUFS calculation)."""
    weighted = k_weight(samples, sample_rate)
    return float(np.mean(weighted**2))


def lufs_from_mean_square(ms: float) -> float:
    """Convert mean square to LUFS value."""
    if ms <= 0.0:
        return _MINUS_INF_DBFS
    return -0.691 + 10.0 * math.log10(ms)


# ── Channel meter state ───────────────────────────────────────────────────────


@dataclass
class ChannelMeter:
    """
    Stateful meter for a single audio channel.

    Accumulates peak hold, maximum, and over detection.
    Thread-safe reads via snapshot() — writes from audio thread only.
    """

    name: str = ""
    node_name: str = ""
    port_name: str = ""
    channel_number: int = 0

    # Current values (updated each block)
    peak_linear: float = 0.0
    rms_linear: float = 0.0

    # Peak hold (latched until clear())
    peak_hold_linear: float = 0.0
    max_linear: float = 0.0  # maximum ever seen
    over: bool = False  # latched over indicator

    def process_block(self, samples: np.ndarray) -> None:
        """Update meter state from a block of samples. Call from audio thread."""
        p = peak_linear(samples)
        r = rms_linear(samples)
        self.peak_linear = p
        self.rms_linear = r
        if p > self.peak_hold_linear:
            self.peak_hold_linear = p
        if p > self.max_linear:
            self.max_linear = p
        if p >= 1.0:
            self.over = True

    def clear(self) -> None:
        """Reset peak hold, max, and over indicator."""
        self.peak_hold_linear = 0.0
        self.max_linear = 0.0
        self.over = False

    @property
    def peak_dbfs(self) -> float:
        return linear_to_dbfs(self.peak_linear)

    @property
    def rms_dbfs(self) -> float:
        return linear_to_dbfs(self.rms_linear)

    @property
    def peak_hold_dbfs(self) -> float:
        return linear_to_dbfs(self.peak_hold_linear)

    @property
    def max_dbfs(self) -> float:
        return linear_to_dbfs(self.max_linear)

    def snapshot(self) -> dict:
        """Return a copy of current state for GUI consumption."""
        return {
            "name": self.name,
            "node_name": self.node_name,
            "port_name": self.port_name,
            "channel_number": self.channel_number,
            "peak_linear": self.peak_linear,
            "rms_linear": self.rms_linear,
            "peak_hold_linear": self.peak_hold_linear,
            "max_linear": self.max_linear,
            "over": self.over,
            "peak_dbfs": self.peak_dbfs,
            "rms_dbfs": self.rms_dbfs,
            "peak_hold_dbfs": self.peak_hold_dbfs,
            "max_dbfs": self.max_dbfs,
        }


# ── LUFS integrated meter ─────────────────────────────────────────────────────

_LUFS_BLOCK_SAMPLES_48K = int(0.4 * 48000)  # 400ms at 48kHz
_LUFS_OVERLAP = 0.75  # 75% overlap → 100ms hop


@dataclass
class LUFSMeter:
    """
    Stateful LUFS meter implementing ITU-R BS.1770-4.

    Supports:
    - LUFS-M (momentary, 400ms)
    - LUFS-S (short-term, 3s)
    - LUFS-I (integrated, gated)

    Call process_block() with mono K-weighted mean-square values.
    Call get_integrated() to retrieve LUFS-I (returns None if insufficient data).
    """

    sample_rate: int = 48000
    _ms_blocks: list[float] = field(default_factory=list)  # 400ms blocks
    _integrated_blocks: list[float] = field(default_factory=list)

    def process_block(self, mean_square: float) -> None:
        """Add a 400ms mean-square block."""
        self._ms_blocks.append(mean_square)
        self._integrated_blocks.append(mean_square)

    def get_momentary(self) -> float | None:
        """LUFS-M: last 400ms block."""
        if not self._ms_blocks:
            return None
        ms = self._ms_blocks[-1]
        val = lufs_from_mean_square(ms)
        return val if val > _MINUS_INF_DBFS else None

    def get_short_term(self) -> float | None:
        """LUFS-S: mean of last 3s worth of 400ms blocks (last 7.5 → use 8)."""
        n_blocks = max(1, int(3.0 / 0.4))  # 7 blocks ≈ 2.8s, 8 ≈ 3.2s
        recent = self._ms_blocks[-n_blocks:]
        if not recent:
            return None
        ms = float(np.mean(recent))
        val = lufs_from_mean_square(ms)
        return val if val > _MINUS_INF_DBFS else None

    def get_integrated(self) -> float | None:
        """
        LUFS-I: gated integrated loudness per ITU-R BS.1770-4.

        Returns None if there are insufficient gated blocks.
        """
        blocks = np.array(self._integrated_blocks)
        if len(blocks) < 2:
            return None

        # Absolute gate: -70 LUFS → mean_square threshold
        abs_threshold_ms = 10 ** ((_LUFS_ABSOLUTE_GATE + 0.691) / 10.0)
        gated_abs = blocks[blocks >= abs_threshold_ms]
        if len(gated_abs) == 0:
            return None

        # Relative gate: -10 LU below ungated mean
        ungated_mean = float(np.mean(gated_abs))
        ungated_lufs = lufs_from_mean_square(ungated_mean)
        rel_threshold_lufs = ungated_lufs + _LUFS_RELATIVE_GATE_OFFSET
        rel_threshold_ms = 10 ** ((rel_threshold_lufs + 0.691) / 10.0)

        gated_rel = gated_abs[gated_abs >= rel_threshold_ms]
        if len(gated_rel) == 0:
            return None

        integrated_ms = float(np.mean(gated_rel))
        val = lufs_from_mean_square(integrated_ms)
        return val if val > _MINUS_INF_DBFS else None

    def reset(self) -> None:
        self._ms_blocks.clear()
        self._integrated_blocks.clear()


# ── Stereo analyzer ───────────────────────────────────────────────────────────

_STEREO_WINDOW = 4096  # samples for correlation window
_GONIODATA_SIZE = 512  # max points sent to UI per frame


@dataclass
class StereoSnapshot:
    """Compact stereo measurement for GUI consumption."""

    correlation: float  # -1.0 … +1.0
    gonio_xy: np.ndarray  # shape (N, 2) float32, M on x-axis, S on y-axis
    was_reset: bool = False  # True on the first snapshot after reset()


class StereoAnalyzer:
    """
    Stateful stereo analyzer: correlation + goniometer data.

    DSP runs in the audio capture thread via process_block().
    snapshot() returns a compact StereoSnapshot for the GUI thread.

    Correlation formula (Pearson over a rolling window)::

        corr = sum(L*R) / sqrt(sum(L²) * sum(R²))

    Goniometer uses M/S rotation::

        M = (L + R) / sqrt(2)   (x-axis)
        S = (L - R) / sqrt(2)   (y-axis)
    """

    _SQRT2 = math.sqrt(2.0)

    def __init__(self, window: int = _STEREO_WINDOW) -> None:
        self._window = window
        self._buf_l = np.zeros(window, dtype=np.float32)
        self._buf_r = np.zeros(window, dtype=np.float32)
        self._write_pos = 0
        self._filled = 0
        # Goniometer accumulation between snapshots
        self._gonio_acc: list[tuple[float, float]] = []
        self._correlation: float = 0.0
        self._was_reset: bool = True

    def process_block(self, left: np.ndarray, right: np.ndarray) -> None:
        """Feed a block of L/R samples. Call from audio thread."""
        n = len(left)
        if n == 0:
            return
        self._was_reset = False
        # Ring-buffer fill
        space = self._window - self._write_pos
        if n >= space:
            self._buf_l[self._write_pos :] = left[:space]
            self._buf_r[self._write_pos :] = right[:space]
            remainder = n - space
            if remainder > 0:
                take = min(remainder, self._window)
                self._buf_l[:take] = left[space : space + take]
                self._buf_r[:take] = right[space : space + take]
                self._write_pos = take
            else:
                self._write_pos = 0
        else:
            self._buf_l[self._write_pos : self._write_pos + n] = left
            self._buf_r[self._write_pos : self._write_pos + n] = right
            self._write_pos += n
        self._filled = min(self._filled + n, self._window)

        # Correlation over current window
        if self._filled >= 64:
            buf_l = self._buf_l[: self._filled]
            buf_r = self._buf_r[: self._filled]
            lr = float(np.dot(buf_l.astype(np.float64), buf_r.astype(np.float64)))
            ll = float(np.dot(buf_l.astype(np.float64), buf_l.astype(np.float64)))
            rr = float(np.dot(buf_r.astype(np.float64), buf_r.astype(np.float64)))
            denom = math.sqrt(ll * rr)
            self._correlation = max(-1.0, min(1.0, lr / denom)) if denom > 1e-12 else 0.0

        # Accumulate goniometer points (decimated)
        step = max(1, n // 64)
        l_dec = left[::step].astype(np.float64)
        r_dec = right[::step].astype(np.float64)
        m = (l_dec + r_dec) / self._SQRT2
        s = (l_dec - r_dec) / self._SQRT2
        for mx, sy in zip(m.tolist(), s.tolist()):
            self._gonio_acc.append((mx, sy))
        # Cap accumulation to avoid unbounded growth
        if len(self._gonio_acc) > _GONIODATA_SIZE * 4:
            self._gonio_acc = self._gonio_acc[-_GONIODATA_SIZE * 2 :]

    def snapshot(self) -> StereoSnapshot:
        """Return current measurements and clear goniometer accumulation."""
        was_reset = self._was_reset
        pts = self._gonio_acc[-_GONIODATA_SIZE:]
        self._gonio_acc.clear()
        if pts:
            xy = np.array(pts, dtype=np.float32)
        else:
            xy = np.empty((0, 2), dtype=np.float32)
        return StereoSnapshot(correlation=self._correlation, gonio_xy=xy, was_reset=was_reset)

    def reset(self) -> None:
        self._buf_l[:] = 0.0
        self._buf_r[:] = 0.0
        self._write_pos = 0
        self._filled = 0
        self._gonio_acc.clear()
        self._correlation = 0.0
        self._was_reset = True
