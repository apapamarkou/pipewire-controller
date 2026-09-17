# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2024 Andrianos Papamarkou
"""Dialogs — About, System Info, Config Manager, Latency Wizard."""

from __future__ import annotations

import threading
from pathlib import Path

from PyQt6.QtCore import QObject, Qt, QTimer, pyqtSignal
from PyQt6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QPushButton,
    QScrollArea,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from .. import __version__
from ..config import delete_preset, rename_preset, save_preset
from ..detection import detect_system
from ..system_ops import detect_distro, distro_supported, get_recipe, render_commands, run_recipe
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

# GitHub raw URL for the setup guide
_GUIDE_URL = (
    "https://raw.githubusercontent.com/apapamarkou/pipewire-controller"
    "/main/docs/PipewireSetupGuide.md"
)
# Local fallback
_GUIDE_LOCAL = Path(__file__).parent.parent.parent.parent / "docs" / "PipewireSetupGuide.md"


def _load_guide() -> str:
    """Load the setup guide — local file first, then GitHub."""
    if _GUIDE_LOCAL.exists():
        return _GUIDE_LOCAL.read_text()
    try:
        import urllib.request

        with urllib.request.urlopen(_GUIDE_URL, timeout=5) as r:
            return r.read().decode()
    except Exception:
        return "Could not load setup guide."


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


# ── Install progress dialog ────────────────────────────────────────────────────


class _InstallSignals(QObject):
    line_received = pyqtSignal(str)
    finished = pyqtSignal(bool, str)  # success, full_output


