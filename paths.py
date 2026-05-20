from __future__ import annotations

import sys
from pathlib import Path


def is_frozen() -> bool:
    return getattr(sys, "frozen", False) or hasattr(sys, "_MEIPASS")


def app_dir() -> Path:
    # User-writable data (settings, stats, log) рядом с .exe.
    if is_frozen():
        return Path(sys.executable).parent
    return Path(__file__).parent


def resource_dir() -> Path:
    # Read-only ресурсы (icon, examples) — _MEIPASS под PyInstaller.
    meipass = getattr(sys, "_MEIPASS", None)
    if meipass:
        return Path(meipass)
    if is_frozen():
        return Path(sys.executable).parent
    return Path(__file__).parent
