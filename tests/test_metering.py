"""
Tests for audio metering engine.

All tests use synthetic signals — no audio hardware required.
"""

import math

import numpy as np

from pipewire_controller.metering import (
    ChannelMeter,
    LUFSMeter,
    dbfs_to_linear,
    k_weight,
    linear_to_dbfs,
    lufs_from_mean_square,
    mean_square_k_weighted,
    peak_dbfs,
    peak_linear,
    rms_dbfs,
    rms_linear,
)


class TestLinearDbfs:
    def test_unity(self):
        assert abs(linear_to_dbfs(1.0) - 0.0) < 0.001

    def test_half(self):
        assert abs(linear_to_dbfs(0.5) - (-6.021)) < 0.01

    def test_silence(self):
        assert linear_to_dbfs(0.0) == -120.0

    def test_negative_silence(self):
        assert linear_to_dbfs(-0.001) == -120.0

    def test_roundtrip(self):
        for db in (-60.0, -20.0, -6.0, 0.0):
            lin = dbfs_to_linear(db)
            assert abs(linear_to_dbfs(lin) - db) < 0.001


class TestPeakRms:
    def test_peak_sine(self):
        t = np.linspace(0, 1, 48000, endpoint=False)
        sine = np.sin(2 * np.pi * 1000 * t).astype(np.float32)
        p = peak_linear(sine)
        assert abs(p - 1.0) < 0.001

    def test_rms_sine(self):
        """RMS of a full-scale sine is 1/sqrt(2) ≈ 0.7071."""
        t = np.linspace(0, 1, 48000, endpoint=False)
        sine = np.sin(2 * np.pi * 1000 * t).astype(np.float32)
        r = rms_linear(sine)
        assert abs(r - (1.0 / math.sqrt(2))) < 0.001

    def test_rms_sine_dbfs(self):
        """Full-scale sine RMS ≈ -3.01 dBFS."""
        t = np.linspace(0, 1, 48000, endpoint=False)
        sine = np.sin(2 * np.pi * 1000 * t).astype(np.float32)
        assert abs(rms_dbfs(sine) - (-3.0103)) < 0.01

    def test_peak_dc(self):
        dc = np.full(1000, 0.5, dtype=np.float32)
        assert abs(peak_linear(dc) - 0.5) < 0.001

    def test_rms_dc(self):
        dc = np.full(1000, 0.5, dtype=np.float32)
        assert abs(rms_linear(dc) - 0.5) < 0.001

    def test_empty(self):
        assert peak_linear(np.array([])) == 0.0
        assert rms_linear(np.array([])) == 0.0

    def test_peak_dbfs_silence(self):
        assert peak_dbfs(np.zeros(100)) == -120.0


class TestChannelMeter:
    def test_process_block_updates_peak(self):
        m = ChannelMeter(name="L")
        samples = np.array([0.0, 0.5, -0.8, 0.3], dtype=np.float32)
        m.process_block(samples)
        assert abs(m.peak_linear - 0.8) < 0.001

    def test_peak_hold_latches(self):
        m = ChannelMeter()
        m.process_block(np.array([0.9], dtype=np.float32))
        m.process_block(np.array([0.1], dtype=np.float32))
        assert abs(m.peak_hold_linear - 0.9) < 0.001
        assert abs(m.peak_linear - 0.1) < 0.001

    def test_max_latches(self):
        m = ChannelMeter()
        m.process_block(np.array([0.7], dtype=np.float32))
        m.process_block(np.array([0.3], dtype=np.float32))
        assert abs(m.max_linear - 0.7) < 0.001

    def test_over_latches_at_clip(self):
        m = ChannelMeter()
        m.process_block(np.array([1.0], dtype=np.float32))
        assert m.over is True
        m.process_block(np.array([0.1], dtype=np.float32))
        assert m.over is True  # still latched

    def test_over_not_set_below_clip(self):
        m = ChannelMeter()
        m.process_block(np.array([0.99], dtype=np.float32))
        assert m.over is False

    def test_clear_resets_hold_max_over(self):
        m = ChannelMeter()
        m.process_block(np.array([1.0], dtype=np.float32))
        m.clear()
        assert m.peak_hold_linear == 0.0
        assert m.max_linear == 0.0
        assert m.over is False

    def test_clear_does_not_reset_current_peak(self):
        m = ChannelMeter()
        m.process_block(np.array([0.5], dtype=np.float32))
        m.clear()
        # Current peak is from last block, not cleared
        assert abs(m.peak_linear - 0.5) < 0.001

    def test_snapshot_keys(self):
        m = ChannelMeter(name="R", node_name="alsa_output", port_name="FR", channel_number=1)
        snap = m.snapshot()
        for key in ("name", "node_name", "port_name", "channel_number", "peak_dbfs", "over"):
            assert key in snap

    def test_dbfs_properties(self):
        m = ChannelMeter()
        m.process_block(np.array([1.0], dtype=np.float32))
        assert abs(m.peak_dbfs - 0.0) < 0.001


