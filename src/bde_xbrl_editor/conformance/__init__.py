"""bde_xbrl_editor.conformance — XBRL conformance suite runner package."""

from bde_xbrl_editor.conformance.errors import (
    ConformanceConfigError,
    ConformanceError,
    SuiteDataMissingError,
    TestCaseParseError,
)
from bde_xbrl_editor.conformance.models import (
    SuiteResult,
    SuiteRunReport,
    SuiteStatus,
    TestCaseResult,
    TestResultOutcome,
)
from bde_xbrl_editor.conformance.registry import SUITE_REGISTRY
from bde_xbrl_editor.conformance.runner import ConformanceRunner

__all__ = [
    "ConformanceRunner",
    "SuiteRunReport",
    "SuiteResult",
    "TestCaseResult",
    "SuiteStatus",
    "TestResultOutcome",
    "SUITE_REGISTRY",
    "SuiteDataMissingError",
    "ConformanceConfigError",
    "ConformanceError",
    "TestCaseParseError",
]
