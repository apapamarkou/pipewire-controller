"""Tests for PipeWire device model."""

from pipewire_controller.pipewire.model import (
    AudioNode,
    GraphSettings,
    NodeDirection,
    PipeWireGraph,
    SampleRateSupport,
)


def _make_node(**kwargs) -> AudioNode:
    defaults = dict(
        id=1,
        name="test_node",
        description="Test Node",
        media_class="Audio/Sink",
        direction=NodeDirection.OUTPUT,
        channel_count=2,
        channel_positions=["FL", "FR"],
        native_rates=[44100, 48000],
        rate_range=None,
        volume=1.0,
        muted=False,
        is_default=False,
        state="running",
        device_id=None,
        device_name="Test Card",
    )
    defaults.update(kwargs)
    return AudioNode(**defaults)


class TestAudioNode:
    def test_is_sink(self):
        n = _make_node(media_class="Audio/Sink")
        assert n.is_sink is True
        assert n.is_source is False

    def test_is_source(self):
        n = _make_node(media_class="Audio/Source")
        assert n.is_source is True
        assert n.is_sink is False

    def test_display_name_uses_friendly_name(self):
        n = _make_node(description="Real Name", friendly_name="My Mic")
        assert n.display_name == "My Mic"

    def test_display_name_falls_back_to_description(self):
        n = _make_node(description="Real Name", friendly_name=None)
        assert n.display_name == "Real Name"

    def test_display_name_falls_back_to_name(self):
        n = _make_node(description="", name="node_name", friendly_name=None)
        assert n.display_name == "node_name"

    def test_rate_support_native(self):
        n = _make_node(native_rates=[44100, 48000, 96000])
        assert n.rate_support(48000) == SampleRateSupport.NATIVE
        assert n.rate_support(96000) == SampleRateSupport.NATIVE

    def test_rate_support_resampled(self):
        n = _make_node(native_rates=[44100, 48000])
        assert n.rate_support(96000) == SampleRateSupport.RESAMPLED

    def test_rate_support_range_native(self):
        n = _make_node(native_rates=[], rate_range=(44100, 192000))
        assert n.rate_support(96000) == SampleRateSupport.NATIVE

    def test_rate_support_range_resampled(self):
        n = _make_node(native_rates=[], rate_range=(44100, 48000))
        assert n.rate_support(96000) == SampleRateSupport.RESAMPLED

    def test_rate_support_unknown_when_no_info(self):
        n = _make_node(native_rates=[], rate_range=None)
        assert n.rate_support(48000) == SampleRateSupport.UNKNOWN


class TestGraphSettings:
    def test_period_ms(self):
        s = GraphSettings(
            rate=48000,
            quantum=1024,
            allowed_rates=[48000],
            min_quantum=32,
            max_quantum=2048,
            force_rate=0,
            force_quantum=0,
        )
        assert abs(s.period_ms - 21.333) < 0.01

    def test_period_ms_zero_rate(self):
        s = GraphSettings(
            rate=0,
            quantum=1024,
            allowed_rates=[],
            min_quantum=32,
            max_quantum=2048,
            force_rate=0,
            force_quantum=0,
        )
        assert s.period_ms == 0.0

    def test_rate_is_forced(self):
        s = GraphSettings(48000, 1024, [48000], 32, 2048, force_rate=96000, force_quantum=0)
        assert s.rate_is_forced is True

    def test_rate_not_forced(self):
        s = GraphSettings(48000, 1024, [48000], 32, 2048, force_rate=0, force_quantum=0)
        assert s.rate_is_forced is False

    def test_quantum_is_forced(self):
        s = GraphSettings(48000, 1024, [48000], 32, 2048, force_rate=0, force_quantum=256)
        assert s.quantum_is_forced is True


class TestPipeWireGraph:
    def _make_graph(self):
        sink = _make_node(id=10, media_class="Audio/Sink", is_default=True)
        source = _make_node(id=20, media_class="Audio/Source", is_default=True)
        settings = GraphSettings(48000, 1024, [48000], 32, 2048, 0, 0)
        return PipeWireGraph(
            nodes=[sink, source],
            settings=settings,
            default_sink_id=10,
            default_source_id=20,
        )

    def test_sinks(self):
        g = self._make_graph()
        assert len(g.sinks) == 1
        assert g.sinks[0].id == 10

    def test_sources(self):
        g = self._make_graph()
        assert len(g.sources) == 1
        assert g.sources[0].id == 20

    def test_node_by_id(self):
        g = self._make_graph()
        assert g.node_by_id(10) is not None
        assert g.node_by_id(999) is None
