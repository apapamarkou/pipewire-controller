# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2024 Andrianos Papamarkou
"""Dark studio theme — color constants and stylesheets."""

from PyQt6.QtGui import QColor

# ── Palette ───────────────────────────────────────────────────────────────────
BG_DEEP = "#0f0f0f"
BG_PANEL = "#141414"
BG_SECTION = "#1a1a1a"
BG_WIDGET = "#1e1e1e"
BG_INPUT = "#252525"
BG_HOVER = "#2a2a2a"
BG_ACTIVE = "#2e2e2e"

BORDER = "#2d2d2d"
BORDER_FOCUS = "#404040"

TEXT_PRIMARY = "#e0e0e0"
TEXT_SECONDARY = "#888888"
TEXT_DIM = "#555555"
TEXT_LABEL = "#aaaaaa"

# Semantic colors
C_OK = "#4caf50"
C_WARN = "#ff9800"
C_ERROR = "#f44336"
C_INFO = "#2196f3"
C_ACCENT = "#5c7cfa"

# Meter colors
C_METER_LOW = "#4caf50"
C_METER_MID = "#ff9800"
C_METER_CLIP = "#f44336"
C_METER_PEAK = "#ffffff"
C_METER_BG = "#111111"

# Qt color objects
Q_OK = QColor(C_OK)
Q_WARN = QColor(C_WARN)
Q_ERROR = QColor(C_ERROR)

# ── Stylesheets ───────────────────────────────────────────────────────────────
PANEL_STYLE = f"""
QWidget {{
    background-color: {BG_PANEL};
    color: {TEXT_PRIMARY};
    font-family: "Inter", "Noto Sans", "DejaVu Sans", sans-serif;
    font-size: 12px;
}}
QScrollArea {{
    background-color: transparent;
    border: none;
}}
QScrollBar:vertical {{
    background: {BG_DEEP};
    width: 6px;
    border-radius: 3px;
}}
QScrollBar::handle:vertical {{
    background: #333333;
    border-radius: 3px;
    min-height: 20px;
}}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
    height: 0;
}}
QComboBox {{
    background-color: {BG_INPUT};
    color: {TEXT_PRIMARY};
    border: 1px solid {BORDER};
    border-radius: 3px;
    padding: 2px 6px;
    min-height: 22px;
}}
QComboBox:hover {{
    border-color: {BORDER_FOCUS};
}}
QComboBox::drop-down {{
    border: none;
    width: 18px;
}}
QComboBox QAbstractItemView {{
    background-color: {BG_INPUT};
    color: {TEXT_PRIMARY};
    border: 1px solid {BORDER_FOCUS};
    selection-background-color: {BG_ACTIVE};
}}
QPushButton {{
    background-color: {BG_INPUT};
    color: {TEXT_PRIMARY};
    border: 1px solid {BORDER};
    border-radius: 3px;
    padding: 3px 10px;
    min-height: 22px;
}}
QPushButton:hover {{
    background-color: {BG_HOVER};
    border-color: {BORDER_FOCUS};
}}
QPushButton:pressed {{
    background-color: {BG_ACTIVE};
}}
QLabel {{
    background: transparent;
    color: {TEXT_PRIMARY};
}}
QCheckBox {{
    color: {TEXT_PRIMARY};
    spacing: 5px;
}}
QCheckBox::indicator {{
    width: 14px;
    height: 14px;
    border: 1px solid {BORDER_FOCUS};
    border-radius: 2px;
    background: {BG_INPUT};
}}
QCheckBox::indicator:checked {{
    background: {C_ACCENT};
    border-color: {C_ACCENT};
}}
QRadioButton {{
    color: {TEXT_PRIMARY};
    spacing: 5px;
}}
QRadioButton::indicator {{
    width: 14px;
    height: 14px;
    border: 1px solid {BORDER_FOCUS};
    border-radius: 7px;
    background: {BG_INPUT};
}}
QRadioButton::indicator:checked {{
    background: {C_ACCENT};
    border-color: {C_ACCENT};
}}
QSlider::groove:horizontal {{
    background: {BG_INPUT};
    height: 4px;
    border-radius: 2px;
}}
QSlider::handle:horizontal {{
    background: {C_ACCENT};
    width: 12px;
    height: 12px;
    margin: -4px 0;
    border-radius: 6px;
}}
QSlider::sub-page:horizontal {{
    background: {C_ACCENT};
    border-radius: 2px;
}}
QToolTip {{
    background-color: #1a1a1a;
    color: {TEXT_PRIMARY};
    border: 1px solid {BORDER_FOCUS};
    padding: 4px 6px;
    font-size: 11px;
}}
"""

SECTION_HEADER_STYLE = f"""
QPushButton {{
    background-color: {BG_SECTION};
    color: {TEXT_LABEL};
    border: none;
    border-bottom: 1px solid {BORDER};
    border-radius: 0;
    padding: 5px 8px;
    text-align: left;
    font-size: 11px;
    font-weight: bold;
    letter-spacing: 0.5px;
}}
QPushButton:hover {{
    background-color: {BG_HOVER};
    color: {TEXT_PRIMARY};
}}
"""

TOOLBAR_BTN_STYLE = f"""
QPushButton {{
    background-color: transparent;
    color: {TEXT_SECONDARY};
    border: 1px solid {BORDER};
    border-radius: 10px;
    padding: 0;
    min-width: 20px;
    max-width: 20px;
    min-height: 20px;
    max-height: 20px;
    font-size: 11px;
}}
QPushButton:hover {{
    background-color: {BG_HOVER};
    color: {TEXT_PRIMARY};
    border-color: {BORDER_FOCUS};
}}
QPushButton:checked {{
    background-color: {C_ACCENT};
    color: #ffffff;
    border-color: {C_ACCENT};
}}
"""

STATUS_OK_STYLE = f"color: {C_OK}; background: transparent;"
STATUS_WARN_STYLE = f"color: {C_WARN}; background: transparent;"
STATUS_ERROR_STYLE = f"color: {C_ERROR}; background: transparent;"
STATUS_DIM_STYLE = f"color: {TEXT_DIM}; background: transparent;"
LABEL_SECONDARY_STYLE = f"color: {TEXT_SECONDARY}; background: transparent; font-size: 11px;"
LABEL_DIM_STYLE = f"color: {TEXT_DIM}; background: transparent; font-size: 10px;"
