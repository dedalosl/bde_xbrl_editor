"""Unit tests for TestCaseExecutor._match_outcome."""

from __future__ import annotations

import pytest

from bde_xbrl_editor.conformance.executor import TestCaseExecutor
from bde_xbrl_editor.conformance.models import (
    ExpectedOutcome,
    ExpectedOutcomeType,
    TestResultOutcome,
)
from bde_xbrl_editor.taxonomy.cache import TaxonomyCache
from bde_xbrl_editor.validation.models import ValidationFinding, ValidationSeverity


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_executor() -> TestCaseExecutor:
    return TestCaseExecutor(TaxonomyCache(max_size=1))


def _error_finding(rule_id: str) -> ValidationFinding:
    return ValidationFinding(
        rule_id=rule_id,
        severity=ValidationSeverity.ERROR,
        message="test error",
        source="structural",
    )


def _warning_finding(rule_id: str) -> ValidationFinding:
    return ValidationFinding(
        rule_id=rule_id,
        severity=ValidationSeverity.WARNING,
        message="test warning",
        source="structural",
    )


# ---------------------------------------------------------------------------
# VALID expected
# ---------------------------------------------------------------------------


def test_valid_no_findings_passes() -> None:
    executor = _make_executor()
    expected = ExpectedOutcome(outcome_type=ExpectedOutcomeType.VALID)
    outcome, codes = executor._match_outcome(expected, (), None)
    assert outcome == TestResultOutcome.PASS
    assert codes == ()


def test_valid_with_error_findings_fails() -> None:
    executor = _make_executor()
    expected = ExpectedOutcome(outcome_type=ExpectedOutcomeType.VALID)
    findings = (_error_finding("xbrl:someError"),)
    outcome, codes = executor._match_outcome(expected, findings, None, None)
    assert outcome == TestResultOutcome.FAIL
    assert "xbrl:someError" in codes


def test_formula_valid_ignores_s_equal_structural_and_calc_errors() -> None:
    """Formula suite VALID: duplicate-fact / summation-inconsistent are out of scope."""
    executor = _make_executor()
    expected = ExpectedOutcome(outcome_type=ExpectedOutcomeType.VALID)
    findings = (
        ValidationFinding(
            rule_id="structural:duplicate-fact",
            severity=ValidationSeverity.ERROR,
            message="dup",
            source="structural",
        ),
        ValidationFinding(
            rule_id="calculation:summation-inconsistent",
            severity=ValidationSeverity.ERROR,
            message="calc",
            source="calculation",
        ),
    )
    outcome, codes = executor._match_outcome(expected, findings, None, "formula")
    assert outcome == TestResultOutcome.PASS
    assert codes == ()


def test_formula_valid_still_fails_on_other_structural_errors() -> None:
    executor = _make_executor()
    expected = ExpectedOutcome(outcome_type=ExpectedOutcomeType.VALID)
    findings = (_error_finding("structural:unresolved-context-ref"),)
    outcome, codes = executor._match_outcome(expected, findings, None, "formula")
    assert outcome == TestResultOutcome.FAIL
    assert "structural:unresolved-context-ref" in codes


def test_valid_with_load_error_fails() -> None:
    executor = _make_executor()
    expected = ExpectedOutcome(outcome_type=ExpectedOutcomeType.VALID)
    outcome, codes = executor._match_outcome(expected, (), ValueError("bad"))
    assert outcome == TestResultOutcome.FAIL


def test_valid_with_only_warnings_passes() -> None:
    executor = _make_executor()
    expected = ExpectedOutcome(outcome_type=ExpectedOutcomeType.VALID)
    findings = (_warning_finding("xbrl:someWarning"),)
    outcome, codes = executor._match_outcome(expected, findings, None)
    assert outcome == TestResultOutcome.PASS


# ---------------------------------------------------------------------------
# ERROR expected (any error)
# ---------------------------------------------------------------------------


