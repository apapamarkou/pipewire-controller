# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2024 Andrianos Papamarkou
"""
PipeWire client — subprocess-based interface to pw-dump, pw-metadata, wpctl.

Design decisions:
- pw-dump (JSON) is used for graph/node/device discovery — it provides the
  complete graph state in a single call and is the canonical way to inspect
  PipeWire objects without requiring native bindings.
- pw-metadata is used for reading/writing clock settings (clock.force-rate,
  clock.force-quantum) — this is the documented mechanism for these settings.
- wpctl is used for volume, mute, and default device operations — it is the
  WirePlumber control interface and handles session policy correctly.
- All operations are synchronous and short-lived. Real-time monitoring is
  handled separately via pw-mon in a background thread (future phase).
- No operation modifies node.name or other stable technical identifiers.
"""

from __future__ import annotations

import json
import re
import subprocess
from typing import Any

from ..log import get_logger
from .model import (
    AudioNode,
    GraphSettings,
    NodeDirection,
    PipeWireGraph,
)

log = get_logger("pw_client")

_TIMEOUT = 5
_COMMON_RATES = [44100, 48000, 88200, 96000, 176400, 192000]


def _run(cmd: list[str], timeout: int = _TIMEOUT) -> subprocess.CompletedProcess:
    return subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)


def _run_check(cmd: list[str], timeout: int = _TIMEOUT) -> str:
    r = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout, check=True)
    return r.stdout


# ── Graph discovery ───────────────────────────────────────────────────────────


def get_graph() -> PipeWireGraph | None:
    """
    Return a complete snapshot of the PipeWire graph.
    Returns None if PipeWire is unavailable.
    """
    try:
        raw = _run_check(["pw-dump"])
        data = json.loads(raw)
    except (subprocess.CalledProcessError, subprocess.TimeoutExpired, json.JSONDecodeError) as exc:
        log.warning("pw-dump failed: %s", exc)
        return None

    settings = _parse_settings()
    default_sink_id, default_source_id = _get_defaults()
    nodes = _parse_nodes(data, default_sink_id, default_source_id)

    return PipeWireGraph(
        nodes=nodes,
        settings=settings,
        default_sink_id=default_sink_id,
        default_source_id=default_source_id,
    )


def _parse_nodes(
    data: list[dict], default_sink_id: int | None, default_source_id: int | None
) -> list[AudioNode]:
    nodes = []
    for obj in data:
        if obj.get("type") != "PipeWire:Interface:Node":
            continue
        node = _parse_node(obj, default_sink_id, default_source_id)
        if node is not None:
            nodes.append(node)
    return nodes


def _parse_node(
    obj: dict, default_sink_id: int | None, default_source_id: int | None
) -> AudioNode | None:
    info = obj.get("info", {})
    props = info.get("props", {})
    media_class = props.get("media.class", "")

    if "Audio/Sink" not in media_class and "Audio/Source" not in media_class:
        return None

    node_id = obj["id"]
    is_sink = "Sink" in media_class
    direction = NodeDirection.OUTPUT if is_sink else NodeDirection.INPUT

    native_rates, rate_range = _extract_rates(info.get("params", {}))

    # Volume and mute from wpctl (more reliable than pw-dump for these)
    volume, muted = _get_volume_mute(node_id)

    is_default = node_id in (default_sink_id, default_source_id)

    return AudioNode(
        id=node_id,
        name=props.get("node.name", f"node-{node_id}"),
        description=props.get("node.description", props.get("alsa.card_name", f"Node {node_id}")),
        media_class=media_class,
        direction=direction,
        channel_count=props.get("audio.channels", 2),
        channel_positions=_parse_positions(props.get("audio.position", "")),
        native_rates=native_rates,
        rate_range=rate_range,
        volume=volume,
        muted=muted,
        is_default=is_default,
        state=info.get("state", "unknown"),
        device_id=props.get("device.id"),
        device_name=props.get("alsa.card_name", props.get("api.alsa.card.name", "")),
        props=props,
    )


def _extract_rates(params: dict) -> tuple[list[int], tuple[int, int] | None]:
    """Extract native sample rates from node params."""
    rates: set[int] = set()
    rate_range: tuple[int, int] | None = None

    for fmt in params.get("EnumFormat", []):
        if not isinstance(fmt, dict):
            continue
        rate = fmt.get("rate")
        if rate is None:
            continue
        if isinstance(rate, int):
            rates.add(rate)
        elif isinstance(rate, dict):
            # {default: N, min: N, max: N} or {min: N, max: N}
            lo = rate.get("min")
            hi = rate.get("max")
            default = rate.get("default")
            if default:
                rates.add(default)
            if lo and hi:
                rate_range = (lo, hi)
                rates.update(r for r in _COMMON_RATES if lo <= r <= hi)

    return sorted(rates), rate_range


