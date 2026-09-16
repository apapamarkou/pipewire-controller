# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2024 Andrianos Papamarkou
"""
System operations — package installation, tool detection.

All privileged commands use pkexec so only one password prompt is shown.
This module has no Qt imports — pure Python/subprocess logic only.
"""

from __future__ import annotations

import shutil
import subprocess
from dataclasses import dataclass, field

# ── Tool detection ─────────────────────────────────────────────────────────────


def tool_installed(cmd: str) -> bool:
    """Return True if the command is found on PATH."""
    return shutil.which(cmd) is not None


# ── Distro detection ───────────────────────────────────────────────────────────


def detect_distro() -> tuple[str, str]:
    """Return (distro_id, version_id) from /etc/os-release."""
    try:
        with open("/etc/os-release") as f:
            data = {}
            for line in f:
                line = line.strip()
                if "=" in line:
                    k, _, v = line.partition("=")
                    data[k] = v.strip('"')
        return data.get("ID", "unknown").lower(), data.get("VERSION_ID", "")
    except OSError:
        return "unknown", ""


# ── Install recipes ────────────────────────────────────────────────────────────


@dataclass
class InstallRecipe:
    """Describes how to install something on a specific distro."""

    distro_id: str  # e.g. "ubuntu", "fedora", "arch"
    component: str  # e.g. "qpwgraph", "easyeffects", "pipewire-jack"
    # Sequence of command lists. Each list is one argv (no shell).
    # If a command needs privilege, prepend "SUDO" as a sentinel — replaced with pkexec.
    commands: list[list[str]] = field(default_factory=list)


# fmt: off
_RECIPES: list[InstallRecipe] = [
    # ── Arch ──────────────────────────────────────────────────────────────────
    InstallRecipe("arch", "qpwgraph",
        [["SUDO", "pacman", "-S", "--needed", "--noconfirm", "qpwgraph"]]),
    InstallRecipe("arch", "easyeffects",
        [["SUDO", "pacman", "-S", "--needed", "--noconfirm", "easyeffects"]]),
    InstallRecipe("arch", "pipewire-jack",
        [["SUDO", "pacman", "-S", "--needed", "--noconfirm", "pipewire-jack"]]),

    # ── Debian 13 ─────────────────────────────────────────────────────────────
    InstallRecipe("debian", "qpwgraph",
        [["SUDO", "apt-get", "install", "-y", "qpwgraph"]]),
    InstallRecipe("debian", "easyeffects",
        [["SUDO", "apt-get", "install", "-y", "easyeffects"]]),
    InstallRecipe("debian", "pipewire-jack", [
        ["SUDO", "apt-get", "install", "-y",
         "pipewire-jack", "pipewire-audio-client-libraries", "libspa-0.2-jack"],
        ["systemctl", "--user", "--now", "enable", "wireplumber.service"],
        ["SUDO", "mkdir", "-p", "/etc/pipewire/media-session.d"],
        ["SUDO", "touch", "/etc/pipewire/media-session.d/with-jack"],
        ["SUDO", "sh", "-c",
         "cp /usr/share/doc/pipewire/examples/ld.so.conf.d/pipewire-jack-*.conf "
         "/etc/ld.so.conf.d/"],
        ["SUDO", "ldconfig"],
    ]),

    # ── Fedora ────────────────────────────────────────────────────────────────
    InstallRecipe("fedora", "qpwgraph",
        [["SUDO", "dnf", "install", "-y", "qpwgraph"]]),
    InstallRecipe("fedora", "easyeffects",
        [["SUDO", "dnf", "install", "-y", "easyeffects"]]),
    InstallRecipe("fedora", "pipewire-jack",
        [["SUDO", "dnf", "install", "-y", "pipewire-jack"]]),

    # ── Ubuntu ────────────────────────────────────────────────────────────────
    InstallRecipe("ubuntu", "qpwgraph",
        [["SUDO", "snap", "install", "qpwgraph"]]),
    InstallRecipe("ubuntu", "easyeffects",
        [["SUDO", "snap", "install", "easyeffects"]]),
    InstallRecipe("ubuntu", "pipewire-jack", [
        ["SUDO", "apt-get", "install", "-y",
         "pipewire-jack", "pipewire-audio-client-libraries", "libspa-0.2-jack"],
        ["systemctl", "--user", "--now", "enable", "wireplumber.service"],
        ["SUDO", "mkdir", "-p", "/etc/pipewire/media-session.d"],
        ["SUDO", "touch", "/etc/pipewire/media-session.d/with-jack"],
        ["SUDO", "sh", "-c",
         "cp /usr/share/doc/pipewire/examples/ld.so.conf.d/pipewire-jack-*.conf "
         "/etc/ld.so.conf.d/"],
        ["SUDO", "ldconfig"],
    ]),
]
# fmt: on

