"""Process management for single instance enforcement."""

import os
import signal
from pathlib import Path


class ProcessManager:
    """Manages application process lifecycle."""

    def __init__(self):
        self.pid_file = Path.home() / ".config" / "pipewire-controller" / "app.pid"
        self.pid_file.parent.mkdir(parents=True, exist_ok=True)

    def ensure_single_instance(self) -> None:
        """Terminate existing instance and register current process."""
        if self.pid_file.exists():
            try:
                with open(self.pid_file, "r") as f:
                    existing_pid = int(f.read().strip())
                os.kill(existing_pid, signal.SIGTERM)
            except (ProcessLookupError, ValueError, IOError):
                pass

        with open(self.pid_file, "w") as f:
            f.write(str(os.getpid()))

    def cleanup(self) -> None:
        """Remove PID file on exit."""
        if self.pid_file.exists():
            try:
                self.pid_file.unlink()
            except IOError:
                pass
