"""Reporters for conformance suite results."""

from bde_xbrl_editor.conformance.reporters.console import ConsoleReporter
from bde_xbrl_editor.conformance.reporters.json_reporter import JsonReporter

__all__ = ["ConsoleReporter", "JsonReporter"]
# reporters sub-package
