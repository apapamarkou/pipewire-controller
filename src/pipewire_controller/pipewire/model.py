# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2024 Andrianos Papamarkou
"""
Device and node model for PipeWire graph objects.

This module defines pure data classes — no subprocess calls, no Qt.
All PipeWire interaction is in pw_client.py.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class NodeDirection(Enum):
    INPUT = "input"
    OUTPUT = "output"
    UNKNOWN = "unknown"


class SampleRateSupport(Enum):
    NATIVE = "native"  # ✓ Hardware-native rate
    RESAMPLED = "resampled"  # ⚠ PipeWire will resample
    UNKNOWN = "unknown"  # Cannot determine


@dataclass
class AudioNode:
    """Represents a PipeWire audio node (sink or source)."""

    id: int
    name: str  # node.name — stable technical identifier, never modified
    description: str  # node.description — user-visible, may be overridden
    media_class: str  # e.g. "Audio/Sink", "Audio/Source"
    direction: NodeDirection
    channel_count: int
    channel_positions: list[str]  # e.g. ["FL", "FR"]
    native_rates: list[int]  # rates advertised by hardware
    rate_range: tuple[int, int] | None  # (min, max) if range-based
    volume: float  # 0.0–1.0 (linear)
    muted: bool
    is_default: bool
    state: str  # "running", "suspended", "idle", "error"
    device_id: int | None
    device_name: str  # alsa.card_name or similar
    props: dict[str, Any] = field(default_factory=dict)
    friendly_name: str | None = None  # user-set override

    @property
    def display_name(self) -> str:
        return self.friendly_name or self.description or self.name

    @property
    def is_sink(self) -> bool:
        return "Sink" in self.media_class

    @property
    def is_source(self) -> bool:
        return "Source" in self.media_class

    def rate_support(self, graph_rate: int) -> SampleRateSupport:
        """Determine if graph_rate is natively supported by this node."""
        if not self.native_rates and self.rate_range is None:
            return SampleRateSupport.UNKNOWN
        if self.rate_range is not None:
            lo, hi = self.rate_range
            if lo <= graph_rate <= hi:
                return SampleRateSupport.NATIVE
            return SampleRateSupport.RESAMPLED
        if graph_rate in self.native_rates:
            return SampleRateSupport.NATIVE
        return SampleRateSupport.RESAMPLED


@dataclass
class GraphSettings:
    """Current PipeWire graph clock settings."""

    rate: int  # clock.rate (actual running rate)
    quantum: int  # clock.quantum (actual running quantum)
    allowed_rates: list[int]
    min_quantum: int
    max_quantum: int
    force_rate: int  # 0 = auto
    force_quantum: int  # 0 = auto

    @property
    def period_ms(self) -> float:
        """Processing period in milliseconds."""
        if self.rate == 0:
            return 0.0
        return (self.quantum / self.rate) * 1000.0

    @property
    def rate_is_forced(self) -> bool:
        return self.force_rate != 0

    @property
    def quantum_is_forced(self) -> bool:
        return self.force_quantum != 0


@dataclass
class PipeWireGraph:
    """Snapshot of the PipeWire graph state."""

    nodes: list[AudioNode]
    settings: GraphSettings
    default_sink_id: int | None
    default_source_id: int | None

    @property
    def sinks(self) -> list[AudioNode]:
        return [n for n in self.nodes if n.is_sink]

    @property
    def sources(self) -> list[AudioNode]:
        return [n for n in self.nodes if n.is_source]

    def node_by_id(self, node_id: int) -> AudioNode | None:
        for n in self.nodes:
            if n.id == node_id:
                return n
        return None