def test_error_any_with_error_finding_passes() -> None:
    executor = _make_executor()
    expected = ExpectedOutcome(outcome_type=ExpectedOutcomeType.ERROR, error_code=None)
    findings = (_error_finding("xbrl:someError"),)
    outcome, codes = executor._match_outcome(expected, findings, None)
    assert outcome == TestResultOutcome.PASS


def test_error_any_with_load_error_passes() -> None:
    executor = _make_executor()
    expected = ExpectedOutcome(outcome_type=ExpectedOutcomeType.ERROR, error_code=None)
    outcome, codes = executor._match_outcome(expected, (), RuntimeError("load failed"))
    assert outcome == TestResultOutcome.PASS


def test_error_any_with_no_errors_fails() -> None:
    executor = _make_executor()
    expected = ExpectedOutcome(outcome_type=ExpectedOutcomeType.ERROR, error_code=None)
    outcome, codes = executor._match_outcome(expected, (), None)
    assert outcome == TestResultOutcome.FAIL


# ---------------------------------------------------------------------------
# ERROR expected (specific code)
# ---------------------------------------------------------------------------


def test_error_code_matching_finding_passes() -> None:
    executor = _make_executor()
    expected = ExpectedOutcome(
        outcome_type=ExpectedOutcomeType.ERROR,
        error_code="xbrldte:HypercubeElementIsNotAbstractError",
    )
    findings = (_error_finding("xbrldte:HypercubeElementIsNotAbstractError"),)
    outcome, codes = executor._match_outcome(expected, findings, None)
    assert outcome == TestResultOutcome.PASS


def test_error_code_wrong_code_fails() -> None:
    executor = _make_executor()
    expected = ExpectedOutcome(
        outcome_type=ExpectedOutcomeType.ERROR,
        error_code="xbrldte:SomeSpecificError",
    )
    findings = (_error_finding("xbrldte:OtherError"),)
    outcome, codes = executor._match_outcome(expected, findings, None)
    assert outcome == TestResultOutcome.FAIL


def test_error_code_in_load_error_message_passes() -> None:
    executor = _make_executor()
    expected = ExpectedOutcome(
        outcome_type=ExpectedOutcomeType.ERROR,
        error_code="xbrldte:HypercubeElementIsNotAbstractError",
    )
    load_error = Exception("HypercubeElementIsNotAbstractError was raised")
    outcome, codes = executor._match_outcome(expected, (), load_error)
    assert outcome == TestResultOutcome.PASS


def test_error_code_no_match_anywhere_fails() -> None:
    executor = _make_executor()
    expected = ExpectedOutcome(
        outcome_type=ExpectedOutcomeType.ERROR,
        error_code="xbrldte:VerySpecificError",
    )
    outcome, codes = executor._match_outcome(expected, (), None)
    assert outcome == TestResultOutcome.FAIL


# ---------------------------------------------------------------------------
# Skip list
# ---------------------------------------------------------------------------


def test_skip_list_returns_skipped_result(tmp_path) -> None:
    from bde_xbrl_editor.conformance.models import (
        ExpectedOutcome,
        ExpectedOutcomeType,
        TestCase,
        TestVariation,
    )

    executor = TestCaseExecutor(
        TaxonomyCache(max_size=1),
        formula_skip_list=frozenset(["V-01"]),
    )
    variation = TestVariation(
        variation_id="V-01",
        name="Skipped",
        description=None,
        input_files=(),
        instance_file=None,
        taxonomy_file=None,
        expected_outcome=ExpectedOutcome(outcome_type=ExpectedOutcomeType.VALID),
        mandatory=True,
    )
    test_case = TestCase(
        test_case_id="TC-001",
        description="",
        source_file=tmp_path / "tc.xml",
        suite_id="formula",
        variations=(variation,),
    )
    result = executor.execute(variation, test_case)
    assert result.outcome == TestResultOutcome.SKIPPED
    assert result.duration_ms == 0
