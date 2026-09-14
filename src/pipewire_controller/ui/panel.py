# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2024 Andrianos Papamarkou
"""Main control panel — right-edge side panel."""

from __future__ import annotations

from PyQt6.QtCore import Qt, QTimer, pyqtSignal
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

_MIN_WIDTH = 400
_MAX_WIDTH = 800
_DEFAULT_WIDTH = 420
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

    autoload_toggled = pyqtSignal(bool)
    tray_icon_toggled = pyqtSignal(str)  # emits "dark" or "light"
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

        self._btn_tray = ToolbarButton(
            "\u25d1", "Tray icon: dark  (click to switch light)", checkable=True
        )
        self._btn_auto = ToolbarButton("⟳", "Auto-load config on startup", checkable=True)
        self._btn_info = ToolbarButton("ℹ", "System info")

        for btn in (self._btn_tray, self._btn_auto, self._btn_info):
            layout.addWidget(btn)

        self._btn_tray.toggled.connect(self._on_tray_toggled)
        self._btn_auto.toggled.connect(self.autoload_toggled)
        self._btn_info.clicked.connect(self.info_requested)

        self.setStyleSheet(f"background-color: {BG_PANEL}; border-bottom: 1px solid {BORDER};")
        self.setFixedHeight(30)

    def _on_tray_toggled(self, checked: bool) -> None:
        variant = "light" if checked else "dark"
        self._btn_tray.setText("\u25d0" if checked else "\u25d1")
        self._btn_tray.setToolTip(f"Tray icon: {variant}  (click to switch)")
        self.tray_icon_toggled.emit(variant)

    def set_state(self, autoload: bool, tray_icon: str = "dark") -> None:
        self._btn_auto.blockSignals(True)
        self._btn_auto.setChecked(autoload)
        self._btn_auto.blockSignals(False)

        self._btn_tray.blockSignals(True)
        is_light = tray_icon == "light"
        self._btn_tray.setChecked(is_light)
        self._btn_tray.setText("\u25d0" if is_light else "\u25d1")
        self._btn_tray.setToolTip(f"Tray icon: {tray_icon}  (click to switch)")
        self._btn_tray.blockSignals(False)


