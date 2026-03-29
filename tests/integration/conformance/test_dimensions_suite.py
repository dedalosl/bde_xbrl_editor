"""Integration tests for the Dimensions 1.0 conformance suite."""

from __future__ import annotations

from pathlib import Path

import pytest

from bde_xbrl_editor.conformance.models import SuiteStatus
from bde_xbrl_editor.conformance.parser import ConformanceSuiteParser
from bde_xbrl_editor.conformance.registry import SUITE_REGISTRY
from bde_xbrl_editor.conformance.runner import ConformanceRunner

from .conftest import dimensions_available


@dimensions_available
def test_dimensions_suite_parses_without_error(suite_data_dir: Path) -> None:
    """The Dimensions 1.0 index and test cases should parse without raising."""
    parser = ConformanceSuiteParser(suite_data_dir)
    suite_def = SUITE_REGISTRY["dimensions"]
    test_cases = parser.load_suite(suite_def)
    assert len(test_cases) > 0, "Expected at least one test case"


@dimensions_available
def test_dimensions_suite_has_error_code_variations(suite_data_dir: Path) -> None:
    """Dimensions suite should have variations with specific error codes."""
    from bde_xbrl_editor.conformance.models import ExpectedOutcomeType

    parser = ConformanceSuiteParser(suite_data_dir)
    suite_def = SUITE_REGISTRY["dimensions"]
    test_cases = parser.load_suite(suite_def)

    error_code_variations = [
        v
        for tc in test_cases
        for v in tc.variations
        if v.expected_outcome.outcome_type == ExpectedOutcomeType.ERROR
        and v.expected_outcome.error_code is not None
    ]
    assert len(error_code_variations) > 0, "Expected variations with specific error codes"


@dimensions_available
@pytest.mark.slow
def test_dimensions_runner_completes(suite_data_dir: Path) -> None:
    runner = ConformanceRunner(
        suite_data_dir=suite_data_dir,
        selected_suites=["dimensions"],
    )
    report = runner.run()
    dim_result = next(
        (sr for sr in report.suite_results if sr.suite_id == "dimensions"), None
    )
    assert dim_result is not None
    assert dim_result.status in (
        SuiteStatus.PASSED,
        SuiteStatus.FAILED,
        SuiteStatus.ERRORED,
    )
