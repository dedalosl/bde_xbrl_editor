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
WINDOW_BG = "#F6F1E7"
PANEL_BG = "#F1E8D7"
SURFACE_BG = "#FBF8F2"
SURFACE_ALT_BG = "#F4EEDF"
INPUT_BG = "#FFFDF9"

# Header and navigation tones
HEADER_BG = "#E5C99B"
HEADER_BG_LIGHT = "#F3DFC0"
HEADER_BG_DARK = "#D3B17D"
HEADER_SURFACE_BG = "#F1D7AA"
HEADER_LEVEL_BACKGROUNDS = (
    "#E9C58D",  # level 0
    "#F1D4A8",  # level 1
    "#F7E6C9",  # level 2
    "#FCF6E9",  # level 3+
)
NAV_BG = "#C8A978"
NAV_BG_DARK = "#B18C5B"
NAV_BG_DEEP = "#8F6E43"

# Borders and accents
BORDER = "#B8A27F"
BORDER_STRONG = "#8B734B"
ACCENT = "#A8854E"
ACCENT_SOFT = "#E8D3AF"
HEADER_LEVEL_ACCENTS = (
    "#B99863",  # level 0
    "#CCAF7B",  # level 1
    "#E0C89E",  # level 2
    "#E8D3AF",  # level 3+
)

# Text
TEXT_MAIN = "#2E261B"
TEXT_MUTED = "#6F5C43"
TEXT_INVERSE = "#FFFDF8"
TEXT_SUBTLE = "#8E7A60"

# States
SELECTION_BG = "#D9BC8C"
SELECTION_FG = TEXT_MAIN
HOVER_BG = "#EEE0C6"
DISABLED_BG = "#E6DED1"
DISABLED_FG = "#9F927C"
WARNING_BG = "#FFF2DA"
WARNING_FG = "#7A5A22"

# Table body
CELL_BG = "#FFFDFC"
CELL_BG_MUTED = "#F7F1E6"
CELL_BG_DISABLED = "#C8C3BB"
CELL_BG_DUPLICATE = "#F6D6D0"
