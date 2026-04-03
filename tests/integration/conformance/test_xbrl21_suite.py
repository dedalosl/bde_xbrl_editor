"""Integration tests for the XBRL 2.1 conformance suite."""

from __future__ import annotations

from pathlib import Path

import pytest

from bde_xbrl_editor.conformance.models import SuiteStatus
from bde_xbrl_editor.conformance.parser import ConformanceSuiteParser
from bde_xbrl_editor.conformance.registry import SUITE_REGISTRY
from bde_xbrl_editor.conformance.runner import ConformanceRunner

from .conftest import xbrl21_available


@xbrl21_available
def test_xbrl21_suite_parses_without_error(suite_data_dir: Path) -> None:
    """The XBRL 2.1 index and test cases should parse without raising."""
    parser = ConformanceSuiteParser(suite_data_dir)
    suite_def = SUITE_REGISTRY["xbrl21"]
    test_cases = parser.load_suite(suite_def)
    assert len(test_cases) > 0, "Expected at least one test case"


@xbrl21_available
def test_xbrl21_suite_has_variations(suite_data_dir: Path) -> None:
    parser = ConformanceSuiteParser(suite_data_dir)
    suite_def = SUITE_REGISTRY["xbrl21"]
    test_cases = parser.load_suite(suite_def)
    total_variations = sum(len(tc.variations) for tc in test_cases)
    assert total_variations > 0, "Expected at least one variation"


@xbrl21_available
@pytest.mark.slow
def test_xbrl21_runner_completes(suite_data_dir: Path) -> None:
    """Run a small subset of xbrl21 suite and check the report structure."""
    runner = ConformanceRunner(
        suite_data_dir=suite_data_dir,
        selected_suites=["xbrl21"],
    )
    report = runner.run()
    xbrl_result = next(
        (sr for sr in report.suite_results if sr.suite_id == "xbrl21"), None
    )
    assert xbrl_result is not None
    assert xbrl_result.status in (
        SuiteStatus.PASSED,
        SuiteStatus.FAILED,
        SuiteStatus.ERRORED,
    )
