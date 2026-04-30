"""Unit tests for ValidationReport, ValidationFinding and ValidationFilterProxy."""
from __future__ import annotations

import dataclasses
from datetime import datetime

import pytest

from bde_xbrl_editor.performance import StageTiming
from bde_xbrl_editor.validation.models import (
    ValidationFinding,
    ValidationReport,
    ValidationSeverity,
    ValidationStatus,
)

# ---------------------------------------------------------------------------
# Helper factories
# ---------------------------------------------------------------------------


def _finding(
    rule_id: str = "structural:missing-schemaref",
    severity: ValidationSeverity = ValidationSeverity.ERROR,
    source: str = "structural",
    table_id: str | None = None,
) -> ValidationFinding:
    return ValidationFinding(
        rule_id=rule_id,
        severity=severity,
        message=f"Test finding for {rule_id}",
        source=source,  # type: ignore[arg-type]
        table_id=table_id,
    )


def _report(findings: tuple[ValidationFinding, ...] = ()) -> ValidationReport:
    return ValidationReport(
        instance_path="/some/instance.xbrl",
        taxonomy_name="ExampleTax",
        taxonomy_version="2024",
        run_timestamp=datetime(2024, 6, 1, 12, 0, 0),
        findings=findings,
        formula_linkbase_available=True,
    )


# ---------------------------------------------------------------------------
# ValidationFinding — immutability
# ---------------------------------------------------------------------------


class TestValidationFindingImmutability:
    def test_finding_is_frozen(self) -> None:
        """ValidationFinding is a frozen dataclass — attribute assignment must raise."""
        f = _finding()
        with pytest.raises((dataclasses.FrozenInstanceError, AttributeError)):
            f.rule_id = "changed"  # type: ignore[misc]

    def test_finding_severity_field_unchanged(self) -> None:
        """Frozen dataclass instances retain their original field values."""
        f = _finding(severity=ValidationSeverity.WARNING)
        assert f.severity == ValidationSeverity.WARNING

    def test_finding_equality_by_value(self) -> None:
        """Two findings with identical fields are equal (value-based equality)."""
        f1 = _finding()
        f2 = _finding()
        assert f1 == f2

    def test_finding_optional_fields_default_none(self) -> None:
        """All optional fields default to None when not provided."""
        f = _finding()
        assert f.table_id is None
        assert f.table_label is None
        assert f.concept_qname is None
        assert f.context_ref is None
        assert f.hypercube_qname is None
        assert f.dimension_qname is None
        assert f.constraint_type is None
        assert f.formula_assertion_type is None
        assert f.formula_expression is None
        assert f.formula_operands_text is None
        assert f.formula_precondition is None
        assert f.rule_label is None
        assert f.rule_label_role is None
        assert f.rule_message is None
        assert f.evaluated_rule_message is None
        assert f.rule_message_role is None


# ---------------------------------------------------------------------------
# ValidationReport — computed properties
# ---------------------------------------------------------------------------


class TestValidationReportErrorCount:
    def test_error_count_zero_when_no_findings(self) -> None:
        """error_count is 0 for a report with no findings."""
        report = _report(())
        assert report.error_count == 0

    def test_error_count_counts_only_errors(self) -> None:
        """error_count returns the number of ERROR findings only."""
        findings = (
            _finding(severity=ValidationSeverity.ERROR),
            _finding(severity=ValidationSeverity.ERROR),
            _finding(severity=ValidationSeverity.WARNING),
        )
        report = _report(findings)
        assert report.error_count == 2

    def test_warning_count_counts_only_warnings(self) -> None:
        """warning_count returns the number of WARNING findings only."""
        findings = (
            _finding(severity=ValidationSeverity.ERROR),
            _finding(severity=ValidationSeverity.WARNING),
            _finding(severity=ValidationSeverity.WARNING),
        )
        report = _report(findings)
        assert report.warning_count == 2

    def test_warning_count_zero_when_no_warnings(self) -> None:
        """warning_count is 0 when there are no WARNING findings."""
        findings = (
            _finding(severity=ValidationSeverity.ERROR),
        )
        report = _report(findings)
        assert report.warning_count == 0


