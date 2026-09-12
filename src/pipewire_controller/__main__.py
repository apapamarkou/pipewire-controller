# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2024 Andrianos Papamarkou
"""Application entry point."""

import sys

from .log import setup_logging
from .ui.tray import run


def main() -> None:
    setup_logging("--debug" in sys.argv)
    sys.exit(run(sys.argv))


if __name__ == "__main__":
    main()
