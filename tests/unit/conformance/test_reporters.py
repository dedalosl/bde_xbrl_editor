"""Unit tests for ConformanceReporters."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

import pytest

from bde_xbrl_editor.conformance.models import (
    ExpectedOutcome,
    ExpectedOutcomeType,
    SuiteResult,
    SuiteRunReport,
    SuiteStatus,
    TestCaseResult,
    TestResultOutcome,
)
from bde_xbrl_editor.conformance.reporters.console import ConsoleReporter
from bde_xbrl_editor.conformance.reporters.json_reporter import JsonReporter


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_result(
    outcome: TestResultOutcome = TestResultOutcome.PASS,
    mandatory: bool = True,
    variation_id: str = "V-01",
) -> TestCaseResult:
    return TestCaseResult(
        variation_id=variation_id,
        test_case_id="TC-001",
        suite_id="xbrl21",
        outcome=outcome,
        mandatory=mandatory,
        expected_outcome=ExpectedOutcome(outcome_type=ExpectedOutcomeType.VALID),
        actual_error_codes=(),
        exception_message=None,
        description="A test",
        input_files=(),
        duration_ms=10,
    )


def _make_suite_result(
    suite_id: str = "xbrl21",
    status: SuiteStatus = SuiteStatus.PASSED,
    blocking: bool = True,
    results: tuple = (),
) -> SuiteResult:
    return SuiteResult(
        suite_id=suite_id,
        label="Test Suite",
        blocking=blocking,
        status=status,
        results=results,
        informational_note=None,
    )


def _make_report(suite_results=None, exit_code: int = 0) -> SuiteRunReport:
    return SuiteRunReport(
        run_timestamp=datetime(2026, 1, 1, 12, 0, 0, tzinfo=timezone.utc),
        runner_version="1.0.0",
        suite_results=tuple(suite_results or [_make_suite_result()]),
        exit_code=exit_code,
    )


# ---------------------------------------------------------------------------
# JsonReporter tests
# ---------------------------------------------------------------------------


class TestJsonReporter:
    def test_to_dict_structure(self) -> None:
        report = _make_report()
        reporter = JsonReporter()
        d = reporter.to_dict(report)

        assert "run_timestamp" in d
        assert "runner_version" in d
        assert "overall_passed" in d
        assert "exit_code" in d
        assert "suites" in d
        assert isinstance(d["suites"], list)

    def test_to_dict_suite_fields(self) -> None:
        result = _make_result()
        suite = _make_suite_result(results=(result,))
        report = _make_report(suite_results=[suite])
        reporter = JsonReporter()
        d = reporter.to_dict(report)

        suite_d = d["suites"][0]
        assert suite_d["suite_id"] == "xbrl21"
        assert suite_d["status"] == "passed"
        assert suite_d["total"] == 1
        assert suite_d["passed"] == 1
        assert suite_d["failed"] == 0
        assert "results" in suite_d

    def test_to_dict_timestamp_is_iso(self) -> None:
        report = _make_report()
        reporter = JsonReporter()
        d = reporter.to_dict(report)
        # Should parse without error
        datetime.fromisoformat(d["run_timestamp"])

    def test_write_creates_json_file(self, tmp_path: Path) -> None:
        report = _make_report()
        reporter = JsonReporter()
        out_path = tmp_path / "report.json"
        reporter.write(report, out_path)
        assert out_path.exists()
        data = json.loads(out_path.read_text())
        assert data["runner_version"] == "1.0.0"

    def test_write_raises_permission_error_on_bad_path(self, tmp_path: Path) -> None:
        report = _make_report()
        reporter = JsonReporter()
        # Use a path inside a file (not a directory)
        file_path = tmp_path / "not_a_dir.txt"
        file_path.write_text("content")
        bad_path = file_path / "report.json"
        with pytest.raises((PermissionError, OSError)):
            reporter.write(report, bad_path)

    def test_overall_passed_true_when_exit_0(self) -> None:
        report = _make_report(exit_code=0)
        reporter = JsonReporter()
        d = reporter.to_dict(report)
        assert d["overall_passed"] is True

    def test_overall_passed_false_when_exit_1(self) -> None:
        report = _make_report(exit_code=1)
        reporter = JsonReporter()
        d = reporter.to_dict(report)
        assert d["overall_passed"] is False


# ---------------------------------------------------------------------------
# ConsoleReporter tests
# ---------------------------------------------------------------------------


class TestConsoleReporter:
    def test_print_report_no_exception(self, capsys) -> None:
        report = _make_report()
        reporter = ConsoleReporter(verbose=False, use_colour=False)
        reporter.print_report(report)
        captured = capsys.readouterr()
        assert "PASSED" in captured.out or "passed" in captured.out.lower()

    def test_print_report_verbose_shows_failures(self, capsys) -> None:
        fail_result = _make_result(TestResultOutcome.FAIL, mandatory=True)
        suite = _make_suite_result(
            status=SuiteStatus.FAILED,
            results=(fail_result,),
        )
        report = _make_report(suite_results=[suite], exit_code=1)
        reporter = ConsoleReporter(verbose=True, use_colour=False)
        reporter.print_report(report)
        captured = capsys.readouterr()
        assert "V-01" in captured.out

    def test_print_report_shows_version(self, capsys) -> None:
        report = _make_report()
        reporter = ConsoleReporter(use_colour=False)
        reporter.print_report(report)
        captured = capsys.readouterr()
        assert "1.0.0" in captured.out

    def test_print_progress_no_crash(self, capsys) -> None:
        reporter = ConsoleReporter(use_colour=False)
        reporter.print_progress("V-01", 1, 10)
        # Just ensure no exception

    def test_print_report_overall_failed(self, capsys) -> None:
        suite = _make_suite_result(status=SuiteStatus.FAILED)
        report = _make_report(suite_results=[suite], exit_code=1)
        reporter = ConsoleReporter(use_colour=False)
        reporter.print_report(report)
        captured = capsys.readouterr()
        assert "FAILED" in captured.out