class ControlPanel(QWidget):
    """
    Main control panel — frameless, right-edge, hides on focus loss.

    On Wayland the compositor controls placement so we request the right
    edge position after show() via reposition(). Always-on-top and docking
    are not reliably available on Wayland; hide-on-focus-loss replaces them.
    """

    closed = pyqtSignal()
    tray_icon_changed = pyqtSignal(str)  # emits "dark" or "light"

    def __init__(self, config: dict, parent: QWidget | None = None) -> None:
        super().__init__(
            parent,
            Qt.WindowType.Tool
            | Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint,
        )
        self._config = config
        self._sections: dict[str, AccordionSection] = {}
        self._hide_on_focus_loss = config.get("window", {}).get("hide_on_focus_loss", True)
        self._resizing = False
        self._resize_start_x = 0
        self._resize_start_w = 0
        self._resize_start_left = 0

        # Skip taskbar / pager — panel should not appear as an app window
        self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating, True)
        self.setWindowFlag(Qt.WindowType.WindowDoesNotAcceptFocus, True)
        self.setAttribute(Qt.WidgetAttribute.WA_AlwaysShowToolTips, True)

        self._build_ui()
        self._restore_geometry()

    def _build_ui(self) -> None:
        self.setStyleSheet(PANEL_STYLE)
        self.setMinimumWidth(_MIN_WIDTH)
        self.setMaximumWidth(_MAX_WIDTH)

        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        self._toolbar = PanelToolbar()
        self._toolbar.autoload_toggled.connect(self._on_autoload_toggled)
        self._toolbar.tray_icon_toggled.connect(self._on_tray_icon_toggled)
        self._toolbar.info_requested.connect(self._on_info_requested)
        root.addWidget(self._toolbar)

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
            autoload=self._config.get("window", {}).get("auto_load", False),
            tray_icon=self._config.get("window", {}).get("tray_icon", "dark"),
        )

        self.setMouseTracking(True)

    def add_section(self, key: str, title: str) -> AccordionSection:
        section = AccordionSection(title)
        accordion_state = self._config.get("window", {}).get("accordion_state", {})
        expanded = accordion_state.get(key, True)
        section.set_expanded(expanded)
        section.toggled.connect(lambda exp, k=key: self._on_section_toggled(k, exp))
        count = self._content_layout.count()
        self._content_layout.insertWidget(count - 1, section)
        self._sections[key] = section
        return section

    def get_section(self, key: str) -> AccordionSection | None:
        return self._sections.get(key)

    def _on_section_toggled(self, key: str, expanded: bool) -> None:
        self._config.setdefault("window", {}).setdefault("accordion_state", {})[key] = expanded

    def _on_autoload_toggled(self, autoload: bool) -> None:
        self._config.setdefault("window", {})["auto_load"] = autoload

    def _on_tray_icon_toggled(self, variant: str) -> None:
        self._config.setdefault("window", {})["tray_icon"] = variant
        self.tray_icon_changed.emit(variant)

    def _on_info_requested(self) -> None:
        from .dialogs import SystemInfoDialog

        dlg = SystemInfoDialog(self)
        dlg.exec()

    def _restore_geometry(self) -> None:
        w = self._config.get("window", {}).get("width", _DEFAULT_WIDTH)
        w = max(_MIN_WIDTH, min(_MAX_WIDTH, w))
        self.resize(w, 800)

    def reposition(self) -> None:
        """Position at right edge of primary screen. Call after show() on Wayland."""
        screen = QApplication.primaryScreen()
        if screen is None:
            return
        geo = screen.availableGeometry()
        w = self._config.get("window", {}).get("width", _DEFAULT_WIDTH)
        w = max(_MIN_WIDTH, min(_MAX_WIDTH, w))
        self.setGeometry(geo.x() + geo.width() - w, geo.y(), w, geo.height())
        self._set_skip_taskbar()

    def _set_skip_taskbar(self) -> None:
        """Set _NET_WM_STATE_SKIP_TASKBAR via xprop (XWayland/KDE)."""
        import subprocess

        wid = self.winId()
        if not wid:
            return
        try:
            subprocess.run(
                [
                    "xprop",
                    "-id",
                    str(int(wid)),
                    "-f",
                    "_NET_WM_STATE",
                    "32a",
                    "-set",
                    "_NET_WM_STATE",
                    "_NET_WM_STATE_SKIP_TASKBAR,_NET_WM_STATE_SKIP_PAGER",
                ],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
        except FileNotFoundError:
            pass  # xprop not available

    def showEvent(self, event) -> None:
        super().showEvent(event)
        self._set_skip_taskbar()

    def save_geometry(self) -> None:
        self._config.setdefault("window", {})["width"] = self.width()

    def toggle_visible(self) -> None:
        if self.isVisible():
            self.hide()
        else:
            self._hide_on_focus_loss = False
            self.show()
            self.raise_()
            QTimer.singleShot(0, self.reposition)
            QTimer.singleShot(300, self._enable_focus_loss_hide)

    # ── Focus loss → hide ─────────────────────────────────────────────────────

    def changeEvent(self, event) -> None:
        super().changeEvent(event)
        from PyQt6.QtCore import QEvent

        if (
            event.type() == QEvent.Type.ActivationChange
            and not self.isActiveWindow()
            and self._hide_on_focus_loss
        ):
            # Small delay so clicks on tray icon don't cause immediate re-hide
            QTimer.singleShot(150, self._hide_if_inactive)

    def _enable_focus_loss_hide(self) -> None:
        self._hide_on_focus_loss = self._config.get("window", {}).get("hide_on_focus_loss", True)

    def _hide_if_inactive(self) -> None:
        if not self.isActiveWindow():
            self.hide()

    # ── Left-edge resize ──────────────────────────────────────────────────────

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
        event.ignore()
        self.hide()
