# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2024 Andrianos Papamarkou
"""Dialogs — About, System Info."""

from __future__ import annotations

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QHBoxLayout,
    QLabel,
    QVBoxLayout,
    QWidget,
)

from .. import __version__
from ..detection import detect_system
from .theme import (
    C_ERROR,
    C_OK,
    C_WARN,
    PANEL_STYLE,
    TEXT_PRIMARY,
    TEXT_SECONDARY,
)


class AboutDialog(QDialog):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("About PipeWire Audio Control Center")
        self.setFixedSize(420, 260)
        self.setStyleSheet(PANEL_STYLE)

        layout = QVBoxLayout(self)
        layout.setSpacing(8)

        title = QLabel("PipeWire Audio Control Center")
        title.setStyleSheet(
            f"color: {TEXT_PRIMARY}; font-size: 15px; font-weight: bold; background: transparent;"
        )
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)

        subtitle = QLabel("DAW Companion")
        subtitle.setStyleSheet(
            f"color: {TEXT_SECONDARY}; font-size: 12px; background: transparent;"
        )
        subtitle.setAlignment(Qt.AlignmentFlag.AlignCenter)

        version = QLabel(f"Version {__version__}")
        version.setStyleSheet(f"color: {TEXT_SECONDARY}; font-size: 11px; background: transparent;")
        version.setAlignment(Qt.AlignmentFlag.AlignCenter)

        author = QLabel("Andrianos Papamarkou")
        author.setStyleSheet(f"color: {TEXT_SECONDARY}; font-size: 11px; background: transparent;")
        author.setAlignment(Qt.AlignmentFlag.AlignCenter)

        link = QLabel(
            '<a href="https://github.com/apapamarkou/pipewire-controller" '
            'style="color: #5c7cfa;">GitHub Repository</a>'
        )
        link.setOpenExternalLinks(True)
        link.setAlignment(Qt.AlignmentFlag.AlignCenter)

        license_lbl = QLabel("GNU General Public License v3.0")
        license_lbl.setStyleSheet(
            f"color: {TEXT_SECONDARY}; font-size: 10px; background: transparent;"
        )
        license_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)

        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok)
        buttons.accepted.connect(self.accept)

        for w in (title, subtitle, version, author, link, license_lbl):
            layout.addWidget(w)
        layout.addStretch()
        layout.addWidget(buttons)


class SystemInfoDialog(QDialog):
    """Shows PipeWire/WirePlumber/JACK detection results."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("System Status")
        self.setMinimumWidth(360)
        self.setStyleSheet(PANEL_STYLE)

        layout = QVBoxLayout(self)
        layout.setSpacing(6)

        status = detect_system()
        self._add_component_row(layout, status.pipewire)
        self._add_component_row(layout, status.wireplumber)
        self._add_component_row(layout, status.pipewire_jack)

        if not status.pipewire_available:
            warn = QLabel("⚠  PipeWire is not running. Most features will be unavailable.")
            warn.setStyleSheet(f"color: {C_WARN}; background: transparent; font-size: 11px;")
            warn.setWordWrap(True)
            layout.addWidget(warn)

        if not status.wireplumber.ok:
            warn = QLabel("⚠  WirePlumber is not running. Device management may be limited.")
            warn.setStyleSheet(f"color: {C_WARN}; background: transparent; font-size: 11px;")
            warn.setWordWrap(True)
            layout.addWidget(warn)

        if not status.pipewire_jack.installed:
            note = QLabel(
                "⚠  PipeWire JACK is not installed. Some DAW/JACK functionality may be unavailable."
            )
            note.setStyleSheet(f"color: {C_WARN}; background: transparent; font-size: 11px;")
            note.setWordWrap(True)
            layout.addWidget(note)

        layout.addStretch()
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok)
        buttons.accepted.connect(self.accept)
        layout.addWidget(buttons)

    def _add_component_row(self, layout: QVBoxLayout, comp) -> None:
        row = QWidget()
        hl = QHBoxLayout(row)
        hl.setContentsMargins(0, 2, 0, 2)

        if comp.ok:
            color = C_OK
        elif comp.installed and comp.running is False:
            color = C_WARN
        else:
            color = C_ERROR

        symbol = QLabel(comp.symbol)
        symbol.setStyleSheet(f"color: {color}; font-size: 14px; background: transparent;")
        symbol.setFixedWidth(20)

        name = QLabel(comp.name)
        name.setStyleSheet(f"color: {TEXT_PRIMARY}; background: transparent;")

        detail_parts = []
        if comp.installed:
            detail_parts.append("Installed")
        else:
            detail_parts.append("Not installed")
        if comp.running is True:
            detail_parts.append("Running")
        elif comp.running is False:
            detail_parts.append("Not running")
        if comp.version:
            detail_parts.append(comp.version.split("\n")[0][:40])
        if comp.note:
            detail_parts.append(comp.note)

        detail = QLabel(" · ".join(detail_parts))
        detail.setStyleSheet(f"color: {TEXT_SECONDARY}; font-size: 11px; background: transparent;")

        hl.addWidget(symbol)
        hl.addWidget(name)
        hl.addStretch()
        hl.addWidget(detail)
        layout.addWidget(row)
