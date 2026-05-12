"""Shared UI palette for the application.

The visual direction is a restrained financial workstation: neutral surfaces,
crisp separators, dark readable text, and one subdued action colour.
"""

from __future__ import annotations


def repeated_level_color(colors: tuple[str, ...], level: int) -> str:
    """Return a hierarchy color by level, repeating the softest tone after the end."""
    if not colors:
        raise ValueError("colors must not be empty")
    if level < 0:
        level = 0
    if level >= len(colors):
        return colors[-1]
    return colors[level]

# Base surfaces
WINDOW_BG = "#F5F6F7"
PANEL_BG = "#ECEFF3"
SURFACE_BG = "#FFFFFF"
SURFACE_ALT_BG = "#F2F4F6"
INPUT_BG = "#FFFFFF"

# Header and navigation tones
HEADER_BG = "#DCE6EF"
HEADER_BG_LIGHT = "#EEF3F7"
HEADER_BG_DARK = "#A9B8C7"
HEADER_SURFACE_BG = "#E8D4B1"
HEADER_LEVEL_BACKGROUNDS = (
    "#E0C18F",  # level 0
    "#EAD3AF",  # level 1
    "#F3E4CC",  # level 2
    "#FAF4E8",  # level 3+
)
NAV_BG = "#506579"
NAV_BG_DARK = "#3E5062"
NAV_BG_DEEP = "#24313D"

# Borders and accents
BORDER = "#CBD3DB"
BORDER_STRONG = "#7F8C99"
ACCENT = "#2F6F9F"
ACCENT_SOFT = "#D8E6F0"
HEADER_LEVEL_ACCENTS = (
    "#B58E58",  # level 0
    "#CAA774",  # level 1
    "#DBC09A",  # level 2
    "#E7D7C0",  # level 3+
)

# Text
TEXT_MAIN = "#1F2933"
TEXT_MUTED = "#54616E"
TEXT_INVERSE = "#FFFFFF"
TEXT_SUBTLE = "#7A8794"

# States
SELECTION_BG = "#CFE0EF"
SELECTION_FG = TEXT_MAIN
HOVER_BG = "#EAF1F7"
DISABLED_BG = "#E2E6EA"
DISABLED_FG = "#8894A0"
WARNING_BG = "#FFF5DE"
WARNING_FG = "#765A19"

# Table body
CELL_BG = "#FFFFFF"
CELL_BG_MUTED = "#F6F8FA"
CELL_BG_DISABLED = "#DCE1E6"
CELL_BG_DUPLICATE = "#F7D7D2"
