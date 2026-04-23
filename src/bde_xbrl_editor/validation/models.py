"""Validation domain models — immutable dataclasses for validation results."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import StrEnum
from typing import Literal

from bde_xbrl_editor.performance import StageTiming
from bde_xbrl_editor.taxonomy.models import QName


class ValidationSeverity(StrEnum):
    ERROR = "error"
    WARNING = "warning"


class ValidationStatus(StrEnum):
    PASS = "pass"
    FAIL = "fail"


@dataclass(frozen=True)
class ValidationFinding:
    """A single identified issue from a validation run. Immutable."""

    rule_id: str
    severity: ValidationSeverity | None
    message: str
    source: Literal["structural", "formula", "dimensional", "calculation"]
    status: ValidationStatus = ValidationStatus.FAIL
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
    rule_label: str | None = None
    rule_label_role: str | None = None
    rule_message: str | None = None
    evaluated_rule_message: str | None = None
    rule_message_role: str | None = None


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
    stage_timings: tuple[StageTiming, ...] = field(default_factory=tuple)

    @property
    def error_count(self) -> int:
        return sum(1 for f in self.findings if f.severity == ValidationSeverity.ERROR)

    @property
    def warning_count(self) -> int:
        return sum(1 for f in self.findings if f.severity == ValidationSeverity.WARNING)

    @property
    def passed(self) -> bool:
        return self.error_count == 0

    @property
    def pass_count(self) -> int:
        return sum(1 for f in self.findings if f.status == ValidationStatus.PASS)

    @property
    def total_elapsed_seconds(self) -> float:
        return sum(stage.elapsed_seconds for stage in self.stage_timings)

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
