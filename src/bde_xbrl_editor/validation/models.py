"""Validation domain models — immutable dataclasses for validation results."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import StrEnum
from typing import Literal

from bde_xbrl_editor.taxonomy.models import QName


class ValidationSeverity(StrEnum):
    ERROR = "error"
    WARNING = "warning"


@dataclass(frozen=True)
class ValidationFinding:
    """A single identified issue from a validation run. Immutable."""

    rule_id: str
    severity: ValidationSeverity
    message: str
    source: Literal["structural", "formula", "dimensional"]
    table_id: str | None = None
    table_label: str | None = None
    concept_qname: QName | None = None
    context_ref: str | None = None
    hypercube_qname: QName | None = None
    dimension_qname: QName | None = None
    constraint_type: str | None = None
    formula_assertion_type: str | None = None
    formula_expression: str | None = None
    formula_operands_text: str | None = None
    formula_precondition: str | None = None


@dataclass(frozen=True)
class ValidationReport:
    """Complete output of one validation run. Immutable."""

    instance_path: str
    taxonomy_name: str
    taxonomy_version: str
    run_timestamp: datetime
    findings: tuple[ValidationFinding, ...]
    formula_linkbase_available: bool
    structural_checks_run: bool = True

    @property
    def error_count(self) -> int:
        return sum(1 for f in self.findings if f.severity == ValidationSeverity.ERROR)

    @property
    def warning_count(self) -> int:
        return sum(1 for f in self.findings if f.severity == ValidationSeverity.WARNING)

    @property
    def passed(self) -> bool:
        return self.error_count == 0

    def findings_for_table(self, table_id: str) -> tuple[ValidationFinding, ...]:
        return tuple(f for f in self.findings if f.table_id == table_id)

    def findings_by_severity(self, sev: ValidationSeverity) -> tuple[ValidationFinding, ...]:
        return tuple(f for f in self.findings if f.severity == sev)


@dataclass
class ValidationRun:
    """Mutable in-progress state held only inside ValidationWorker."""

    findings: list[ValidationFinding] = field(default_factory=list)
    total_assertions: int = 0
    evaluated_assertions: int = 0
