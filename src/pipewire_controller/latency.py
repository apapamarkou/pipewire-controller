# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2024 Andrianos Papamarkou
"""
Latency measurement — signal analysis core.

This module is completely independent of Qt and PipeWire.
It can be tested with synthetic signals without any hardware.

Algorithm:
- Generate a known test signal (swept sine / chirp)
- Cross-correlate the recorded signal with the original
- The peak of the cross-correlation gives the sample delay
- Convert samples → milliseconds using the sample rate

Design notes:
- Cross-correlation is used rather than wall-clock timing because it is
  sample-accurate and immune to OS scheduling jitter.
- A chirp (frequency sweep) is used rather than a single tone because it
  has good autocorrelation properties (low sidelobes) and is broadband,
  making it robust to frequency-dependent filtering in the signal path.
- Multiple measurements are averaged to improve stability.
"""

from __future__ import annotations

import numpy as np


def generate_chirp(
    duration_s: float,
    sample_rate: int,
    f_start: float = 200.0,
    f_end: float = 4000.0,
    amplitude: float = 0.5,
) -> np.ndarray:
    """
    Generate a linear frequency sweep (chirp) signal.

    Args:
        duration_s: Duration in seconds.
        sample_rate: Sample rate in Hz.
        f_start: Start frequency in Hz.
        f_end: End frequency in Hz.
        amplitude: Peak amplitude (0.0–1.0).

    Returns:
        1-D float32 array of samples.
    """
    n = int(duration_s * sample_rate)
    t = np.linspace(0, duration_s, n, endpoint=False)
    # Linear chirp: instantaneous frequency increases linearly
    k = (f_end - f_start) / duration_s
    phase = 2 * np.pi * (f_start * t + 0.5 * k * t**2)
    signal = amplitude * np.sin(phase).astype(np.float32)
    # Apply Hann window to reduce spectral leakage at edges
    window = np.hanning(n).astype(np.float32)
    return signal * window


def estimate_delay_samples(
    reference: np.ndarray,
    recorded: np.ndarray,
    max_delay_samples: int | None = None,
) -> tuple[int, float]:
    """
    Estimate the delay between reference and recorded signals using
    normalized cross-correlation.

    Args:
        reference: The original transmitted signal.
        recorded: The received/recorded signal (may be longer).
        max_delay_samples: Maximum delay to search (None = full length).

    Returns:
        (delay_samples, confidence) where confidence is 0.0–1.0.
        confidence is the normalized peak correlation value.
    """
    if len(reference) == 0 or len(recorded) == 0:
        return 0, 0.0

    ref = reference.astype(np.float64)
    rec = recorded.astype(np.float64)

    # Normalize to unit energy
    ref_energy = np.sqrt(np.sum(ref**2))
    rec_energy = np.sqrt(np.sum(rec**2))
    if ref_energy < 1e-10 or rec_energy < 1e-10:
        return 0, 0.0

    ref = ref / ref_energy
    rec = rec / rec_energy

    # Cross-correlation via FFT (O(n log n))
    n = len(ref) + len(rec) - 1
    fft_size = 1 << (n - 1).bit_length()  # next power of 2

    ref_fft = np.fft.rfft(ref, n=fft_size)
    rec_fft = np.fft.rfft(rec, n=fft_size)
    xcorr = np.fft.irfft(np.conj(ref_fft) * rec_fft, n=fft_size)

    # Search range
    if max_delay_samples is not None:
        search = xcorr[: max_delay_samples + 1]
    else:
        search = xcorr[: len(rec)]

    peak_idx = int(np.argmax(search))
    confidence = float(search[peak_idx])

    return peak_idx, confidence


def samples_to_ms(samples: int, sample_rate: int) -> float:
    """Convert a sample count to milliseconds."""
    if sample_rate <= 0:
        return 0.0
    return (samples / sample_rate) * 1000.0


def ms_to_samples(ms: float, sample_rate: int) -> int:
    """Convert milliseconds to sample count."""
    return int((ms / 1000.0) * sample_rate)


class LatencyMeasurement:
    """
    Result of a latency measurement.

    Attributes:
        delay_samples: Measured delay in samples.
        delay_ms: Measured delay in milliseconds.
        sample_rate: Sample rate used for measurement.
        confidence: Normalized cross-correlation peak (0.0–1.0).
        valid: True if the measurement is considered reliable.
    """

    def __init__(
        self,
        delay_samples: int,
        sample_rate: int,
        confidence: float,
        min_confidence: float = 0.1,
    ) -> None:
        self.delay_samples = delay_samples
        self.sample_rate = sample_rate
        self.confidence = confidence
        self.delay_ms = samples_to_ms(delay_samples, sample_rate)
        self.valid = confidence >= min_confidence and delay_samples >= 0

    def __repr__(self) -> str:
        return (
            f"LatencyMeasurement(delay={self.delay_samples}sa / {self.delay_ms:.2f}ms, "
            f"confidence={self.confidence:.3f}, valid={self.valid})"
        )


def measure_from_arrays(
    reference: np.ndarray,
    recorded: np.ndarray,
    sample_rate: int,
    max_delay_ms: float = 500.0,
) -> LatencyMeasurement:
    """
    Measure latency from pre-captured reference and recorded arrays.

    This is the testable core — no audio hardware required.

    Args:
        reference: Original transmitted signal.
        recorded: Captured signal (may include silence before the echo).
        sample_rate: Sample rate in Hz.
        max_delay_ms: Maximum expected delay in ms (limits search range).

    Returns:
        LatencyMeasurement result.
    """
    max_samples = ms_to_samples(max_delay_ms, sample_rate)
    delay_samples, confidence = estimate_delay_samples(reference, recorded, max_samples)
    return LatencyMeasurement(delay_samples, sample_rate, confidence)
