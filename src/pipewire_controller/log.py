# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2024 Andrianos Papamarkou
"""Structured logging for PipeWire Audio Control Center."""

import logging
import sys


def get_logger(name: str) -> logging.Logger:
    return logging.getLogger(f"pipewire_controller.{name}")


def setup_logging(debug: bool = False) -> None:
    level = logging.DEBUG if debug else logging.INFO
    handler = logging.StreamHandler(sys.stderr)
    handler.setFormatter(
        logging.Formatter("%(asctime)s %(levelname)-8s %(name)s: %(message)s", "%H:%M:%S")
    )
    root = logging.getLogger("pipewire_controller")
    root.setLevel(level)
    if not root.handlers:
        root.addHandler(handler)
