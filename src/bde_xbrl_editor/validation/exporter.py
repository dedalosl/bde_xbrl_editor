"""ValidationReportExporter — write validation reports to text or JSON files."""

from __future__ import annotations

import json
from pathlib import Path

from bde_xbrl_editor.validation.errors import ExportPermissionError
from bde_xbrl_editor.validation.models import ValidationReport


class ValidationReportExporter:
    """Export a ValidationReport to plain text or JSON."""

    def export_text(self, report: ValidationReport, path: Path) -> None:
        """Write a human-readable plain text report.

        Raises ExportPermissionError if path is not writable.
        """
        lines: list[str] = [
            "=" * 72,
            "XBRL Validation Report",
            "=" * 72,
            f"Instance  : {report.instance_path}",
            f"Taxonomy  : {report.taxonomy_name} {report.taxonomy_version}",
            f"Timestamp : {report.run_timestamp.isoformat()}",
            f"Result    : {'PASSED' if report.passed else 'FAILED'}",
            f"Passed    : {report.pass_count}",
            f"Not Eval. : {report.not_evaluated_count}",
            f"Errors    : {report.error_count}",
            f"Warnings  : {report.warning_count}",
            f"Formula   : {'available' if report.formula_linkbase_available else 'not available'}",
            "",
        ]

        if report.findings:
            lines.append("Findings:")
            lines.append("-" * 72)
            for finding in report.findings:
                lines.append(
                    f"[{finding.status.value.upper() if finding.status else 'FAIL'}"
                    f"{'/' + finding.severity.value.upper() if finding.severity else ''}] "
                    f"{finding.rule_id}: {finding.message}"
                )
                if finding.rule_label:
                    lines.append(f"  Definition : {finding.rule_label}")
                if finding.rule_message:
                    lines.append(f"  Official Message : {finding.rule_message}")
                if finding.evaluated_rule_message:
                    lines.append(f"  Evaluated Message : {finding.evaluated_rule_message}")
                if finding.table_label or finding.table_id:
                    lines.append(f"  Table   : {finding.table_label or finding.table_id}")
                if finding.concept_qname:
                    lines.append(f"  Concept : {finding.concept_qname}")
                if finding.context_ref:
                    lines.append(f"  Context : {finding.context_ref}")
                if finding.constraint_type:
                    lines.append(f"  Constraint: {finding.constraint_type}")
                if finding.formula_assertion_type:
                    lines.append(f"  Formula Type: {finding.formula_assertion_type}")
                if finding.formula_expression:
                    lines.append("  Formula / Test:")
                    for detail_line in finding.formula_expression.splitlines():
                        lines.append(f"    {detail_line}")
                if finding.formula_operands_text:
                    lines.append("  Operands:")
                    for detail_line in finding.formula_operands_text.splitlines():
                        lines.append(f"    {detail_line}")
                if finding.formula_precondition and finding.formula_precondition != "—":
                    lines.append(f"  Precondition: {finding.formula_precondition}")
                lines.append("")
        else:
            lines.append("No findings — instance passes all validation checks.")

        content = "\n".join(lines)
        try:
            path.write_text(content, encoding="utf-8")
        except PermissionError as exc:
            raise ExportPermissionError(f"Cannot write to '{path}': {exc}") from exc
        except OSError as exc:
            raise ExportPermissionError(f"Cannot write to '{path}': {exc}") from exc

    def export_json(self, report: ValidationReport, path: Path) -> None:
        """Write a JSON report following the documented schema.

        Raises ExportPermissionError if path is not writable.
        """
        data = {
            "summary": {
                "instance": report.instance_path,
                "taxonomy": f"{report.taxonomy_name} {report.taxonomy_version}",
                "run_timestamp": report.run_timestamp.isoformat(),
                "passed": report.passed,
                "pass_count": report.pass_count,
                "not_evaluated_count": report.not_evaluated_count,
                "error_count": report.error_count,
                "warning_count": report.warning_count,
            },
            "findings": [
                {
                    "rule_id": f.rule_id,
                    "severity": f.severity.value if f.severity is not None else None,
                    "status": f.status.value,
                    "source": f.source,
                    "message": f.message,
                    "table_id": f.table_id,
                    "table_label": f.table_label,
                    "concept": str(f.concept_qname) if f.concept_qname else None,
                    "context_ref": f.context_ref,
                    "constraint_type": f.constraint_type,
                    "formula_assertion_type": f.formula_assertion_type,
                    "formula_expression": f.formula_expression,
                    "formula_operands_text": f.formula_operands_text,
                    "rule_label": f.rule_label,
                    "rule_label_role": f.rule_label_role,
                    "rule_message": f.rule_message,
                    "evaluated_rule_message": f.evaluated_rule_message,
                    "rule_message_role": f.rule_message_role,
                    "formula_precondition": (
                        f.formula_precondition
                        if f.formula_precondition != "—"
                        else None
                    ),
                }
                for f in report.findings
            ],
        }
        content = json.dumps(data, indent=2, ensure_ascii=False)
        try:
            path.write_text(content, encoding="utf-8")
        except PermissionError as exc:
            raise ExportPermissionError(f"Cannot write to '{path}': {exc}") from exc
        except OSError as exc:
            raise ExportPermissionError(f"Cannot write to '{path}': {exc}") from exc
