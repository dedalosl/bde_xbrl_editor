"""Shared UI palette for the application.

The visual direction is inspired by regulator table exports: warm sand headers,
neutral surfaces, restrained borders, and dark readable text.
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
WINDOW_BG = "#F3F1EC"
PANEL_BG = "#E7E1D6"
SURFACE_BG = "#FCFBF8"
SURFACE_ALT_BG = "#F1ECE3"
INPUT_BG = "#FFFEFC"

# Header and navigation tones
HEADER_BG = "#DCC29A"
HEADER_BG_LIGHT = "#EEE0CA"
HEADER_BG_DARK = "#B89160"
HEADER_SURFACE_BG = "#E8D4B1"
HEADER_LEVEL_BACKGROUNDS = (
    "#E0C18F",  # level 0
    "#EAD3AF",  # level 1
    "#F3E4CC",  # level 2
    "#FAF4E8",  # level 3+
)
NAV_BG = "#BDA682"
NAV_BG_DARK = "#9D7E59"
NAV_BG_DEEP = "#4F5B66"

# Borders and accents
BORDER = "#B7AEA1"
BORDER_STRONG = "#7C6D5A"
ACCENT = "#A8793F"
ACCENT_SOFT = "#E7D7C0"
HEADER_LEVEL_ACCENTS = (
    "#B58E58",  # level 0
    "#CAA774",  # level 1
    "#DBC09A",  # level 2
    "#E7D7C0",  # level 3+
)

# Text
TEXT_MAIN = "#2B2620"
TEXT_MUTED = "#665B4D"
TEXT_INVERSE = "#FFFDF8"
TEXT_SUBTLE = "#8C8377"

# States
SELECTION_BG = "#D8C6A6"
SELECTION_FG = TEXT_MAIN
HOVER_BG = "#ECE4D7"
DISABLED_BG = "#E5DFD5"
DISABLED_FG = "#9C9183"
WARNING_BG = "#FFF2DA"
WARNING_FG = "#7A5A22"

# Table body
CELL_BG = "#FFFEFC"
CELL_BG_MUTED = "#F5F0E8"
CELL_BG_DISABLED = "#C8C3BB"
CELL_BG_DUPLICATE = "#F6D6D0"
