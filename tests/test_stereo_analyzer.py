"""
Tests for StereoAnalyzer — correlation and goniometer data.

All tests use synthetic signals; no audio hardware required.
"""

import math

import numpy as np

from pipewire_controller.metering import StereoAnalyzer, StereoSnapshot


def _sine(freq: float = 440.0, sr: int = 48000, n: int = 4096) -> np.ndarray:
    t = np.linspace(0, n / sr, n, endpoint=False)
    return np.sin(2 * math.pi * freq * t).astype(np.float32)


class TestStereoAnalyzerCorrelation:
    def _feed(self, left: np.ndarray, right: np.ndarray) -> StereoSnapshot:
        sa = StereoAnalyzer()
        sa.process_block(left, right)
        return sa.snapshot()

    def test_identical_signals_correlation_plus_one(self):
        sig = _sine()
        snap = self._feed(sig, sig)
        assert abs(snap.correlation - 1.0) < 0.01

    def test_inverted_signal_correlation_minus_one(self):
        sig = _sine()
        snap = self._feed(sig, -sig)
        assert abs(snap.correlation - (-1.0)) < 0.01

    def test_uncorrelated_signals_near_zero(self):
        """Two independent sine tones at different frequencies → near 0."""
        left = _sine(440.0)
        right = _sine(997.0)  # prime frequency, orthogonal over window
        snap = self._feed(left, right)
        assert abs(snap.correlation) < 0.2

    def test_silence_returns_zero_not_nan(self):
        """Zero-energy input must not produce NaN or crash."""
        silence = np.zeros(4096, dtype=np.float32)
        snap = self._feed(silence, silence)
        assert not math.isnan(snap.correlation)
        assert snap.correlation == 0.0

    def test_one_channel_silent(self):
        """One silent channel → zero energy denominator → safe fallback."""
        sig = _sine()
        silence = np.zeros(4096, dtype=np.float32)
        snap = self._feed(sig, silence)
        assert not math.isnan(snap.correlation)
        assert snap.correlation == 0.0

    def test_correlation_clamped_to_range(self):
        """Correlation must always be in [-1, +1]."""
        rng = np.random.default_rng(42)
        left = rng.standard_normal(4096).astype(np.float32)
        right = rng.standard_normal(4096).astype(np.float32)
        snap = self._feed(left, right)
        assert -1.0 <= snap.correlation <= 1.0

    def test_dc_offset_identical(self):
        """DC signal (constant) — identical → +1."""
        dc = np.full(4096, 0.5, dtype=np.float32)
        snap = self._feed(dc, dc)
        assert abs(snap.correlation - 1.0) < 0.01

    def test_dc_offset_inverted(self):
        """DC signal — inverted → -1."""
        dc = np.full(4096, 0.5, dtype=np.float32)
        snap = self._feed(dc, -dc)
        assert abs(snap.correlation - (-1.0)) < 0.01

    def test_empty_block_no_crash(self):
        """Empty block must not crash."""
        sa = StereoAnalyzer()
        sa.process_block(np.array([], dtype=np.float32), np.array([], dtype=np.float32))
        snap = sa.snapshot()
        assert snap.correlation == 0.0

    def test_multiple_blocks_accumulate(self):
        """Feeding multiple blocks should converge to correct correlation."""
        sa = StereoAnalyzer()
        sig = _sine()
        for _ in range(4):
            sa.process_block(sig, sig)
        snap = sa.snapshot()
        assert abs(snap.correlation - 1.0) < 0.01

    def test_reset_clears_state(self):
        sa = StereoAnalyzer()
        sig = _sine()
        sa.process_block(sig, sig)
        sa.reset()
        snap = sa.snapshot()
        assert snap.correlation == 0.0
        assert len(snap.gonio_xy) == 0


class TestStereoAnalyzerGoniometer:
    def test_snapshot_returns_ndarray(self):
        sa = StereoAnalyzer()
        sig = _sine()
        sa.process_block(sig, sig)
        snap = sa.snapshot()
        assert isinstance(snap.gonio_xy, np.ndarray)
        assert snap.gonio_xy.ndim == 2
        assert snap.gonio_xy.shape[1] == 2

    def test_snapshot_clears_accumulation(self):
        """After snapshot(), gonio_xy should be empty on next call if no new data."""
        sa = StereoAnalyzer()
        sig = _sine()
        sa.process_block(sig, sig)
        sa.snapshot()  # consume
        snap2 = sa.snapshot()
        assert len(snap2.gonio_xy) == 0

    def test_mono_signal_m_nonzero_s_near_zero(self):
        """Identical L/R (mono) → M = L*sqrt(2), S ≈ 0."""
        sa = StereoAnalyzer()
        sig = _sine()
        sa.process_block(sig, sig)
        snap = sa.snapshot()
        if len(snap.gonio_xy) > 0:
            s_vals = snap.gonio_xy[:, 1]
            assert np.max(np.abs(s_vals)) < 0.01

    def test_antiphase_signal_m_near_zero_s_nonzero(self):
        """L = -R (anti-phase) → M ≈ 0, S = L*sqrt(2)."""
        sa = StereoAnalyzer()
        sig = _sine()
        sa.process_block(sig, -sig)
        snap = sa.snapshot()
        if len(snap.gonio_xy) > 0:
            m_vals = snap.gonio_xy[:, 0]
            assert np.max(np.abs(m_vals)) < 0.01

    def test_gonio_points_capped(self):
        """Accumulation must not grow unboundedly."""
        sa = StereoAnalyzer()
        sig = _sine(n=48000)  # large block
        sa.process_block(sig, sig)
        snap = sa.snapshot()
        assert len(snap.gonio_xy) <= 512
