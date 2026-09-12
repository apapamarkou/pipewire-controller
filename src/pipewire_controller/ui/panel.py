# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2024 Andrianos Papamarkou
"""Main control panel — docked/floating side panel."""

from __future__ import annotations

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QCursor
from PyQt6.QtWidgets import (
    QApplication,
    QHBoxLayout,
    QLabel,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from ..log import get_logger
from .accordion import AccordionSection
from .components.flat_button import FlatButton
from .theme import (
    BG_PANEL,
    BORDER,
    PANEL_STYLE,
    TEXT_SECONDARY,
    TOOLBAR_BTN_STYLE,
)

log = get_logger("panel")

_MIN_WIDTH = 260
_MAX_WIDTH = 600
_DEFAULT_WIDTH = 340
_RESIZE_MARGIN = 6  # px from left edge that triggers resize drag


class ToolbarButton(FlatButton):
    """Small round toolbar button."""

    def __init__(self, text: str, tooltip: str, checkable: bool = False) -> None:
        super().__init__(text)
        self.setToolTip(tooltip)
        self.setCheckable(checkable)
        self.setStyleSheet(TOOLBAR_BTN_STYLE)
        self.setFixedSize(20, 20)


class PanelToolbar(QWidget):
    """Top toolbar with panel control buttons."""

    float_toggled = pyqtSignal(bool)
    pin_toggled = pyqtSignal(bool)
    ontop_toggled = pyqtSignal(bool)
    autoload_toggled = pyqtSignal(bool)
    info_requested = pyqtSignal()

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(6, 4, 6, 4)
        layout.setSpacing(4)

        title = QLabel("PW Control")
        title.setStyleSheet(
            f"color: {TEXT_SECONDARY}; font-size: 11px; font-weight: bold; background: transparent;"
        )
        layout.addWidget(title)
        layout.addStretch()

        self._btn_float = ToolbarButton("⊞", "Floating / Docked", checkable=True)
        self._btn_ontop = ToolbarButton("⊤", "Always on top", checkable=True)
        self._btn_pin = ToolbarButton("⊕", "Pin (keep visible)", checkable=True)
        self._btn_auto = ToolbarButton("⟳", "Auto-load config on startup", checkable=True)
        self._btn_info = ToolbarButton("ℹ", "System info")

        for btn in (
            self._btn_float,
            self._btn_ontop,
            self._btn_pin,
            self._btn_auto,
            self._btn_info,
        ):
            layout.addWidget(btn)

        self._btn_float.toggled.connect(self.float_toggled)
        self._btn_ontop.toggled.connect(self.ontop_toggled)
        self._btn_pin.toggled.connect(self.pin_toggled)
        self._btn_auto.toggled.connect(self.autoload_toggled)
        self._btn_info.clicked.connect(self.info_requested)

        self.setStyleSheet(f"background-color: {BG_PANEL}; border-bottom: 1px solid {BORDER};")
        self.setFixedHeight(30)

    def set_state(self, floating: bool, ontop: bool, pinned: bool, autoload: bool) -> None:
        for btn, val in (
            (self._btn_float, floating),
            (self._btn_ontop, ontop),
            (self._btn_pin, pinned),
            (self._btn_auto, autoload),
        ):
            btn.blockSignals(True)
            btn.setChecked(val)
            btn.blockSignals(False)


class ControlPanel(QWidget):
    """
    Main control panel widget.

    Can be docked to the right edge of the screen or float freely.
    Contains a scrollable area of accordion sections.
    """

    closed = pyqtSignal()

    def __init__(self, config: dict, parent: QWidget | None = None) -> None:
        super().__init__(parent, Qt.WindowType.Tool)
        self._config = config
        self._sections: dict[str, AccordionSection] = {}
        self._floating = config.get("window", {}).get("docked", True) is False
        self._always_on_top = config.get("window", {}).get("always_on_top", False)
        self._pinned = config.get("window", {}).get("pinned", False)
        self._resizing = False
        self._resize_start_x = 0
        self._resize_start_w = 0
        self._resize_start_left = 0

        self._build_ui()
        self._apply_window_flags()
        self._restore_geometry()

    def _build_ui(self) -> None:
        self.setStyleSheet(PANEL_STYLE)
        self.setMinimumWidth(_MIN_WIDTH)
        self.setMaximumWidth(_MAX_WIDTH)

        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        self._toolbar = PanelToolbar()
        self._toolbar.float_toggled.connect(self._on_float_toggled)
        self._toolbar.ontop_toggled.connect(self._on_ontop_toggled)
        self._toolbar.pin_toggled.connect(self._on_pin_toggled)
        self._toolbar.autoload_toggled.connect(self._on_autoload_toggled)
        self._toolbar.info_requested.connect(self._on_info_requested)
        root.addWidget(self._toolbar)

        # Scrollable content area
        self._scroll = QScrollArea()
        self._scroll.setWidgetResizable(True)
        self._scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self._scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)

        self._content = QWidget()
        self._content_layout = QVBoxLayout(self._content)
        self._content_layout.setContentsMargins(0, 0, 0, 0)
        self._content_layout.setSpacing(0)
        self._content_layout.addStretch()

        self._scroll.setWidget(self._content)
        root.addWidget(self._scroll)

        self._toolbar.set_state(
            floating=self._floating,
            ontop=self._always_on_top,
            pinned=self._pinned,
            autoload=self._config.get("window", {}).get("auto_load", False),
        )

        self.setMouseTracking(True)

    def add_section(self, key: str, title: str) -> AccordionSection:
        """Add a named accordion section. Returns the section for content population."""
        section = AccordionSection(title)
        # Restore expanded state from config
        accordion_state = self._config.get("window", {}).get("accordion_state", {})
        expanded = accordion_state.get(key, True)
        section.set_expanded(expanded)
        section.toggled.connect(lambda exp, k=key: self._on_section_toggled(k, exp))

        # Insert before the trailing stretch
        count = self._content_layout.count()
        self._content_layout.insertWidget(count - 1, section)
        self._sections[key] = section
        return section

    def get_section(self, key: str) -> AccordionSection | None:
        return self._sections.get(key)

    def _on_section_toggled(self, key: str, expanded: bool) -> None:
        self._config.setdefault("window", {}).setdefault("accordion_state", {})[key] = expanded

    def _on_float_toggled(self, floating: bool) -> None:
        self._floating = floating
        self._config.setdefault("window", {})["docked"] = not floating
        self._apply_window_flags()
        if not floating:
            self.reposition()

    def _on_ontop_toggled(self, ontop: bool) -> None:
        self._always_on_top = ontop
        self._config.setdefault("window", {})["always_on_top"] = ontop
        self._apply_window_flags()

    def _on_pin_toggled(self, pinned: bool) -> None:
        self._pinned = pinned
        self._config.setdefault("window", {})["pinned"] = pinned

    def _on_autoload_toggled(self, autoload: bool) -> None:
        self._config.setdefault("window", {})["auto_load"] = autoload

    def _on_info_requested(self) -> None:
        from .dialogs import SystemInfoDialog

        dlg = SystemInfoDialog(self)
        dlg.exec()

    def _apply_window_flags(self) -> None:
        flags = Qt.WindowType.Tool | Qt.WindowType.FramelessWindowHint
        if self._always_on_top:
            flags |= Qt.WindowType.WindowStaysOnTopHint
        was_visible = self.isVisible()
        self.setWindowFlags(flags)
        if was_visible:
            self.show()

    def _dock_to_right(self) -> None:
        screen = QApplication.primaryScreen()
        if screen is None:
            return
        geo = screen.availableGeometry()
        w = self._config.get("window", {}).get("width", _DEFAULT_WIDTH)
        self.setGeometry(geo.right() - w, geo.top(), w, geo.height())

    def _restore_geometry(self) -> None:
        w = self._config.get("window", {}).get("width", _DEFAULT_WIDTH)
        self.resize(w, 800)  # initial size; reposition() called after show()

    def reposition(self) -> None:
        """Position the panel at the right edge. Call after show() for Wayland compatibility."""
        screen = QApplication.primaryScreen()
        if screen is None:
            return
        geo = screen.availableGeometry()
        w = self._config.get("window", {}).get("width", _DEFAULT_WIDTH)
        self.setGeometry(geo.right() - w, geo.top(), w, geo.height())

    def save_geometry(self) -> None:
        self._config.setdefault("window", {})["width"] = self.width()

    def toggle_visible(self) -> None:
        if self.isVisible():
            self.hide()
        else:
            self.show()
            self.raise_()
            self.activateWindow()

    def _in_resize_zone(self, x: int) -> bool:
        return x <= _RESIZE_MARGIN

    def mousePressEvent(self, event) -> None:
        if event.button() == Qt.MouseButton.LeftButton and self._in_resize_zone(
            event.position().x()
        ):
            self._resizing = True
            self._resize_start_x = event.globalPosition().x()
            self._resize_start_w = self.width()
            self._resize_start_left = self.x()
            event.accept()
        else:
            super().mousePressEvent(event)

    def mouseMoveEvent(self, event) -> None:
        if self._resizing:
            delta = int(self._resize_start_x - event.globalPosition().x())
            new_w = max(_MIN_WIDTH, min(_MAX_WIDTH, self._resize_start_w + delta))
            self.setGeometry(
                self._resize_start_left + self._resize_start_w - new_w,
                self.y(),
                new_w,
                self.height(),
            )
            event.accept()
        else:
            if self._in_resize_zone(event.position().x()):
                self.setCursor(QCursor(Qt.CursorShape.SizeHorCursor))
            else:
                self.unsetCursor()
            super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event) -> None:
        if self._resizing and event.button() == Qt.MouseButton.LeftButton:
            self._resizing = False
            event.accept()
        else:
            super().mouseReleaseEvent(event)

    def resizeEvent(self, event) -> None:
        super().resizeEvent(event)
        self._config.setdefault("window", {})["width"] = self.width()

    def closeEvent(self, event) -> None:
        if self._pinned:
            event.ignore()
            return
        event.accept()
        self.closed.emit()