class InstallDialog(QDialog):
    """Two-phase install dialog: preview → progress → result."""

    def __init__(self, component: str, recipe, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._component = component
        self._recipe = recipe
        self._signals = _InstallSignals()
        self.setWindowTitle(f"Install {component}")
        self.setMinimumSize(500, 360)
        self.setStyleSheet(PANEL_STYLE)
        self._build_ui()

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setSpacing(8)

        # Preview label
        self._phase_lbl = QLabel(
            f"The following commands will be executed to install <b>{self._component}</b>:"
        )
        self._phase_lbl.setStyleSheet(f"color: {TEXT_PRIMARY}; background: transparent;")
        self._phase_lbl.setWordWrap(True)
        layout.addWidget(self._phase_lbl)

        # Scrollable command / output box
        self._output = QTextEdit()
        self._output.setReadOnly(True)
        self._output.setStyleSheet(
            f"background: {BG_SECTION}; color: {TEXT_PRIMARY}; "
            f"font-family: monospace; font-size: 11px; border: 1px solid {BORDER};"
        )
        scroll = QScrollArea()
        scroll.setWidget(self._output)
        scroll.setWidgetResizable(True)
        scroll.setMinimumHeight(200)
        layout.addWidget(scroll)

        # Spinner row (hidden until running)
        self._spinner_row = QWidget()
        sr = QHBoxLayout(self._spinner_row)
        sr.setContentsMargins(0, 0, 0, 0)
        self._spinner_lbl = QLabel("")
        self._spinner_lbl.setStyleSheet(f"color: {TEXT_SECONDARY}; background: transparent;")
        self._status_lbl = QLabel("")
        self._status_lbl.setStyleSheet(f"color: {TEXT_SECONDARY}; background: transparent;")
        sr.addWidget(self._spinner_lbl)
        sr.addWidget(self._status_lbl)
        sr.addStretch()
        self._spinner_row.setVisible(False)
        layout.addWidget(self._spinner_row)

        # Buttons
        self._btn_box = QDialogButtonBox()
        self._allow_btn = self._btn_box.addButton("Install", QDialogButtonBox.ButtonRole.AcceptRole)
        self._cancel_btn = self._btn_box.addButton("Cancel", QDialogButtonBox.ButtonRole.RejectRole)
        self._allow_btn.clicked.connect(self._on_allow)
        self._cancel_btn.clicked.connect(self.reject)
        layout.addWidget(self._btn_box)

        # Populate preview
        cmds = render_commands(self._recipe)
        self._output.setPlainText("\n".join(cmds))

        # Spinner animation timer
        self._spinner_frames = ["|", "/", "-", "\\"]
        self._spinner_idx = 0
        self._spinner_timer = QTimer(self)
        self._spinner_timer.timeout.connect(self._tick_spinner)

        # Wire signals
        self._signals.line_received.connect(self._on_line)
        self._signals.finished.connect(self._on_finished)

    def _on_allow(self) -> None:
        self._allow_btn.setEnabled(False)
        self._cancel_btn.setEnabled(False)
        self._output.clear()
        self._phase_lbl.setText(f"Installing <b>{self._component}</b>…")
        self._spinner_row.setVisible(True)
        self._status_lbl.setText("Running…")
        self._spinner_timer.start(120)

        threading.Thread(target=self._run, daemon=True).start()

    def _run(self) -> None:
        success, output = run_recipe(
            self._recipe,
            stdout_cb=lambda line: self._signals.line_received.emit(line),
        )
        self._signals.finished.emit(success, output)

    def _tick_spinner(self) -> None:
        self._spinner_lbl.setText(self._spinner_frames[self._spinner_idx % 4])
        self._spinner_idx += 1

    def _on_line(self, line: str) -> None:
        self._output.moveCursor(self._output.textCursor().MoveOperation.End)
        self._output.insertPlainText(line)
        self._output.moveCursor(self._output.textCursor().MoveOperation.End)

    def _on_finished(self, success: bool, _output: str) -> None:
        self._spinner_timer.stop()
        self._spinner_lbl.setText("")
        if success:
            self._status_lbl.setText(f"\u2713 {self._component} installed successfully.")
            self._status_lbl.setStyleSheet(f"color: {C_OK}; background: transparent;")
        else:
            self._status_lbl.setText("\u2717 Installation failed. See output above.")
            self._status_lbl.setStyleSheet(f"color: {C_ERROR}; background: transparent;")
        self._cancel_btn.setText("Close")
        self._cancel_btn.setEnabled(True)
        # Signal the parent to refresh status
        self.setProperty("install_success", success)


# ── System Info dialog ─────────────────────────────────────────────────────────


class SystemInfoDialog(QDialog):
    """
    System Status dialog.

    Shows per-component status rows with:
    - Colored indicator (green/yellow/red)
    - Spinner while installing
    - Fix button (enabled only if distro is supported and component is missing)
    - Info button (shows setup guide section)
    """

    _status_ready = pyqtSignal(object)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("System Status")
        self.setMinimumWidth(560)
        self.setStyleSheet(PANEL_STYLE)
        self._distro_id, _ = detect_distro()
        self._row_widgets: dict[str, dict] = {}
        self._build_ui()

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setSpacing(4)

        self._rows_layout = layout
        self._buttons_widget = QDialogButtonBox(QDialogButtonBox.StandardButton.Close)
        self._buttons_widget.rejected.connect(self.accept)

        loading = QLabel("Detecting system components…")
        loading.setStyleSheet(f"color: {TEXT_SECONDARY}; font-size: 11px; background: transparent;")
        layout.addWidget(loading)
        self._loading_lbl = loading

        layout.addStretch()
        layout.addSpacing(15)
        layout.addWidget(self._buttons_widget)

        self._status_ready.connect(self._populate)
        import threading

        threading.Thread(target=self._detect_bg, daemon=True).start()

    def _detect_bg(self) -> None:
        status = detect_system()
        self._status_ready.emit(status)

    def _populate(self, status) -> None:
        self._status = status
        # Clear everything except the buttons widget
        while self._rows_layout.count() > 0:
            item = self._rows_layout.takeAt(0)
            w = item.widget()
            if w is not None and w is not self._buttons_widget:
                w.deleteLater()
        # Re-add rows, stretch, then buttons
        rows = [
            (status.pipewire, "pipewire"),
            (status.wireplumber, "wireplumber"),
            (status.pipewire_jack, "pipewire-jack"),
            (status.qpwgraph, "qpwgraph"),
            (status.easyeffects, "easyeffects"),
        ]
        for comp, key in rows:
            self._add_row(self._rows_layout, comp, key)
        self._rows_layout.addStretch()
        self._rows_layout.addSpacing(15)

    def _add_row(self, layout: QVBoxLayout, comp, key: str) -> None:
        row = QWidget()
        hl = QHBoxLayout(row)
        hl.setContentsMargins(0, 3, 0, 3)
        hl.setSpacing(6)

        # Colored indicator
        color = self._comp_color(comp)
        symbol = QLabel(comp.symbol)
        symbol.setStyleSheet(f"color: {color}; font-size: 14px; background: transparent;")
        symbol.setFixedWidth(18)

        # Name
        name = QLabel(comp.name)
        name.setStyleSheet(f"color: {TEXT_PRIMARY}; background: transparent; font-size: 12px;")
        name.setFixedWidth(130)

        # Detail
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
            detail_parts.append(comp.version.split("\n")[0][:30])
        if comp.note:
            detail_parts.append(comp.note)
        detail = QLabel(" · ".join(detail_parts))
        detail.setStyleSheet(f"color: {TEXT_SECONDARY}; font-size: 11px; background: transparent;")

        # Spinner label (hidden by default)
        spinner = QLabel("")
        spinner.setStyleSheet(f"color: {TEXT_SECONDARY}; background: transparent; width: 14px;")
        spinner.setFixedWidth(16)

        # Fix button
        fix_btn = QPushButton("Fix")
        fix_btn.setFixedWidth(40)
        fix_btn.setFixedHeight(20)
        fix_btn.setStyleSheet(
            f"QPushButton {{ background: #2a2a2a; color: {TEXT_PRIMARY}; "
            f"border: 1px solid {BORDER}; border-radius: 3px; font-size: 10px; }}"
            f"QPushButton:hover {{ background: #333; }}"
            f"QPushButton:disabled {{ color: {TEXT_DIM}; }}"
        )
        can_fix = (
            not comp.installed
            and distro_supported(self._distro_id)
            and get_recipe(self._distro_id, key) is not None
        )
        fix_btn.setEnabled(can_fix)
        fix_btn.clicked.connect(lambda checked, k=key, c=comp: self._on_fix(k, c))

        # Info button
        info_btn = QPushButton("Info")
        info_btn.setFixedSize(40, 20)
        info_btn.setStyleSheet(
            f"QPushButton {{ background: transparent; color: {TEXT_SECONDARY}; "
            f"border: 1px solid {BORDER}; border-radius: 3px; font-size: 11px; }}"
            f"QPushButton:hover {{ color: {TEXT_PRIMARY}; background: #2a2a2a; }}"
        )
        info_btn.clicked.connect(lambda checked, k=key, c=comp: self._on_info(k, c))

        hl.addWidget(symbol)
        hl.addWidget(name)
        hl.addWidget(detail, 1)
        hl.addWidget(spinner)
        hl.addWidget(fix_btn)
        hl.addWidget(info_btn)
        layout.addWidget(row)

        self._row_widgets[key] = {
            "symbol": symbol,
            "fix_btn": fix_btn,
            "spinner": spinner,
            "detail": detail,
            "spinner_timer": None,
            "spinner_idx": 0,
        }

    @staticmethod
    def _comp_color(comp) -> str:
        if comp.ok:
            return C_OK
        if comp.installed and comp.running is False:
            return C_WARN
        return C_ERROR

    def _on_fix(self, key: str, comp) -> None:
        recipe = get_recipe(self._distro_id, key)
        if recipe is None:
            return
        dlg = InstallDialog(comp.name, recipe, self)
        dlg.exec()
        # Refresh row after install attempt
        self._refresh_row(key)

    def _refresh_row(self, key: str) -> None:
        """Re-run detection and update a single row."""
        new_status = detect_system()
        comp_map = {
            "pipewire": new_status.pipewire,
            "wireplumber": new_status.wireplumber,
            "pipewire-jack": new_status.pipewire_jack,
            "qpwgraph": new_status.qpwgraph,
            "easyeffects": new_status.easyeffects,
        }
        comp = comp_map.get(key)
        if comp is None or key not in self._row_widgets:
            return
        w = self._row_widgets[key]
        color = self._comp_color(comp)
        w["symbol"].setText(comp.symbol)
        w["symbol"].setStyleSheet(f"color: {color}; font-size: 14px; background: transparent;")
        can_fix = (
            not comp.installed
            and distro_supported(self._distro_id)
            and get_recipe(self._distro_id, key) is not None
        )
        w["fix_btn"].setEnabled(can_fix)

    def _on_info(self, key: str, comp) -> None:
        guide = _load_guide()
        # Find section for this component
        section_titles = {
            "pipewire": "Pipewire Setup",
            "pipewire-jack": "Pipewire Setup",
            "wireplumber": "Pipewire Setup",
            "qpwgraph": "Pipewire Patch Bay",
            "easyeffects": "Pipewire Easy Effects",
        }
        target = section_titles.get(key, "")
        section_text = self._extract_section(guide, target) if target else guide

        dlg = QDialog(self)
        dlg.setWindowTitle(f"Setup Instructions: {comp.name}")
        dlg.setMinimumSize(520, 400)
        dlg.setStyleSheet(PANEL_STYLE)
        v = QVBoxLayout(dlg)
        te = QTextEdit()
        te.setReadOnly(True)
        te.setPlainText(section_text)
        te.setStyleSheet(
            f"background: {BG_SECTION}; color: {TEXT_PRIMARY}; "
            f"font-family: monospace; font-size: 11px; border: 1px solid {BORDER};"
        )
        v.addWidget(te)
        link = QLabel(
            f'<a href="{_GUIDE_URL}" style="color:#5c7cfa;">View full guide on GitHub</a>'
        )
        link.setOpenExternalLinks(True)
        v.addWidget(link)
        btns = QDialogButtonBox(QDialogButtonBox.StandardButton.Close)
        btns.rejected.connect(dlg.accept)
        v.addWidget(btns)
        dlg.exec()

    @staticmethod
    def _extract_section(guide: str, section_title: str) -> str:
        """Extract lines from a ## section matching section_title."""
        lines = guide.splitlines()
        collecting = False
        result = []
        for line in lines:
            if line.startswith("## ") and section_title.lower() in line.lower():
                collecting = True
            elif collecting and line.startswith("## "):
                break
            if collecting:
                result.append(line)
        return "\n".join(result) if result else guide


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
