"""Integration tests for the Formula 1.0 conformance suite."""

from __future__ import annotations

from pathlib import Path

import pytest

from bde_xbrl_editor.conformance.models import SuiteStatus
from bde_xbrl_editor.conformance.parser import ConformanceSuiteParser
from bde_xbrl_editor.conformance.registry import SUITE_REGISTRY
from bde_xbrl_editor.conformance.runner import ConformanceRunner

from .conftest import formula_available


@formula_available
def test_formula_suite_parses_without_error(suite_data_dir: Path) -> None:
    """The Formula 1.0 index (documentation format) and test cases parse correctly."""
    parser = ConformanceSuiteParser(suite_data_dir)
    suite_def = SUITE_REGISTRY["formula"]
    test_cases = parser.load_suite(suite_def)
    assert len(test_cases) > 0, "Expected at least one test case"


@formula_available
def test_formula_suite_uses_schema_tag(suite_data_dir: Path) -> None:
    """Formula suite uses <schema> tag rather than <xsd>."""
    parser = ConformanceSuiteParser(suite_data_dir)
    suite_def = SUITE_REGISTRY["formula"]
    test_cases = parser.load_suite(suite_def)

    # At least some variations should have taxonomy files parsed from <schema> elements
    variations_with_taxonomy = [
        v
        for tc in test_cases
        for v in tc.variations
        if v.taxonomy_file is not None
    ]
    assert len(variations_with_taxonomy) > 0


@formula_available
@pytest.mark.slow
def test_formula_runner_completes(suite_data_dir: Path) -> None:
    runner = ConformanceRunner(
        suite_data_dir=suite_data_dir,
        selected_suites=["formula"],
    )
    report = runner.run()
    formula_result = next(
        (sr for sr in report.suite_results if sr.suite_id == "formula"), None
    )
    assert formula_result is not None
    assert formula_result.status in (
        SuiteStatus.PASSED,
        SuiteStatus.FAILED,
        SuiteStatus.ERRORED,
    )
