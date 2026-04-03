"""ConsoleReporter — prints conformance run results to stdout."""

from __future__ import annotations

import sys

from bde_xbrl_editor.conformance.models import (
    SuiteRunReport,
    SuiteStatus,
    TestResultOutcome,
)

_GREEN = "\033[32m"
_RED = "\033[31m"
_YELLOW = "\033[33m"
_CYAN = "\033[36m"
_BOLD = "\033[1m"
_RESET = "\033[0m"

_STATUS_COLOUR = {
    SuiteStatus.PASSED: _GREEN,
    SuiteStatus.FAILED: _RED,
    SuiteStatus.ERRORED: _RED,
    SuiteStatus.INCOMPLETE: _YELLOW,
    SuiteStatus.SKIPPED: _CYAN,
}


class ConsoleReporter:
    """Formats and prints a SuiteRunReport to stdout."""

    def __init__(
        self,
        verbose: bool = False,
        use_colour: bool | None = None,
    ) -> None:
        self._verbose = verbose
        self._use_colour = (
            sys.stdout.isatty() if use_colour is None else use_colour
        )

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def print_report(self, report: SuiteRunReport) -> None:
        """Print the full suite run report."""
        self._print_header(report)
        self._print_table(report)
        if self._verbose:
            self._print_failures(report)
        self._print_informational_notes(report)
        self._print_banner(report)

    def print_progress(self, variation_id: str, current: int, total: int) -> None:
        """Print a single-line progress indicator (overwrites previous line on TTY)."""
        if not self._use_colour:
            return
        pct = int(current / total * 100) if total > 0 else 0
        line = f"\r  [{pct:3d}%] {current}/{total} — {variation_id[:60]:<60}"
        sys.stdout.write(line)
        sys.stdout.flush()
        if current >= total:
            sys.stdout.write("\n")
            sys.stdout.flush()

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _colour(self, text: str, code: str) -> str:
        if self._use_colour:
            return f"{code}{text}{_RESET}"
        return text

    def _print_header(self, report: SuiteRunReport) -> None:
        ts = report.run_timestamp.strftime("%Y-%m-%d %H:%M:%S UTC")
        print(f"\nBDE XBRL Editor — Conformance Suite Runner v{report.runner_version}")
        print(f"Run at: {ts}")
        print()

    def _print_table(self, report: SuiteRunReport) -> None:
        col_widths = [40, 7, 7, 7, 8, 8, 12]
        headers = ["Suite", "Total", "Passed", "Failed", "Optional", "Errored", "Status"]

        def _row(cols: list[str]) -> str:
            return "  ".join(c.ljust(w) for c, w in zip(cols, col_widths))

        header_line = _row(headers)
        print(header_line)
        print("-" * len(header_line))

        for sr in report.suite_results:
            status_str = sr.status.value.upper()
            colour = _STATUS_COLOUR.get(sr.status, "")
            coloured_status = self._colour(status_str, colour)

            cols = [
                sr.label[:38],
                str(sr.total),
                str(sr.passed),
                str(sr.failed),
                str(sr.failed_optional),
                str(sr.errored),
                coloured_status,
            ]
            # Print row without status so we can colour it separately
            base_cols = cols[:-1]
            base_line = "  ".join(c.ljust(w) for c, w in zip(base_cols, col_widths[:-1]))
            print(f"{base_line}  {coloured_status}")

        print()

    def _print_failures(self, report: SuiteRunReport) -> None:
        any_failures = False
        for sr in report.suite_results:
            for r in sr.failures:
                if not any_failures:
                    print(self._colour("=== Failures ===", _BOLD))
                    any_failures = True

                outcome_colour = _RED if r.outcome == TestResultOutcome.FAIL else _YELLOW
                outcome_str = self._colour(r.outcome.value.upper(), outcome_colour)
                mand = "" if r.mandatory else " (optional)"
                print(
                    f"  [{sr.suite_id}] {r.test_case_id}/{r.variation_id}{mand}: "
                    f"{outcome_str}"
                )
                if r.exception_message:
                    print(f"    Exception: {r.exception_message[:200]}")
                if r.actual_error_codes:
                    print(f"    Actual codes: {', '.join(r.actual_error_codes)}")
                expected = r.expected_outcome
                exp_code = f" ({expected.error_code})" if expected.error_code else ""
                print(f"    Expected: {expected.outcome_type.value}{exp_code}")
                if r.description:
                    print(f"    Description: {r.description[:120]}")

        if any_failures:
            print()

    def _print_informational_notes(self, report: SuiteRunReport) -> None:
        for sr in report.suite_results:
            if sr.informational_note and sr.status != "skipped":
                note = self._colour("NOTE", _YELLOW)
                print(f"  {note} [{sr.suite_id}]: {sr.informational_note}")
        print()

    def _print_banner(self, report: SuiteRunReport) -> None:
        if report.overall_passed:
            banner = self._colour("PASSED", _GREEN)
        else:
            banner = self._colour("FAILED", _RED)

        print(f"Overall result: {banner}  (exit code: {report.exit_code})")
        print()
