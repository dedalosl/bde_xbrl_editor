"""Unit tests for ConformanceRunner."""

from __future__ import annotations

import textwrap
from datetime import datetime
from pathlib import Path

import pytest

from bde_xbrl_editor.conformance.models import SuiteStatus, TestResultOutcome
from bde_xbrl_editor.conformance.runner import ConformanceRunner, _compute_suite_status


# ---------------------------------------------------------------------------
# _compute_suite_status tests
# ---------------------------------------------------------------------------


def _make_result(outcome: TestResultOutcome, mandatory: bool = True):
    from bde_xbrl_editor.conformance.models import (
        ExpectedOutcome,
        ExpectedOutcomeType,
        TestCaseResult,
    )
    return TestCaseResult(
        variation_id="V-01",
        test_case_id="TC-001",
        suite_id="xbrl21",
        outcome=outcome,
        mandatory=mandatory,
        expected_outcome=ExpectedOutcome(outcome_type=ExpectedOutcomeType.VALID),
        actual_error_codes=(),
        exception_message=None,
        description=None,
        input_files=(),
        duration_ms=1,
    )


def test_compute_status_all_pass() -> None:
    results = [_make_result(TestResultOutcome.PASS)]
    assert _compute_suite_status(results) == SuiteStatus.PASSED


def test_compute_status_mandatory_fail() -> None:
    results = [
        _make_result(TestResultOutcome.PASS),
        _make_result(TestResultOutcome.FAIL, mandatory=True),
    ]
    assert _compute_suite_status(results) == SuiteStatus.FAILED


def test_compute_status_optional_fail_only() -> None:
    results = [
        _make_result(TestResultOutcome.PASS),
        _make_result(TestResultOutcome.FAIL, mandatory=False),
    ]
    # Optional failure should not mark as FAILED
    status = _compute_suite_status(results)
    assert status in (SuiteStatus.PASSED,)


def test_compute_status_error() -> None:
    results = [_make_result(TestResultOutcome.ERROR)]
    assert _compute_suite_status(results) == SuiteStatus.ERRORED


def test_compute_status_all_skipped() -> None:
    results = [_make_result(TestResultOutcome.SKIPPED)]
    assert _compute_suite_status(results) == SuiteStatus.SKIPPED


def test_compute_status_empty() -> None:
    assert _compute_suite_status([]) == SuiteStatus.PASSED


# ---------------------------------------------------------------------------
# ConformanceRunner integration with missing data
# ---------------------------------------------------------------------------


def test_runner_suite_data_missing_yields_incomplete(tmp_path: Path) -> None:
    """When suite data dir doesn't exist, blocking suites become INCOMPLETE."""
    runner = ConformanceRunner(
        suite_data_dir=tmp_path / "nonexistent",
        selected_suites=["xbrl21"],
    )
    report = runner.run()
    xbrl_result = next(sr for sr in report.suite_results if sr.suite_id == "xbrl21")
    assert xbrl_result.status == SuiteStatus.INCOMPLETE


def test_runner_unselected_suites_are_skipped(tmp_path: Path) -> None:
    runner = ConformanceRunner(
        suite_data_dir=tmp_path,
        selected_suites=["xbrl21"],
    )
    report = runner.run()
    for sr in report.suite_results:
        if sr.suite_id != "xbrl21":
            assert sr.status == SuiteStatus.SKIPPED


def test_runner_exit_code_is_1_when_blocking_suite_incomplete(tmp_path: Path) -> None:
    runner = ConformanceRunner(
        suite_data_dir=tmp_path / "nonexistent",
        selected_suites=["xbrl21"],
    )
    report = runner.run()
    # xbrl21 is blocking and INCOMPLETE, so exit code should be 1
    assert report.exit_code == 1


def test_runner_exit_code_0_when_non_blocking_suite_fails(tmp_path: Path) -> None:
    """Non-blocking suites that are INCOMPLETE should not contribute to exit code 1."""
    runner = ConformanceRunner(
        suite_data_dir=tmp_path / "nonexistent",
        selected_suites=["table-linkbase"],  # non-blocking suite
    )
    report = runner.run()
    tl_result = next(sr for sr in report.suite_results if sr.suite_id == "table-linkbase")
    assert tl_result.status == SuiteStatus.INCOMPLETE
    # Non-blocking suite being INCOMPLETE should not force exit code 1
    assert report.exit_code == 0


def test_runner_report_timestamp_is_utc(tmp_path: Path) -> None:
    runner = ConformanceRunner(
        suite_data_dir=tmp_path / "nonexistent",
        selected_suites=[],
    )
    report = runner.run()
    assert report.run_timestamp.tzinfo is not None


def test_runner_report_has_runner_version(tmp_path: Path) -> None:
    runner = ConformanceRunner(
        suite_data_dir=tmp_path / "nonexistent",
        selected_suites=[],
    )
    report = runner.run()
    assert isinstance(report.runner_version, str)
    assert len(report.runner_version) > 0
