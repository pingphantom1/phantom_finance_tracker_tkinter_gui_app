"""
utils/platform_utils.py
OS-aware helpers for fonts and UI text.

Font availability by OS:
  - Windows : Segoe UI (ships with Vista+)
  - macOS   : Helvetica Neue (system font, always present)
  - Linux   : DejaVu Sans (packaged with most distros; Helvetica also common)

Emoji rendering:
  Tkinter on Windows < 10 (and some older Tk builds) can crash or show
  boxes when a label contains emoji. We replace them with plain-text
  equivalents on Windows.
"""

from __future__ import annotations

import platform
import sys

_OS = platform.system()  # "Windows", "Darwin", or "Linux"


# ---------------------------------------------------------------------------
# Font
# ---------------------------------------------------------------------------

def ui_font(size: int = 10, weight: str = "normal") -> tuple[str, int, str]:
    """
    Return a (family, size, weight) font tuple appropriate for the current OS.
    Usage: font=ui_font(12, "bold")
    """
    if _OS == "Windows":
        family = "Segoe UI"
    elif _OS == "Darwin":
        family = "Helvetica Neue"
    else:
        family = "DejaVu Sans"

    if weight == "normal":
        return (family, size)
    return (family, size, weight)


# ---------------------------------------------------------------------------
# DPI / scaling hint
# ---------------------------------------------------------------------------

def is_hidpi() -> bool:
    """
    Best-effort check for HiDPI / Retina displays.
    Used to adjust matplotlib figure DPI.
    """
    if _OS == "Darwin":
        return True  # assume Retina by default on macOS
    return False


def figure_dpi() -> int:
    """Return a sensible matplotlib figure DPI for the current display."""
    return 144 if is_hidpi() else 96