def _parse_positions(pos_str: str) -> list[str]:
    """Parse '[ FL, FR ]' → ['FL', 'FR']."""
    if not pos_str:
        return []
    return [p.strip() for p in pos_str.strip("[] ").split(",") if p.strip()]


def _get_volume_mute(node_id: int) -> tuple[float, bool]:
    """Get volume and mute state for a node via wpctl."""
    try:
        out = _run_check(["wpctl", "get-volume", str(node_id)])
        # "Volume: 0.75\n" or "Volume: 0.75 [MUTED]\n"
        m = re.search(r"Volume:\s*([\d.]+)", out)
        vol = float(m.group(1)) if m else 1.0
        muted = "[MUTED]" in out
        return vol, muted
    except Exception:
        return 1.0, False


# ── Settings ──────────────────────────────────────────────────────────────────


def _parse_settings() -> GraphSettings:
    """Read current PipeWire clock settings from pw-metadata."""
    defaults = {
        "clock.rate": 48000,
        "clock.quantum": 1024,
        "clock.allowed-rates": "[ 48000 ]",
        "clock.min-quantum": 32,
        "clock.max-quantum": 2048,
        "clock.force-rate": 0,
        "clock.force-quantum": 0,
    }
    try:
        out = _run_check(["pw-metadata", "-n", "settings"])
        for line in out.splitlines():
            for key in defaults:
                if f"key:'{key}'" in line:
                    m = re.search(r"value:'([^']*)'", line)
                    if m:
                        defaults[key] = m.group(1)
    except Exception as exc:
        log.warning("pw-metadata read failed: %s", exc)

    def _int(k: str) -> int:
        try:
            return int(defaults[k])
        except (ValueError, TypeError):
            return 0

    allowed = _parse_allowed_rates(str(defaults["clock.allowed-rates"]))

    return GraphSettings(
        rate=_int("clock.rate"),
        quantum=_int("clock.quantum"),
        allowed_rates=allowed,
        min_quantum=_int("clock.min-quantum"),
        max_quantum=_int("clock.max-quantum"),
        force_rate=_int("clock.force-rate"),
        force_quantum=_int("clock.force-quantum"),
    )


def _parse_allowed_rates(s: str) -> list[int]:
    """Parse '[ 44100 48000 ]' or '[ 48000 ]' → [44100, 48000]."""
    return [int(x) for x in re.findall(r"\d+", s) if int(x) > 100]


def get_settings() -> GraphSettings:
    return _parse_settings()


# ── Default devices ───────────────────────────────────────────────────────────


def _get_defaults() -> tuple[int | None, int | None]:
    """Return (default_sink_id, default_source_id) from wpctl status."""
    sink_id: int | None = None
    source_id: int | None = None
    try:
        out = _run_check(["wpctl", "status"])
        in_audio = False
        in_sinks = False
        in_sources = False
        for line in out.splitlines():
            # Only parse the Audio section
            if line.startswith("Audio"):
                in_audio = True
                continue
            if in_audio and line and not line[0].isspace() and not line.startswith(" "):
                break  # left the Audio section (e.g. "Video")
            if not in_audio:
                continue
            if "Sinks:" in line:
                in_sinks = True
                in_sources = False
                continue
            if "Sources:" in line:
                in_sources = True
                in_sinks = False
                continue
            if "Filters:" in line or "Streams:" in line:
                in_sinks = False
                in_sources = False
                continue
            if (in_sinks or in_sources) and "*" in line:
                m = re.search(r"\*\s+(\d+)\.", line)
                if m:
                    nid = int(m.group(1))
                    if in_sinks:
                        sink_id = nid
                    else:
                        source_id = nid
    except Exception as exc:
        log.warning("wpctl status failed: %s", exc)
    return sink_id, source_id


