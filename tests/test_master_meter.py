"""Tests for master meter mode configuration."""

from pipewire_controller.ui.sections.master_meter import MASTER_MODES


class TestMasterModes:
    def test_mono(self):
        count, labels = MASTER_MODES["Mono"]
        assert count == 1
        assert labels == ["M"]

    def test_stereo(self):
        count, labels = MASTER_MODES["Stereo"]
        assert count == 2
        assert labels == ["L", "R"]

    def test_21(self):
        count, labels = MASTER_MODES["2.1"]
        assert count == 3
        assert "LFE" in labels

    def test_quadro(self):
        count, labels = MASTER_MODES["Quadro"]
        assert count == 4

    def test_51(self):
        count, labels = MASTER_MODES["5.1"]
        assert count == 6
        assert "C" in labels
        assert "LFE" in labels

    def test_71(self):
        count, labels = MASTER_MODES["7.1"]
        assert count == 8
        assert "Lb" in labels
        assert "Rb" in labels

    def test_custom_defined(self):
        assert "Custom" in MASTER_MODES

    def test_all_modes_present(self):
        for mode in ("Mono", "Stereo", "2.1", "Quadro", "5.1", "7.1", "Custom"):
            assert mode in MASTER_MODES