class TestValidationReportPassed:
    def test_passed_true_when_no_errors(self) -> None:
        """passed is True when error_count is 0."""
        report = _report(())
        assert report.passed is True

    def test_passed_false_when_has_errors(self) -> None:
        """passed is False when there is at least one ERROR finding."""
        findings = (_finding(severity=ValidationSeverity.ERROR),)
        report = _report(findings)
        assert report.passed is False

    def test_passed_true_with_only_warnings(self) -> None:
        """passed is True when findings contain only warnings (no errors)."""
        findings = (_finding(severity=ValidationSeverity.WARNING),)
        report = _report(findings)
        assert report.passed is True

    def test_pass_count_counts_only_pass_rows(self) -> None:
        findings = (
            _finding(rule_id="formula:pass-1", severity=None, source="formula"),
            _finding(rule_id="formula:fail-1", severity=ValidationSeverity.ERROR, source="formula"),
        )
        findings = (
            dataclasses.replace(findings[0], status=ValidationStatus.PASS),
            findings[1],
        )
        report = _report(findings)
        assert report.pass_count == 1

    def test_not_evaluated_count_counts_only_not_evaluated_rows(self) -> None:
        findings = (
            dataclasses.replace(
                _finding(rule_id="formula:not-evaluated", severity=None, source="formula"),
                status=ValidationStatus.NOT_EVALUATED,
            ),
            dataclasses.replace(
                _finding(rule_id="formula:pass", severity=None, source="formula"),
                status=ValidationStatus.PASS,
            ),
            _finding(rule_id="formula:fail", severity=ValidationSeverity.ERROR, source="formula"),
        )
        report = _report(findings)
        assert report.not_evaluated_count == 1

    def test_total_elapsed_seconds_sums_stage_timings(self) -> None:
        report = ValidationReport(
            instance_path="/some/instance.xbrl",
            taxonomy_name="ExampleTax",
            taxonomy_version="2024",
            run_timestamp=datetime(2024, 6, 1, 12, 0, 0),
            findings=(),
            formula_linkbase_available=True,
            stage_timings=(
                StageTiming("structural", 0.25),
                StageTiming("formula", 1.75),
            ),
        )

        assert report.total_elapsed_seconds == pytest.approx(2.0)


class TestValidationReportFindingsForTable:
    def test_findings_for_table_returns_matching(self) -> None:
        """findings_for_table returns only findings for the specified table_id."""
        f1 = _finding(table_id="T01")
        f2 = _finding(table_id="T02")
        f3 = _finding(table_id="T01")
        report = _report((f1, f2, f3))
        result = report.findings_for_table("T01")
        assert len(result) == 2
        assert all(f.table_id == "T01" for f in result)

    def test_findings_for_table_no_match_returns_empty(self) -> None:
        """findings_for_table returns an empty tuple when no findings match the table_id."""
        f1 = _finding(table_id="T01")
        report = _report((f1,))
        result = report.findings_for_table("T99")
        assert result == ()

    def test_findings_for_table_with_none_table_id(self) -> None:
        """findings_for_table('None') does not return findings with table_id=None."""
        f1 = _finding(table_id=None)
        f2 = _finding(table_id="T01")
        report = _report((f1, f2))
        # Findings with table_id=None should only appear when queried by None
        result = report.findings_for_table(None)  # type: ignore[arg-type]
        assert f1 in result
        assert f2 not in result


class TestValidationReportFindingsBySeverity:
    def test_findings_by_severity_error(self) -> None:
        """findings_by_severity(ERROR) returns only ERROR findings."""
        f_err = _finding(severity=ValidationSeverity.ERROR)
        f_warn = _finding(severity=ValidationSeverity.WARNING)
        report = _report((f_err, f_warn))
        result = report.findings_by_severity(ValidationSeverity.ERROR)
        assert f_err in result
        assert f_warn not in result

    def test_findings_by_severity_warning(self) -> None:
        """findings_by_severity(WARNING) returns only WARNING findings."""
        f_err = _finding(severity=ValidationSeverity.ERROR)
        f_warn = _finding(severity=ValidationSeverity.WARNING)
        report = _report((f_err, f_warn))
        result = report.findings_by_severity(ValidationSeverity.WARNING)
        assert f_warn in result
        assert f_err not in result

    def test_findings_by_severity_empty(self) -> None:
        """findings_by_severity returns empty tuple when no findings match."""
        report = _report(())
        result = report.findings_by_severity(ValidationSeverity.ERROR)
        assert result == ()


# ---------------------------------------------------------------------------
# ValidationReport — immutability
# ---------------------------------------------------------------------------


class TestValidationReportImmutability:
    def test_report_is_frozen(self) -> None:
        """ValidationReport is a frozen dataclass — attribute assignment must raise."""
        report = _report()
        with pytest.raises((dataclasses.FrozenInstanceError, AttributeError)):
            report.instance_path = "other"  # type: ignore[misc]


# ---------------------------------------------------------------------------
# ValidationFilterProxy — requires PySide6, skip gracefully if unavailable
# ---------------------------------------------------------------------------

PySide6 = pytest.importorskip(
    "PySide6",
    reason="PySide6 not available — ValidationFilterProxy tests skipped",
)


