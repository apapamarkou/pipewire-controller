# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2024 Andrianos Papamarkou
"""Dialogs — About, System Info, Config Manager, Latency Wizard."""

from __future__ import annotations

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QPushButton,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from .. import __version__
from ..config import delete_preset, rename_preset, save_preset
from ..detection import detect_system
from .theme import (
    BG_SECTION,
    BORDER,
    C_ERROR,
    C_OK,
    C_WARN,
    PANEL_STYLE,
    TEXT_DIM,
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
                "⚠  PipeWire JACK is not installed. "
                "Some DAW/JACK functionality may be unavailable."
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


class ConfigManagerDialog(QDialog):
    """Manage named configurations — list, edit, load, delete."""

    config_loaded = pyqtSignal(str)  # preset name

    def __init__(self, config: dict, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._config = config
        self.setWindowTitle("Configuration Manager")
        self.setMinimumSize(500, 360)
        self.setStyleSheet(PANEL_STYLE)
        self._build_ui()
        self._refresh_list()

    def _build_ui(self) -> None:
        layout = QHBoxLayout(self)

        # Left: preset list
        left = QVBoxLayout()
        self._list = QListWidget()
        self._list.setStyleSheet(
            f"QListWidget {{ background: {BG_SECTION}; border: 1px solid {BORDER}; }}"
            f"QListWidget::item:selected {{ background: #2e2e2e; }}"
        )
        self._list.currentTextChanged.connect(self._on_selection_changed)
        left.addWidget(self._list)
        layout.addLayout(left, 1)

        # Right: details + buttons
        right = QVBoxLayout()
        right.setSpacing(6)

        name_lbl = QLabel("Name:")
        name_lbl.setStyleSheet(f"color: {TEXT_DIM}; font-size: 10px; background: transparent;")
        self._name_edit = QLineEdit()
        self._name_edit.setReadOnly(True)

        desc_lbl = QLabel("Description:")
        desc_lbl.setStyleSheet(f"color: {TEXT_DIM}; font-size: 10px; background: transparent;")
        self._desc_edit = QTextEdit()
        self._desc_edit.setReadOnly(True)
        self._desc_edit.setMaximumHeight(80)

        right.addWidget(name_lbl)
        right.addWidget(self._name_edit)
        right.addWidget(desc_lbl)
        right.addWidget(self._desc_edit)
        right.addStretch()

        self._edit_btn = QPushButton("Edit")
        self._load_btn = QPushButton("Load")
        self._delete_btn = QPushButton("Delete")
        self._new_btn = QPushButton("New…")
        exit_btn = QPushButton("Close")

        self._edit_btn.clicked.connect(self._on_edit)
        self._load_btn.clicked.connect(self._on_load)
        self._delete_btn.clicked.connect(self._on_delete)
        self._new_btn.clicked.connect(self._on_new)
        exit_btn.clicked.connect(self.accept)

        for btn in (self._new_btn, self._edit_btn, self._load_btn, self._delete_btn, exit_btn):
            right.addWidget(btn)

        layout.addLayout(right)

    def _refresh_list(self) -> None:
        current = self._list.currentItem()
        current_text = current.text() if current else None
        self._list.clear()
        for name in self._config.get("presets", {}):
            self._list.addItem(name)
        if current_text:
            items = self._list.findItems(current_text, Qt.MatchFlag.MatchExactly)
            if items:
                self._list.setCurrentItem(items[0])

    def _on_selection_changed(self, name: str) -> None:
        preset = self._config.get("presets", {}).get(name)
        if preset is None:
            return
        self._name_edit.setText(name)
        self._desc_edit.setPlainText(preset.get("description", ""))
        active = self._config.get("active_preset")
        self._delete_btn.setEnabled(name != active)

    def _on_edit(self) -> None:
        name = self._list.currentItem()
        if name is None:
            return
        old_name = name.text()
        preset = self._config.get("presets", {}).get(old_name)
        if preset is None:
            return

        self._name_edit.setReadOnly(False)
        self._desc_edit.setReadOnly(False)
        self._edit_btn.setText("Save")
        self._edit_btn.clicked.disconnect()
        self._edit_btn.clicked.connect(lambda: self._on_save_edit(old_name))

    def _on_save_edit(self, old_name: str) -> None:
        new_name = self._name_edit.text().strip()
        new_desc = self._desc_edit.toPlainText().strip()

        if new_name and new_name != old_name:
            if not rename_preset(self._config, old_name, new_name):
                self._name_edit.setText(old_name)
                return
            old_name = new_name

        preset = self._config.get("presets", {}).get(old_name)
        if preset:
            preset["description"] = new_desc

        self._name_edit.setReadOnly(True)
        self._desc_edit.setReadOnly(True)
        self._edit_btn.setText("Edit")
        self._edit_btn.clicked.disconnect()
        self._edit_btn.clicked.connect(self._on_edit)
        self._refresh_list()

    def _on_load(self) -> None:
        item = self._list.currentItem()
        if item is None:
            return
        self.config_loaded.emit(item.text())
        self.accept()

    def _on_delete(self) -> None:
        item = self._list.currentItem()
        if item is None:
            return
        if delete_preset(self._config, item.text()):
            self._refresh_list()

    def _on_new(self) -> None:
        """Create a new preset, optionally duplicating the current one."""
        from PyQt6.QtWidgets import QCheckBox, QFormLayout

        dialog = QDialog(self)
        dialog.setWindowTitle("New Configuration")
        dialog.setMinimumWidth(320)
        dialog.setStyleSheet(PANEL_STYLE)

        form = QFormLayout()
        name_edit = QLineEdit()
        name_edit.setPlaceholderText("e.g. Studio 44.1kHz")
        duplicate_cb = QCheckBox("Duplicate current settings")
        duplicate_cb.setChecked(True)
        form.addRow("Name:", name_edit)
        form.addRow("", duplicate_cb)

        btns = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        btns.accepted.connect(dialog.accept)
        btns.rejected.connect(dialog.reject)

        vbox = QVBoxLayout(dialog)
        vbox.addLayout(form)
        vbox.addWidget(btns)

        if dialog.exec() != QDialog.DialogCode.Accepted:
            return

        new_name = name_edit.text().strip()
        if not new_name:
            return
        if new_name in self._config.get("presets", {}):
            # Name already exists — append a suffix
            base, n = new_name, 2
            while f"{base} ({n})" in self._config.get("presets", {}):
                n += 1
            new_name = f"{base} ({n})"

        if duplicate_cb.isChecked():
            import json

            active_name = self._config.get("active_preset", "Default")
            source = self._config.get("presets", {}).get(active_name, {})
            new_preset = json.loads(json.dumps(source))  # deep copy
        else:
            new_preset = {
                "name": "",
                "description": "",
                "samplerate": 48000,
                "quantum": 1024,
                "force_rate": True,
                "force_quantum": True,
                "panel_width": 420,
                "panel_docked": True,
                "always_on_top": False,
                "pinned": False,
                "auto_load": False,
                "accordion_state": {},
                "friendly_names": {},
                "channel_names": {},
                "meter_mode": "Peak",
                "master_mode": "Stereo",
                "master_channel_map": {},
            }

        new_preset["name"] = new_name
        save_preset(self._config, new_preset)
        self._refresh_list()
        # Select the new preset in the list
        items = self._list.findItems(new_name, Qt.MatchFlag.MatchExactly)
        if items:
            self._list.setCurrentItem(items[0])


class LatencyWizardDialog(QDialog):
    """
    Latency measurement wizard.

    Phase 6 will implement the actual measurement engine.
    This dialog provides the UI shell and will be wired to the
    latency measurement subsystem when that phase is complete.
    """

    measurement_complete = pyqtSignal(float, object)  # sw_ms, hw_ms (or None)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Latency Measurement")
        self.setMinimumWidth(400)
        self.setStyleSheet(PANEL_STYLE)
        self._build_ui()

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setSpacing(8)

        title = QLabel("Latency Measurement")
        title.setStyleSheet(
            f"color: {TEXT_PRIMARY}; font-size: 13px; font-weight: bold; background: transparent;"
        )
        layout.addWidget(title)

        info = QLabel(
            "Latency measurement requires audio loopback.\n\n"
            "Connect your audio output to your audio input (hardware loopback),\n"
            "then click Measure to perform a software round-trip measurement.\n\n"
            "Full automatic measurement will be available in a future update."
        )
        info.setStyleSheet(f"color: {TEXT_SECONDARY}; font-size: 11px; background: transparent;")
        info.setWordWrap(True)
        layout.addWidget(info)

        layout.addStretch()

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)