class TestKWeighting:
    def test_returns_array_same_length(self):
        samples = np.random.randn(4800).astype(np.float32)
        result = k_weight(samples, 48000)
        assert len(result) == len(samples)

    def test_unknown_rate_returns_unfiltered(self):
        samples = np.ones(100, dtype=np.float32)
        result = k_weight(samples, 22050)
        assert len(result) == 100

    def test_attenuates_low_frequencies(self):
        """K-weighting high-pass should attenuate 50Hz relative to 1kHz."""
        sr = 48000
        t = np.linspace(0, 0.1, int(0.1 * sr), endpoint=False)
        low = np.sin(2 * np.pi * 50 * t).astype(np.float32)
        high = np.sin(2 * np.pi * 1000 * t).astype(np.float32)
        low_out = k_weight(low, sr)
        high_out = k_weight(high, sr)
        low_rms = float(np.sqrt(np.mean(low_out**2)))
        high_rms = float(np.sqrt(np.mean(high_out**2)))
        assert low_rms < high_rms


class TestLUFSMeter:
    def _sine_ms(self, amplitude: float, sr: int = 48000) -> float:
        """Mean square of K-weighted sine at given amplitude."""
        t = np.linspace(0, 0.4, int(0.4 * sr), endpoint=False)
        sine = (amplitude * np.sin(2 * np.pi * 1000 * t)).astype(np.float32)
        return mean_square_k_weighted(sine, sr)

    def test_momentary_none_when_empty(self):
        m = LUFSMeter()
        assert m.get_momentary() is None

    def test_short_term_none_when_empty(self):
        m = LUFSMeter()
        assert m.get_short_term() is None

    def test_integrated_none_when_empty(self):
        m = LUFSMeter()
        assert m.get_integrated() is None

    def test_momentary_full_scale_sine(self):
        """Full-scale 1kHz sine should give approximately -3 LUFS-M."""
        m = LUFSMeter(sample_rate=48000)
        ms = self._sine_ms(1.0)
        m.process_block(ms)
        val = m.get_momentary()
        assert val is not None
        assert -10.0 < val < 0.0  # reasonable range for full-scale sine

    def test_integrated_below_absolute_gate(self):
        """Very quiet signal should be gated out → None."""
        m = LUFSMeter(sample_rate=48000)
        # -80 dBFS signal — below absolute gate of -70 LUFS
        ms = self._sine_ms(dbfs_to_linear(-80.0))
        for _ in range(20):
            m.process_block(ms)
        assert m.get_integrated() is None

    def test_integrated_above_gate(self):
        """Loud signal should produce a valid integrated value."""
        m = LUFSMeter(sample_rate=48000)
        ms = self._sine_ms(0.5)  # -6 dBFS
        for _ in range(20):
            m.process_block(ms)
        val = m.get_integrated()
        assert val is not None
        assert val > -70.0

    def test_reset_clears_state(self):
        m = LUFSMeter(sample_rate=48000)
        ms = self._sine_ms(0.5)
        for _ in range(10):
            m.process_block(ms)
        m.reset()
        assert m.get_momentary() is None
        assert m.get_integrated() is None

    def test_lufs_from_mean_square_silence(self):
        assert lufs_from_mean_square(0.0) == -120.0
