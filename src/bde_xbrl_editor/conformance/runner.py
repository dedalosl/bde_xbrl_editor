"""ConformanceRunner — orchestrates execution of all selected conformance suites."""

from __future__ import annotations

import importlib.metadata
import logging
from collections.abc import Callable
from datetime import datetime, timezone
from pathlib import Path

from bde_xbrl_editor.conformance.errors import SuiteDataMissingError
from bde_xbrl_editor.conformance.executor import TestCaseExecutor
from bde_xbrl_editor.conformance.models import (
    SuiteResult,
    SuiteRunReport,
    SuiteStatus,
    TestCaseResult,
    TestResultOutcome,
)
from bde_xbrl_editor.conformance.parser import ConformanceSuiteParser
from bde_xbrl_editor.conformance.registry import SUITE_REGISTRY
from bde_xbrl_editor.taxonomy.cache import TaxonomyCache

log = logging.getLogger(__name__)

ProgressCallback = Callable[[str, int, int], None]


def _compute_suite_status(results: list[TestCaseResult]) -> SuiteStatus:
    """Derive a SuiteStatus from a list of test results."""
    if not results:
        return SuiteStatus.PASSED

    has_mandatory_fail = any(
        r.outcome == TestResultOutcome.FAIL and r.mandatory for r in results
    )
    has_error = any(r.outcome == TestResultOutcome.ERROR for r in results)
    all_skipped = all(r.outcome == TestResultOutcome.SKIPPED for r in results)

    if all_skipped:
        return SuiteStatus.SKIPPED
    if has_mandatory_fail:
        return SuiteStatus.FAILED
    if has_error:
        return SuiteStatus.ERRORED
    return SuiteStatus.PASSED


class ConformanceRunner:
    """Runs selected conformance suites and returns a SuiteRunReport."""

    def __init__(
        self,
        suite_data_dir: Path,
        selected_suites: list[str] | None = None,
        verbose: bool = False,
        stop_on_first_failure: bool = False,
        formula_skip_list: frozenset[str] | None = None,
    ) -> None:
        self._suite_data_dir = suite_data_dir
        self._selected_suites = selected_suites
        self._verbose = verbose
        self._stop_on_first_failure = stop_on_first_failure
        self._formula_skip_list = formula_skip_list or frozenset()

    def run(self, progress_callback: ProgressCallback | None = None) -> SuiteRunReport:
        """Execute all selected suites and return a SuiteRunReport."""
        try:
            runner_version = importlib.metadata.version("bde-xbrl-editor")
        except importlib.metadata.PackageNotFoundError:
            runner_version = "0.0.0"

        selected = self._selected_suites or list(SUITE_REGISTRY.keys())
        suite_results: list[SuiteResult] = []
        stop_requested = False

        for suite_id, suite_def in SUITE_REGISTRY.items():
            if stop_requested:
                break

            if suite_id not in selected:
                suite_results.append(
                    SuiteResult(
                        suite_id=suite_id,
                        label=suite_def.label,
                        blocking=suite_def.blocking,
                        status=SuiteStatus.SKIPPED,
                        results=(),
                        informational_note=suite_def.informational_note,
                    )
                )
                continue

            try:
                parser = ConformanceSuiteParser(self._suite_data_dir)
                test_cases = parser.load_suite(suite_def)

                cache = TaxonomyCache(max_size=50)
                executor = TestCaseExecutor(
                    cache,
                    allow_network=False,
                    formula_skip_list=self._formula_skip_list,
                )

                results: list[TestCaseResult] = []
                total_variations = sum(len(tc.variations) for tc in test_cases)
                current = 0

                outer_break = False
                for tc in test_cases:
                    if outer_break:
                        break
                    for variation in tc.variations:
                        result = executor.execute(variation, tc)
                        results.append(result)
                        current += 1

                        if progress_callback is not None:
                            try:
                                progress_callback(variation.variation_id, current, total_variations)
                            except Exception:  # noqa: BLE001
                                pass

                        if (
                            self._stop_on_first_failure
                            and result.outcome == TestResultOutcome.FAIL
                            and result.mandatory
                        ):
                            outer_break = True
                            stop_requested = True
                            break

                status = _compute_suite_status(results)
                suite_results.append(
                    SuiteResult(
                        suite_id=suite_id,
                        label=suite_def.label,
                        blocking=suite_def.blocking,
                        status=status,
                        results=tuple(results),
                        informational_note=suite_def.informational_note,
                    )
                )

            except SuiteDataMissingError as exc:
                log.warning("Suite data missing for '%s': %s", suite_id, exc)
                suite_results.append(
                    SuiteResult(
                        suite_id=suite_id,
                        label=suite_def.label,
                        blocking=suite_def.blocking,
                        status=SuiteStatus.INCOMPLETE,
                        results=(),
                        informational_note=suite_def.informational_note,
                    )
                )
            except Exception as exc:  # noqa: BLE001
                log.error("Unexpected error running suite '%s': %s", suite_id, exc)
                suite_results.append(
                    SuiteResult(
                        suite_id=suite_id,
                        label=suite_def.label,
                        blocking=suite_def.blocking,
                        status=SuiteStatus.ERRORED,
                        results=(),
                        informational_note=suite_def.informational_note,
                    )
                )

        exit_code = self._compute_exit_code(suite_results)

        return SuiteRunReport(
            run_timestamp=datetime.now(timezone.utc),
            runner_version=runner_version,
            suite_results=tuple(suite_results),
            exit_code=exit_code,
        )

    def _compute_exit_code(self, suite_results: list[SuiteResult]) -> int:
        """Return 0 if all blocking suites passed, else 1."""
        for sr in suite_results:
            if sr.blocking and sr.status not in (SuiteStatus.PASSED, SuiteStatus.SKIPPED):
                return 1
        return 0
