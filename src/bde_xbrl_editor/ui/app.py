"""Application factory — creates and returns the main window."""

from __future__ import annotations

from bde_xbrl_editor.ui.main_window import MainWindow


def create_app() -> MainWindow:
    """Create and return the application main window."""
    return MainWindow()
