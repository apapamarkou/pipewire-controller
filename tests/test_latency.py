"""
Tests for latency measurement signal analysis.

All tests use synthetic signals — no audio hardware required.
The algorithm is tested independently from PipeWire and Qt.
"""

import numpy as np

from pipewire_controller.latency import (
    LatencyMeasurement,
    estimate_delay_samples,
    generate_chirp,
    measure_from_arrays,
    ms_to_samples,
    samples_to_ms,
)


class TestGenerateChirp:
    def test_length(self):
        sig = generate_chirp(0.1, 48000)
        assert len(sig) == 4800

    def test_amplitude_bounded(self):
        sig = generate_chirp(0.1, 48000, amplitude=0.5)
        assert np.max(np.abs(sig)) <= 0.5 + 1e-6

    def test_dtype(self):
        sig = generate_chirp(0.1, 48000)
        assert sig.dtype == np.float32

    def test_windowed_edges_near_zero(self):
        sig = generate_chirp(0.1, 48000)
        # Hann window forces edges to zero
        assert abs(float(sig[0])) < 0.01
        assert abs(float(sig[-1])) < 0.01


class TestSamplesMs:
    def test_samples_to_ms(self):
        assert abs(samples_to_ms(480, 48000) - 10.0) < 0.001

    def test_ms_to_samples(self):
        assert ms_to_samples(10.0, 48000) == 480

    def test_zero_rate(self):
        assert samples_to_ms(100, 0) == 0.0

    def test_roundtrip(self):
        sr = 48000
        for ms in (1.0, 5.0, 10.0, 21.333, 100.0):
            samples = ms_to_samples(ms, sr)
            recovered = samples_to_ms(samples, sr)
            assert abs(recovered - ms) < 1.0  # within 1ms (integer rounding)


class TestEstimateDelaySamples:
    def _make_delayed(self, signal: np.ndarray, delay: int) -> np.ndarray:
        """Prepend `delay` zeros to simulate a delayed recording."""
        return np.concatenate([np.zeros(delay, dtype=np.float32), signal])

    def test_zero_delay(self):
        ref = generate_chirp(0.1, 48000)
        delay, conf = estimate_delay_samples(ref, ref)
        assert delay == 0
        assert conf > 0.5

    def test_known_delay_100_samples(self):
        ref = generate_chirp(0.1, 48000)
        rec = self._make_delayed(ref, 100)
        delay, conf = estimate_delay_samples(ref, rec, max_delay_samples=500)
        assert delay == 100
        assert conf > 0.3

    def test_known_delay_480_samples(self):
        """10ms at 48kHz."""
        ref = generate_chirp(0.2, 48000)
        rec = self._make_delayed(ref, 480)
        delay, conf = estimate_delay_samples(ref, rec, max_delay_samples=2000)
        assert delay == 480
        assert conf > 0.3

    def test_known_delay_2048_samples(self):
        """~42ms at 48kHz — typical DAW buffer."""
        ref = generate_chirp(0.5, 48000)
        rec = self._make_delayed(ref, 2048)
        delay, conf = estimate_delay_samples(ref, rec, max_delay_samples=5000)
        assert delay == 2048
        assert conf > 0.3

    def test_with_noise(self):
        """Delay detection should be robust to moderate noise."""
        rng = np.random.default_rng(42)
        ref = generate_chirp(0.2, 48000)
        rec = self._make_delayed(ref, 300)
        noise = rng.normal(0, 0.05, len(rec)).astype(np.float32)
        rec_noisy = rec + noise
        delay, conf = estimate_delay_samples(ref, rec_noisy, max_delay_samples=1000)
        assert delay == 300
        assert conf > 0.1

    def test_empty_reference(self):
        delay, conf = estimate_delay_samples(np.array([]), np.array([1.0, 2.0]))
        assert delay == 0
        assert conf == 0.0

    def test_empty_recorded(self):
        ref = generate_chirp(0.1, 48000)
        delay, conf = estimate_delay_samples(ref, np.array([]))
        assert delay == 0
        assert conf == 0.0

    def test_silent_recorded(self):
        ref = generate_chirp(0.1, 48000)
        rec = np.zeros(len(ref), dtype=np.float32)
        delay, conf = estimate_delay_samples(ref, rec)
        assert conf == 0.0


class TestMeasureFromArrays:
    def test_known_delay_10ms(self):
        sr = 48000
        delay_samples = ms_to_samples(10.0, sr)
        ref = generate_chirp(0.2, sr)
        rec = np.concatenate([np.zeros(delay_samples, dtype=np.float32), ref])
        result = measure_from_arrays(ref, rec, sr, max_delay_ms=50.0)
        assert result.valid
        assert result.delay_samples == delay_samples
        assert abs(result.delay_ms - 10.0) < 0.5

    def test_known_delay_21ms(self):
        """~1024 frames at 48kHz — common DAW quantum."""
        sr = 48000
        delay_samples = 1024
        ref = generate_chirp(0.5, sr)
        rec = np.concatenate([np.zeros(delay_samples, dtype=np.float32), ref])
        result = measure_from_arrays(ref, rec, sr, max_delay_ms=100.0)
        assert result.valid
        assert result.delay_samples == delay_samples

    def test_invalid_when_silent(self):
        sr = 48000
        ref = generate_chirp(0.1, sr)
        rec = np.zeros(len(ref), dtype=np.float32)
        result = measure_from_arrays(ref, rec, sr)
        assert result.valid is False

    def test_44100_sample_rate(self):
        sr = 44100
        delay_samples = 441  # 10ms at 44100
        ref = generate_chirp(0.2, sr)
        rec = np.concatenate([np.zeros(delay_samples, dtype=np.float32), ref])
        result = measure_from_arrays(ref, rec, sr, max_delay_ms=50.0)
        assert result.valid
        assert result.delay_samples == delay_samples
        assert abs(result.delay_ms - 10.0) < 0.5

    def test_96000_sample_rate(self):
        sr = 96000
        delay_samples = 960  # 10ms at 96000
        ref = generate_chirp(0.2, sr)
        rec = np.concatenate([np.zeros(delay_samples, dtype=np.float32), ref])
        result = measure_from_arrays(ref, rec, sr, max_delay_ms=50.0)
        assert result.valid
        assert result.delay_samples == delay_samples


class TestLatencyMeasurement:
    def test_repr(self):
        m = LatencyMeasurement(480, 48000, 0.8)
        r = repr(m)
        assert "480" in r
        assert "10.00" in r

    def test_valid_threshold(self):
        assert LatencyMeasurement(100, 48000, 0.15).valid is True
        assert LatencyMeasurement(100, 48000, 0.05).valid is False

    def test_negative_delay_invalid(self):
        m = LatencyMeasurement(-1, 48000, 0.9)
        assert m.valid is False
