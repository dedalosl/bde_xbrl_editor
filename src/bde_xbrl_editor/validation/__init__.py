"""Instance validation — public API for Feature 005."""

from bde_xbrl_editor.validation.errors import ExportPermissionError, ValidationEngineError
from bde_xbrl_editor.validation.exporter import ValidationReportExporter
from bde_xbrl_editor.validation.models import (
    ValidationFinding,
    ValidationReport,
    ValidationSeverity,
)
from bde_xbrl_editor.validation.orchestrator import InstanceValidator

__all__ = [
    "InstanceValidator",
    "ValidationReport",
    "ValidationFinding",
    "ValidationSeverity",
    "ValidationReportExporter",
    "ValidationEngineError",
    "ExportPermissionError",
]