_SUPPORTED_DISTROS = {"arch", "debian", "fedora", "ubuntu"}


def get_recipe(distro_id: str, component: str) -> InstallRecipe | None:
    """Return the recipe for installing component on distro_id, or None."""
    for r in _RECIPES:
        if r.distro_id == distro_id and r.component == component:
            return r
    return None


def distro_supported(distro_id: str) -> bool:
    return distro_id in _SUPPORTED_DISTROS


def render_commands(recipe: InstallRecipe) -> list[str]:
    """Return human-readable command strings for preview (SUDO shown as sudo)."""
    lines = []
    for cmd in recipe.commands:
        display = [("sudo" if c == "SUDO" else c) for c in cmd]
        lines.append(" ".join(display))
    return lines


# ── Execution ─────────────────────────────────────────────────────────────────


def _build_argv(cmd: list[str]) -> list[str]:
    """Replace SUDO sentinel with pkexec."""
    if cmd and cmd[0] == "SUDO":
        return ["pkexec"] + cmd[1:]
    return cmd


def run_recipe(
    recipe: InstallRecipe,
    stdout_cb=None,  # callable(str) — receives output lines
    stderr_cb=None,
) -> tuple[bool, str]:
    """
    Execute all commands in the recipe sequentially.

    Privilege: all SUDO-marked commands are batched under a single pkexec
    shell script to avoid multiple polkit prompts.

    Returns (success, combined_output).
    """
    output_parts: list[str] = []

    # Split into privilege blocks and normal blocks.
    # Consecutive SUDO commands are merged into one pkexec sh -c "cmd1; cmd2" call.
    sudo_block: list[list[str]] = []
    blocks: list[tuple[bool, list[list[str]]]] = []  # (is_sudo, [cmds])

    for cmd in recipe.commands:
        is_sudo = bool(cmd and cmd[0] == "SUDO")
        if is_sudo:
            sudo_block.append(cmd[1:])
        else:
            if sudo_block:
                blocks.append((True, sudo_block))
                sudo_block = []
            blocks.append((False, [cmd]))
    if sudo_block:
        blocks.append((True, sudo_block))

    for is_sudo, cmds in blocks:
        if is_sudo:
            # Merge all sudo commands into one pkexec sh invocation
            shell_script = " && ".join(" ".join(_shell_quote(tok) for tok in cmd) for cmd in cmds)
            argv = ["pkexec", "sh", "-c", shell_script]
        else:
            argv = cmds[0]

        try:
            proc = subprocess.Popen(
                argv,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
            )
            for line in proc.stdout:
                output_parts.append(line)
                if stdout_cb:
                    stdout_cb(line)
            proc.wait()
            if proc.returncode != 0:
                err = f"Command exited with code {proc.returncode}\n"
                output_parts.append(err)
                if stderr_cb:
                    stderr_cb(err)
                return False, "".join(output_parts)
        except FileNotFoundError as exc:
            err = f"Command not found: {exc}\n"
            output_parts.append(err)
            if stderr_cb:
                stderr_cb(err)
            return False, "".join(output_parts)

    return True, "".join(output_parts)


def _shell_quote(s: str) -> str:
    """Minimal shell quoting for tokens passed to sh -c."""
    if not s:
        return "''"
    safe = set("abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789-_./=,:")
    if all(c in safe for c in s):
        return s
    return "'" + s.replace("'", "'\\''") + "'"
