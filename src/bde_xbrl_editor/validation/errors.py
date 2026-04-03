"""Error hierarchy for the validation subsystem."""

from __future__ import annotations


class ValidationEngineError(Exception):
    """Formula evaluator internal error (caught, converted to finding)."""


class FormulaParseError(ValidationEngineError):
    """Formula linkbase XPath expression cannot be compiled."""


class ExportPermissionError(PermissionError):
    """Export path is not writable."""