def _set_default_device(node_id: int, is_sink: bool) -> bool:
    """
    Set the default audio sink or source.

    WirePlumber overrides wpctl set-default via its session policy unless we
    also update default.configured.audio.{sink,source} in the 'default'
    metadata namespace. We set both keys so the change persists.
    """
    kind = "sink" if is_sink else "source"
    # Look up node.name from pw-dump
    node_name: str | None = None
    try:
        raw = _run_check(["pw-dump"])
        data = json.loads(raw)
        for obj in data:
            if obj.get("id") == node_id:
                node_name = obj.get("info", {}).get("props", {}).get("node.name")
                break
    except Exception:
        pass

    try:
        # Set session default via wpctl
        _run_check(["wpctl", "set-default", str(node_id)])
    except Exception as exc:
        log.error("set_default_%s(%d) wpctl failed: %s", kind, node_id, exc)
        return False

    if node_name:
        # Also update the configured default so WirePlumber doesn't revert it
        name_json = json.dumps({"name": node_name})
        for key in (f"default.configured.audio.{kind}", f"default.audio.{kind}"):
            try:
                _run_check(["pw-metadata", "-n", "default", "0", key, name_json])
            except Exception as exc:
                log.warning("set_default_%s metadata %s failed: %s", kind, key, exc)

    log.info("Default %s set to %d (%s)", kind, node_id, node_name or "?")
    return True


def set_default_sink(node_id: int) -> bool:
    """Set the default audio sink."""
    return _set_default_device(node_id, is_sink=True)


def set_default_source(node_id: int) -> bool:
    """Set the default audio source."""
    return _set_default_device(node_id, is_sink=False)


# ── Volume / mute ─────────────────────────────────────────────────────────────


def set_volume(node_id: int, volume: float) -> bool:
    """Set volume for a node (0.0–1.0 linear)."""
    vol = max(0.0, min(1.5, volume))  # wpctl allows >1.0 for boost
    try:
        _run_check(["wpctl", "set-volume", str(node_id), f"{vol:.2f}"])
        return True
    except Exception as exc:
        log.error("set_volume(%d, %.2f) failed: %s", node_id, vol, exc)
        return False


def set_mute(node_id: int, muted: bool) -> bool:
    """Set mute state for a node."""
    try:
        _run_check(["wpctl", "set-mute", str(node_id), "1" if muted else "0"])
        return True
    except Exception as exc:
        log.error("set_mute(%d, %s) failed: %s", node_id, muted, exc)
        return False


# ── Clock settings ────────────────────────────────────────────────────────────


def set_force_rate(rate: int) -> bool:
    """
    Force PipeWire clock rate. rate=0 clears the force (returns to auto).
    Uses pw-metadata on the 'settings' metadata object.
    """
    try:
        _run_check(
            ["pw-metadata", "-n", "settings", "0", "clock.force-rate", str(rate)],
        )
        log.info("clock.force-rate set to %d", rate)
        return True
    except Exception as exc:
        log.error("set_force_rate(%d) failed: %s", rate, exc)
        return False


def set_force_quantum(quantum: int) -> bool:
    """
    Force PipeWire quantum. quantum=0 clears the force (returns to auto).
    """
    try:
        _run_check(
            ["pw-metadata", "-n", "settings", "0", "clock.force-quantum", str(quantum)],
        )
        log.info("clock.force-quantum set to %d", quantum)
        return True
    except Exception as exc:
        log.error("set_force_quantum(%d) failed: %s", quantum, exc)
        return False


def clear_force_rate() -> bool:
    return set_force_rate(0)


def clear_force_quantum() -> bool:
    return set_force_quantum(0)


# ── Stream moving ─────────────────────────────────────────────────────────────


def move_stream_to_node(stream_id: int, target_node_id: int) -> bool:
    """
    Move a stream (client node) to a different sink/source.
    Uses wpctl move which is the WirePlumber-supported mechanism.
    """
    try:
        _run_check(["wpctl", "move", str(stream_id), str(target_node_id)])
        return True
    except Exception as exc:
        log.warning("move_stream(%d → %d) failed: %s", stream_id, target_node_id, exc)
        return False


def get_streams() -> list[dict[str, Any]]:
    """Return active audio streams from pw-dump."""
    try:
        raw = _run_check(["pw-dump"])
        data = json.loads(raw)
    except Exception:
        return []

    streams = []
    for obj in data:
        if obj.get("type") != "PipeWire:Interface:Node":
            continue
        props = obj.get("info", {}).get("props", {})
        mc = props.get("media.class", "")
        if mc not in ("Stream/Output/Audio", "Stream/Input/Audio"):
            continue
        streams.append(
            {
                "id": obj["id"],
                "name": props.get("application.name", props.get("node.name", "?")),
                "media_class": mc,
                "node_id": props.get("node.id"),
            }
        )
    return streams
