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
                    f"[{finding.severity.value.upper()}] {finding.rule_id}: {finding.message}"
                )
                if finding.table_label or finding.table_id:
                    lines.append(f"  Table   : {finding.table_label or finding.table_id}")
                if finding.concept_qname:
                    lines.append(f"  Concept : {finding.concept_qname}")
                if finding.context_ref:
                    lines.append(f"  Context : {finding.context_ref}")
                if finding.constraint_type:
                    lines.append(f"  Constraint: {finding.constraint_type}")
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
                "error_count": report.error_count,
                "warning_count": report.warning_count,
            },
            "findings": [
                {
                    "rule_id": f.rule_id,
                    "severity": f.severity.value,
                    "source": f.source,
                    "message": f.message,
                    "table_id": f.table_id,
                    "table_label": f.table_label,
                    "concept": str(f.concept_qname) if f.concept_qname else None,
                    "context_ref": f.context_ref,
                    "constraint_type": f.constraint_type,
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