class TestValidationFilterProxy:
    """Tests for ValidationFilterProxy that need a running Qt application."""

    @pytest.fixture(autouse=True)
    def _qt_app(self):
        """Ensure a QApplication instance exists for the test session."""
        import sys

        from PySide6.QtWidgets import QApplication

        app = QApplication.instance() or QApplication(sys.argv)
        yield app

    def _make_model_and_proxy(self, findings: tuple[ValidationFinding, ...]):
        """Create a ValidationResultsModel + ValidationFilterProxy pair."""
        from bde_xbrl_editor.ui.widgets.validation_results_model import (
            ValidationFilterProxy,
            ValidationResultsModel,
        )

        source_model = ValidationResultsModel()
        source_model.populate(findings)
        proxy = ValidationFilterProxy()
        proxy.setSourceModel(source_model)
        return source_model, proxy

    def test_severity_filter_shows_only_errors(self) -> None:
        """After setting a severity filter, only ERROR rows are visible."""
        findings = (
            _finding("r1", ValidationSeverity.ERROR),
            _finding("r2", ValidationSeverity.WARNING),
            _finding("r3", ValidationSeverity.ERROR),
        )
        source, proxy = self._make_model_and_proxy(findings)
        proxy.set_severity_filter(ValidationSeverity.ERROR)
        visible = proxy.rowCount()
        assert visible == 2

    def test_severity_filter_shows_only_warnings(self) -> None:
        """After setting a warning severity filter, only WARNING rows are visible."""
        findings = (
            _finding("r1", ValidationSeverity.ERROR),
            _finding("r2", ValidationSeverity.WARNING),
        )
        source, proxy = self._make_model_and_proxy(findings)
        proxy.set_severity_filter(ValidationSeverity.WARNING)
        assert proxy.rowCount() == 1

    def test_table_filter(self) -> None:
        """After setting a table filter, only rows for that table_id are visible."""
        findings = (
            _finding("r1", table_id="T01"),
            _finding("r2", table_id="T02"),
            _finding("r3", table_id="T01"),
        )
        source, proxy = self._make_model_and_proxy(findings)
        proxy.set_table_filter("T01")
        assert proxy.rowCount() == 2

    def test_combined_severity_and_table_filter(self) -> None:
        """Combining severity and table filters applies both constraints (AND)."""
        findings = (
            _finding("r1", ValidationSeverity.ERROR, table_id="T01"),
            _finding("r2", ValidationSeverity.WARNING, table_id="T01"),
            _finding("r3", ValidationSeverity.ERROR, table_id="T02"),
        )
        source, proxy = self._make_model_and_proxy(findings)
        proxy.set_severity_filter(ValidationSeverity.ERROR)
        proxy.set_table_filter("T01")
        assert proxy.rowCount() == 1

    def test_clear_filters_restores_all_rows(self) -> None:
        """Calling clear_filters() after filtering restores all rows."""
        findings = (
            _finding("r1", ValidationSeverity.ERROR),
            _finding("r2", ValidationSeverity.WARNING),
        )
        source, proxy = self._make_model_and_proxy(findings)
        proxy.set_severity_filter(ValidationSeverity.ERROR)
        proxy.clear_filters()
        assert proxy.rowCount() == 2

    def test_status_filter_shows_only_not_evaluated(self) -> None:
        findings = (
            _finding("r1", ValidationSeverity.ERROR),
            dataclasses.replace(
                _finding("r2", severity=None, source="formula"),
                status=ValidationStatus.NOT_EVALUATED,
            ),
        )
        source, proxy = self._make_model_and_proxy(findings)
        proxy.set_severity_filter(ValidationStatus.NOT_EVALUATED)
        assert proxy.rowCount() == 1

    def test_table_column_reuses_compact_table_identity_without_duplication(self) -> None:
        """Table column should reuse the compact table identity string as-is."""
        from bde_xbrl_editor.ui.widgets.validation_results_model import ValidationResultsModel

        finding = ValidationFinding(
            rule_id="r1",
            severity=ValidationSeverity.ERROR,
            message="Test finding",
            source="formula",
            table_id="es_tFI_40-1",
            table_label="0010  |  es_tFI_40-1",
        )
        model = ValidationResultsModel()
        model.populate((finding,))

        assert model.item(0, 2).text() == "0010  |  es_tFI_40-1"

    def test_append_findings_adds_rows_without_replacing_existing_ones(self) -> None:
        """append_findings keeps previously streamed results visible."""
        from bde_xbrl_editor.ui.widgets.validation_results_model import ValidationResultsModel

        initial = _finding("r1", ValidationSeverity.ERROR, table_id="T01")
        streamed = _finding("r2", ValidationSeverity.WARNING, table_id="T02")

        model = ValidationResultsModel()
        model.populate((initial,))
        model.append_findings((streamed,))

        assert model.rowCount() == 2
        assert model.item(0, 1).text() == "r1"
        assert model.item(1, 1).text() == "r2"
