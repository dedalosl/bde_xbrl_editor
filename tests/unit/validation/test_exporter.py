"""Unit tests for ValidationReportExporter (validation/exporter.py)."""
from __future__ import annotations

import json
import stat
import sys
from datetime import datetime
from pathlib import Path

import pytest

from bde_xbrl_editor.validation.errors import ExportPermissionError
from bde_xbrl_editor.validation.exporter import ValidationReportExporter
from bde_xbrl_editor.validation.models import (
    ValidationFinding,
    ValidationReport,
    ValidationSeverity,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _finding(
    rule_id: str = "structural:missing-schemaref",
    severity: ValidationSeverity = ValidationSeverity.ERROR,
    message: str = "Test message",
    source: str = "structural",
    table_id: str | None = None,
    table_label: str | None = None,
    context_ref: str | None = None,
    constraint_type: str | None = None,
) -> ValidationFinding:
    return ValidationFinding(
        rule_id=rule_id,
        severity=severity,
        message=message,
        source=source,  # type: ignore[arg-type]
        table_id=table_id,
        table_label=table_label,
        context_ref=context_ref,
        constraint_type=constraint_type,
    )


_TIMESTAMP = datetime(2024, 6, 15, 10, 30, 0)


def _report(
    findings: tuple[ValidationFinding, ...] = (),
    passed_by_design: bool = True,
) -> ValidationReport:
    return ValidationReport(
        instance_path="/reports/instance.xbrl",
        taxonomy_name="BDE-COREP",
        taxonomy_version="3.4",
        run_timestamp=_TIMESTAMP,
        findings=findings,
        formula_linkbase_available=True,
    )


# ---------------------------------------------------------------------------
# export_text
# ---------------------------------------------------------------------------


class TestExportText:
    def test_creates_file(self, tmp_path: Path) -> None:
        """export_text creates a file at the specified path."""
        out = tmp_path / "report.txt"
        ValidationReportExporter().export_text(_report(), out)
        assert out.exists()

    def test_summary_header_present(self, tmp_path: Path) -> None:
        """The exported text file contains the summary header lines."""
        report = _report()
        out = tmp_path / "report.txt"
        ValidationReportExporter().export_text(report, out)
        content = out.read_text(encoding="utf-8")
        assert "XBRL Validation Report" in content
        assert "BDE-COREP 3.4" in content
        assert _TIMESTAMP.isoformat() in content

    def test_passed_label_in_header(self, tmp_path: Path) -> None:
        """The header shows PASSED when there are no error findings."""
        out = tmp_path / "report.txt"
        ValidationReportExporter().export_text(_report(findings=()), out)
        assert "PASSED" in out.read_text(encoding="utf-8")

    def test_failed_label_in_header(self, tmp_path: Path) -> None:
        """The header shows FAILED when there is at least one error finding."""
        findings = (_finding(severity=ValidationSeverity.ERROR),)
        out = tmp_path / "report.txt"
        ValidationReportExporter().export_text(_report(findings=findings), out)
        assert "FAILED" in out.read_text(encoding="utf-8")

    def test_each_finding_appears(self, tmp_path: Path) -> None:
        """Each finding's rule_id and message appear in the exported file."""
        f1 = _finding(rule_id="structural:missing-schemaref", message="no schema ref")
        f2 = _finding(rule_id="dimensional.invalid_member", message="bad member")
        out = tmp_path / "report.txt"
        ValidationReportExporter().export_text(_report(findings=(f1, f2)), out)
        content = out.read_text(encoding="utf-8")
        assert "structural:missing-schemaref" in content
        assert "no schema ref" in content
        assert "dimensional.invalid_member" in content
        assert "bad member" in content

    def test_no_findings_section_message(self, tmp_path: Path) -> None:
        """When there are no findings, a 'no findings' message is written."""
        out = tmp_path / "report.txt"
        ValidationReportExporter().export_text(_report(findings=()), out)
        content = out.read_text(encoding="utf-8")
        assert "No findings" in content

    def test_finding_with_context_ref_appears(self, tmp_path: Path) -> None:
        """A finding with a context_ref includes it in the text output."""
        f = _finding(context_ref="ctx_001")
        out = tmp_path / "report.txt"
        ValidationReportExporter().export_text(_report(findings=(f,)), out)
        assert "ctx_001" in out.read_text(encoding="utf-8")

    def test_finding_with_table_label_appears(self, tmp_path: Path) -> None:
        """A finding with a table_label includes it in the text output."""
        f = _finding(table_label="Table C 01.00")
        out = tmp_path / "report.txt"
        ValidationReportExporter().export_text(_report(findings=(f,)), out)
        assert "Table C 01.00" in out.read_text(encoding="utf-8")

    def test_finding_with_constraint_type_appears(self, tmp_path: Path) -> None:
        """A finding with a constraint_type includes it in the text output."""
        f = _finding(constraint_type="UNDECLARED_DIMENSION")
        out = tmp_path / "report.txt"
        ValidationReportExporter().export_text(_report(findings=(f,)), out)
        assert "UNDECLARED_DIMENSION" in out.read_text(encoding="utf-8")

    def test_formula_detail_fields_appear(self, tmp_path: Path) -> None:
        """Formula findings export their richer rule details."""
        f = ValidationFinding(
            rule_id="formula:test",
            severity=ValidationSeverity.ERROR,
            message="Formula failed",
            source="formula",
            formula_assertion_type="Value Assertion",
            formula_expression="$a > 0",
            formula_operands_text="$a\n  concept: ex:Amount",
            formula_precondition="$a",
        )
        out = tmp_path / "report.txt"
        ValidationReportExporter().export_text(_report(findings=(f,)), out)
        content = out.read_text(encoding="utf-8")
        assert "Formula Type: Value Assertion" in content
        assert "$a > 0" in content
        assert "concept: ex:Amount" in content
        assert "Precondition: $a" in content

    @pytest.mark.skipif(sys.platform == "win32", reason="chmod read-only not reliable on Windows")
    def test_permission_error_on_readonly_path(self, tmp_path: Path) -> None:
        """export_text raises ExportPermissionError when the path is not writable."""
        readonly_dir = tmp_path / "ro"
        readonly_dir.mkdir()
        readonly_dir.chmod(stat.S_IREAD | stat.S_IEXEC)
        out = readonly_dir / "report.txt"
        try:
            with pytest.raises(ExportPermissionError):
                ValidationReportExporter().export_text(_report(), out)
        finally:
            readonly_dir.chmod(stat.S_IRWXU)  # restore so tmp_path cleanup works


# ---------------------------------------------------------------------------
# export_json
# ---------------------------------------------------------------------------


class TestExportJson:
    def test_creates_file(self, tmp_path: Path) -> None:
        """export_json creates a file at the specified path."""
        out = tmp_path / "report.json"
        ValidationReportExporter().export_json(_report(), out)
        assert out.exists()

    def test_valid_json(self, tmp_path: Path) -> None:
        """The exported JSON file contains valid JSON."""
        out = tmp_path / "report.json"
        ValidationReportExporter().export_json(_report(), out)
        data = json.loads(out.read_text(encoding="utf-8"))
        assert isinstance(data, dict)

    def test_json_summary_keys_present(self, tmp_path: Path) -> None:
        """The JSON root has a 'summary' key with expected sub-keys."""
        out = tmp_path / "report.json"
        ValidationReportExporter().export_json(_report(), out)
        data = json.loads(out.read_text(encoding="utf-8"))
        assert "summary" in data
        summary = data["summary"]
        assert "instance" in summary
        assert "taxonomy" in summary
        assert "run_timestamp" in summary
        assert "passed" in summary
        assert "error_count" in summary
        assert "warning_count" in summary

    def test_json_findings_key_present(self, tmp_path: Path) -> None:
        """The JSON root has a 'findings' key that is a list."""
        out = tmp_path / "report.json"
        ValidationReportExporter().export_json(_report(), out)
        data = json.loads(out.read_text(encoding="utf-8"))
        assert "findings" in data
        assert isinstance(data["findings"], list)

    def test_json_no_findings_empty_list(self, tmp_path: Path) -> None:
        """When there are no findings, the findings list is empty."""
        out = tmp_path / "report.json"
        ValidationReportExporter().export_json(_report(findings=()), out)
        data = json.loads(out.read_text(encoding="utf-8"))
        assert data["findings"] == []

    def test_json_finding_fields(self, tmp_path: Path) -> None:
        """Each finding in the JSON output contains the expected schema fields."""
        f = _finding(
            rule_id="structural:unresolved-context-ref",
            severity=ValidationSeverity.ERROR,
            message="ctx missing",
            source="structural",
            table_id="T01",
            context_ref="ctx1",
            constraint_type=None,
        )
        out = tmp_path / "report.json"
        ValidationReportExporter().export_json(_report(findings=(f,)), out)
        data = json.loads(out.read_text(encoding="utf-8"))
        assert len(data["findings"]) == 1
        jf = data["findings"][0]
        assert jf["rule_id"] == "structural:unresolved-context-ref"
        assert jf["severity"] == "error"
        assert jf["source"] == "structural"
        assert jf["message"] == "ctx missing"
        assert jf["formula_assertion_type"] is None
        assert jf["formula_expression"] is None
        assert jf["formula_operands_text"] is None
        assert jf["formula_precondition"] is None

    def test_json_formula_detail_fields(self, tmp_path: Path) -> None:
        """Formula-specific detail fields are preserved in JSON export."""
        f = ValidationFinding(
            rule_id="formula:detail",
            severity=ValidationSeverity.ERROR,
            message="Formula failed",
            source="formula",
            formula_assertion_type="Consistency Assertion",
            formula_expression="$a = $b",
            formula_operands_text="$a\n\n$b",
            formula_precondition="$a",
        )
        out = tmp_path / "report.json"
        ValidationReportExporter().export_json(_report(findings=(f,)), out)
        data = json.loads(out.read_text(encoding="utf-8"))
        jf = data["findings"][0]
        assert jf["formula_assertion_type"] == "Consistency Assertion"
        assert jf["formula_expression"] == "$a = $b"
        assert jf["formula_operands_text"] == "$a\n\n$b"
        assert jf["formula_precondition"] == "$a"

    def test_json_passed_flag_matches_report(self, tmp_path: Path) -> None:
        """The 'passed' field in JSON summary matches report.passed."""
        findings_err = (_finding(severity=ValidationSeverity.ERROR),)
        out_fail = tmp_path / "fail.json"
        out_pass = tmp_path / "pass.json"
        ValidationReportExporter().export_json(_report(findings=findings_err), out_fail)
        ValidationReportExporter().export_json(_report(findings=()), out_pass)
        assert json.loads(out_fail.read_text())["summary"]["passed"] is False
        assert json.loads(out_pass.read_text())["summary"]["passed"] is True

    def test_json_counts_match(self, tmp_path: Path) -> None:
        """error_count and warning_count in JSON match the actual finding counts."""
        findings = (
            _finding(severity=ValidationSeverity.ERROR),
            _finding(severity=ValidationSeverity.ERROR),
            _finding(severity=ValidationSeverity.WARNING),
        )
        out = tmp_path / "report.json"
        ValidationReportExporter().export_json(_report(findings=findings), out)
        data = json.loads(out.read_text(encoding="utf-8"))
        assert data["summary"]["error_count"] == 2
        assert data["summary"]["warning_count"] == 1

    @pytest.mark.skipif(sys.platform == "win32", reason="chmod read-only not reliable on Windows")
    def test_permission_error_on_readonly_path(self, tmp_path: Path) -> None:
        """export_json raises ExportPermissionError when the path is not writable."""
        readonly_dir = tmp_path / "ro2"
        readonly_dir.mkdir()
        readonly_dir.chmod(stat.S_IREAD | stat.S_IEXEC)
        out = readonly_dir / "report.json"
        try:
            with pytest.raises(ExportPermissionError):
                ValidationReportExporter().export_json(_report(), out)
        finally:
            readonly_dir.chmod(stat.S_IRWXU)
