"""Conformance suite domain models — immutable dataclasses for results."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from pathlib import Path


# ---------------------------------------------------------------------------
# Enumerations
# ---------------------------------------------------------------------------


class SuiteStatus(str, Enum):
    PASSED = "passed"
    FAILED = "failed"
    ERRORED = "errored"
    INCOMPLETE = "incomplete"
    SKIPPED = "skipped"


class TestResultOutcome(str, Enum):
    PASS = "pass"
    FAIL = "fail"
    ERROR = "error"
    SKIPPED = "skipped"


class ExpectedOutcomeType(str, Enum):
    VALID = "valid"
    ERROR = "error"
    WARNING = "warning"


# ---------------------------------------------------------------------------
# Value objects
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class ExpectedOutcome:
    """The expected result of a conformance test variation."""

    outcome_type: ExpectedOutcomeType
    error_code: str | None = None


@dataclass(frozen=True)
class TestVariation:
    """A single variation within a conformance test case."""

    variation_id: str
    name: str
    description: str | None
    input_files: tuple[Path, ...]
    instance_file: Path | None
    taxonomy_file: Path | None
    expected_outcome: ExpectedOutcome
    mandatory: bool


@dataclass(frozen=True)
class TestCase:
    """A conformance test case grouping multiple variations."""

    test_case_id: str
    description: str
    source_file: Path
    suite_id: str
    variations: tuple[TestVariation, ...]


# ---------------------------------------------------------------------------
# Result objects
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class TestCaseResult:
    """The result of executing a single test variation."""

    variation_id: str
    test_case_id: str
    suite_id: str
    outcome: TestResultOutcome
    mandatory: bool
    expected_outcome: ExpectedOutcome
    actual_error_codes: tuple[str, ...]
    exception_message: str | None
    description: str | None
    input_files: tuple[Path, ...]
    duration_ms: int


@dataclass(frozen=True)
class SuiteResult:
    """Aggregated result for one conformance suite."""

    suite_id: str
    label: str
    blocking: bool
    status: SuiteStatus
    results: tuple[TestCaseResult, ...]
    informational_note: str | None = None

    @property
    def total(self) -> int:
        return len(self.results)

    @property
    def passed(self) -> int:
        return sum(1 for r in self.results if r.outcome == TestResultOutcome.PASS)

    @property
    def failed(self) -> int:
        """Mandatory failures."""
        return sum(
            1 for r in self.results
            if r.outcome == TestResultOutcome.FAIL and r.mandatory
        )

    @property
    def failed_optional(self) -> int:
        """Non-mandatory failures."""
        return sum(
            1 for r in self.results
            if r.outcome == TestResultOutcome.FAIL and not r.mandatory
        )

    @property
    def errored(self) -> int:
        return sum(1 for r in self.results if r.outcome == TestResultOutcome.ERROR)

    @property
    def skipped(self) -> int:
        return sum(1 for r in self.results if r.outcome == TestResultOutcome.SKIPPED)

    @property
    def failures(self) -> tuple[TestCaseResult, ...]:
        return tuple(r for r in self.results if r.outcome == TestResultOutcome.FAIL)


@dataclass(frozen=True)
class SuiteRunReport:
    """Top-level report for a complete conformance suite run."""

    run_timestamp: datetime
    runner_version: str
    suite_results: tuple[SuiteResult, ...]
    exit_code: int

    @property
    def overall_passed(self) -> bool:
        return self.exit_code == 0

    @property
    def blocking_failures(self) -> tuple[TestCaseResult, ...]:
        results: list[TestCaseResult] = []
        for sr in self.suite_results:
            if sr.blocking:
                results.extend(sr.failures)
        return tuple(results)
