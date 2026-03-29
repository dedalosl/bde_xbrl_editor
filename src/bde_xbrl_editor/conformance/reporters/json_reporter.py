"""JsonReporter — serialises a SuiteRunReport to JSON."""

from __future__ import annotations

import json
from pathlib import Path

from bde_xbrl_editor.conformance.models import SuiteRunReport, TestCaseResult


class JsonReporter:
    """Converts a SuiteRunReport to a JSON-serialisable dict and writes it to a file."""

    def to_dict(self, report: SuiteRunReport) -> dict:
        """Convert report to a JSON-serialisable dictionary."""
        suites = []
        for sr in report.suite_results:
            results = [self._result_to_dict(r) for r in sr.results]
            suites.append({
                "suite_id": sr.suite_id,
                "label": sr.label,
                "blocking": sr.blocking,
                "status": sr.status.value,
                "total": sr.total,
                "passed": sr.passed,
                "failed": sr.failed,
                "failed_optional": sr.failed_optional,
                "errored": sr.errored,
                "skipped": sr.skipped,
                "informational_note": sr.informational_note,
                "results": results,
            })

        return {
            "run_timestamp": report.run_timestamp.isoformat(),
            "runner_version": report.runner_version,
            "overall_passed": report.overall_passed,
            "exit_code": report.exit_code,
            "suites": suites,
        }

    def write(self, report: SuiteRunReport, path: Path) -> None:
        """Write the report as JSON to the given path.

        Raises:
            PermissionError: if the file cannot be written.
        """
        data = self.to_dict(report)
        try:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
        except PermissionError:
            raise
        except OSError as exc:
            raise PermissionError(f"Cannot write report to '{path}': {exc}") from exc

    def _result_to_dict(self, r: TestCaseResult) -> dict:
        return {
            "variation_id": r.variation_id,
            "test_case_id": r.test_case_id,
            "suite_id": r.suite_id,
            "outcome": r.outcome.value,
            "mandatory": r.mandatory,
            "expected_outcome": {
                "type": r.expected_outcome.outcome_type.value,
                "error_code": r.expected_outcome.error_code,
            },
            "actual_error_codes": list(r.actual_error_codes),
            "exception_message": r.exception_message,
            "description": r.description,
            "input_files": [str(f) for f in r.input_files],
            "duration_ms": r.duration_ms,
        }
