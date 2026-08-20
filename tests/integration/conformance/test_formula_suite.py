"""Integration tests for the Formula 1.0 conformance suite."""

from __future__ import annotations

from pathlib import Path

import pytest

from bde_xbrl_editor.conformance.executor import TestCaseExecutor
from bde_xbrl_editor.conformance.models import SuiteStatus, TestResultOutcome
from bde_xbrl_editor.conformance.parser import ConformanceSuiteParser
from bde_xbrl_editor.conformance.registry import SUITE_REGISTRY
from bde_xbrl_editor.conformance.runner import ConformanceRunner
from bde_xbrl_editor.taxonomy.cache import TaxonomyCache

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
        v for tc in test_cases for v in tc.variations if v.taxonomy_file is not None
    ]
    assert len(variations_with_taxonomy) > 0


@formula_available
def test_formula_assertion_processing_regressions(suite_data_dir: Path) -> None:
    """Representative official assertions keep their normative result counts."""
    test_cases = ConformanceSuiteParser(suite_data_dir).load_suite(SUITE_REGISTRY["formula"])
    cases_by_number = {test_case.test_case_id.split()[0]: test_case for test_case in test_cases}
    expected_outcomes = {
        ("31210", "V-01"): TestResultOutcome.PASS,
        ("31220", "V-01"): TestResultOutcome.PASS,
        ("31230", "V-03"): TestResultOutcome.PASS,
        ("31440", "V-01"): TestResultOutcome.PASS,
        ("32210", "V-05"): TestResultOutcome.PASS,
        ("33210", "V-08"): TestResultOutcome.PASS,
        ("23020", "V-01"): TestResultOutcome.PASS,
        ("12010", "V-01"): TestResultOutcome.PASS,
        ("12030", "V-01"): TestResultOutcome.PASS,
        ("12040", "V-02"): TestResultOutcome.PASS,
        ("12050", "V-06"): TestResultOutcome.PASS,
        ("12060", "V-10"): TestResultOutcome.PASS,
        ("12061", "V-27"): TestResultOutcome.PASS,
        ("12070", "V-04"): TestResultOutcome.PASS,
        ("12080", "V-01"): TestResultOutcome.PASS,
        ("14020", "V-01"): TestResultOutcome.PASS,
        ("22170", "V-02"): TestResultOutcome.PASS,
        ("22170", "V-04"): TestResultOutcome.PASS,
        ("22170", "V-06"): TestResultOutcome.PASS,
        ("22170", "V-07"): TestResultOutcome.PASS,
        ("22170", "V-08"): TestResultOutcome.PASS,
        ("22170", "V-10"): TestResultOutcome.PASS,
        ("22170", "V-12"): TestResultOutcome.PASS,
        ("22170", "V-15"): TestResultOutcome.PASS,
        ("22170", "V-16"): TestResultOutcome.PASS,
        ("22170", "V-20a"): TestResultOutcome.PASS,
        ("22180", "V-05"): TestResultOutcome.PASS,
        ("22040", "V-01"): TestResultOutcome.PASS,
        ("22040", "V-02"): TestResultOutcome.PASS,
        ("22040", "V-02a"): TestResultOutcome.PASS,
        ("22040", "V-02d"): TestResultOutcome.PASS,
        ("22040", "V-03a"): TestResultOutcome.PASS,
        ("42210", "V-02"): TestResultOutcome.PASS,
        ("42210", "V-03"): TestResultOutcome.PASS,
        ("48220", "V-01"): TestResultOutcome.PASS,
        ("48220", "V-02"): TestResultOutcome.PASS,
        ("48230", "V-01"): TestResultOutcome.PASS,
        ("48230", "V-02"): TestResultOutcome.PASS,
        ("48240", "V-01"): TestResultOutcome.PASS,
        ("48240", "V-02"): TestResultOutcome.PASS,
        ("48250", "V-01"): TestResultOutcome.PASS,
        ("48260", "V-01"): TestResultOutcome.PASS,
        ("48260", "V-02"): TestResultOutcome.PASS,
        ("50210", "V-01"): TestResultOutcome.PASS,
        ("50210", "V-02"): TestResultOutcome.PASS,
        ("50220", "V-01"): TestResultOutcome.PASS,
        ("50220", "V-02"): TestResultOutcome.PASS,
        ("51210", "V-01"): TestResultOutcome.PASS,
        ("51210", "V-02"): TestResultOutcome.PASS,
        ("51220", "V-02"): TestResultOutcome.PASS,
        ("51230", "V-01"): TestResultOutcome.PASS,
        ("51240", "V-01"): TestResultOutcome.PASS,
        ("51240", "V-02"): TestResultOutcome.PASS,
        ("51240", "V-03"): TestResultOutcome.PASS,
        ("51240", "V-05"): TestResultOutcome.PASS,
        ("52210", "V-02"): TestResultOutcome.PASS,
        ("52210", "V-03"): TestResultOutcome.PASS,
        ("52220", "V-01"): TestResultOutcome.PASS,
        ("52220", "V-02"): TestResultOutcome.PASS,
        ("52220", "V-03"): TestResultOutcome.PASS,
        ("53210", "V-01"): TestResultOutcome.PASS,
        ("53230", "V-01"): TestResultOutcome.PASS,
        ("53230", "V-02"): TestResultOutcome.PASS,
        ("61100", "V-21"): TestResultOutcome.PASS,
        ("61100", "V-42"): TestResultOutcome.PASS,
        ("60100", "V-01"): TestResultOutcome.PASS,
        ("60100", "V-09"): TestResultOutcome.PASS,
    }
    executor = TestCaseExecutor(TaxonomyCache(max_size=20))

    for (case_number, variation_id), expected_outcome in expected_outcomes.items():
        test_case = cases_by_number[case_number]
        variation = next(item for item in test_case.variations if item.variation_id == variation_id)
        result = executor.execute(variation, test_case)
        assert result.outcome == expected_outcome, (
            case_number,
            variation_id,
            result.actual_error_codes,
        )


@formula_available
@pytest.mark.slow
def test_formula_runner_completes(suite_data_dir: Path) -> None:
    runner = ConformanceRunner(
        suite_data_dir=suite_data_dir,
        selected_suites=["formula"],
    )
    report = runner.run()
    formula_result = next((sr for sr in report.suite_results if sr.suite_id == "formula"), None)
    assert formula_result is not None
    assert formula_result.status in (
        SuiteStatus.PASSED,
        SuiteStatus.FAILED,
        SuiteStatus.ERRORED,
        SuiteStatus.INCOMPLETE,
    )
