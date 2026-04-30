"""InstanceValidator — orchestrates the full XBRL validation pipeline.

Runs structural checks → calculation (summation-item) checks → dimensional
checks → formula assertions in sequence, assembling the results into an
immutable ValidationReport. Never raises.
"""

from __future__ import annotations

import contextlib
import threading
import time
from collections.abc import Callable
from datetime import datetime

from bde_xbrl_editor.instance.models import XbrlInstance
from bde_xbrl_editor.performance import StageTiming
from bde_xbrl_editor.taxonomy.models import TaxonomyStructure
from bde_xbrl_editor.validation.calculation import CalculationConsistencyValidator
from bde_xbrl_editor.validation.dimensional import DimensionalConstraintValidator
from bde_xbrl_editor.validation.formula.evaluator import FormulaEvaluator
from bde_xbrl_editor.validation.models import (
    ValidationFinding,
    ValidationReport,
    ValidationSeverity,
)
from bde_xbrl_editor.validation.relationships import RelationshipSetValidator
from bde_xbrl_editor.validation.structural import StructuralConformanceValidator

ProgressCallback = Callable[[int, int, str], None]
FindingCallback = Callable[[tuple[ValidationFinding, ...]], None]


class InstanceValidator:
    """Runs the full validation pipeline against a single XbrlInstance.

    Pure Python — no PySide6 dependency.
    """

    def __init__(
        self,
        taxonomy: TaxonomyStructure,
        progress_callback: ProgressCallback | None = None,
        finding_callback: FindingCallback | None = None,
        cancel_event: threading.Event | None = None,
    ) -> None:
        self._taxonomy = taxonomy
        self._progress_callback = progress_callback
        self._finding_callback = finding_callback
        self._cancel_event = cancel_event

    def validate_sync(self, instance: XbrlInstance) -> ValidationReport:
        """Run structural + dimensional + formula validation synchronously.

        Always returns a ValidationReport — never raises. Exceptions from
        individual validators are caught and turned into error findings.
        """
        findings: list[ValidationFinding] = []
        stage_timings: list[StageTiming] = []

        # --- 1. Structural checks -------------------------------------------
        if not (self._cancel_event and self._cancel_event.is_set()):
            stage_started_at = time.perf_counter()
            if self._progress_callback:
                with contextlib.suppress(Exception):
                    self._progress_callback(0, 4, "Running structural checks…")
            try:
                sv = StructuralConformanceValidator()
                stage_findings = tuple(sv.validate(instance, self._taxonomy))
                findings.extend(stage_findings)
                self._publish_findings(stage_findings)
            except Exception as exc:  # noqa: BLE001
                stage_findings = (ValidationFinding(
                    rule_id="internal:structural-error",
                    severity=ValidationSeverity.ERROR,
                    message=f"Structural validator failed unexpectedly: {exc}",
                    source="structural",
                ),)
                findings.extend(stage_findings)
                self._publish_findings(stage_findings)
            stage_timings.append(
                StageTiming("structural", time.perf_counter() - stage_started_at)
            )

        # --- 1b. Taxonomy relationship-set checks ---------------------------
        if not (self._cancel_event and self._cancel_event.is_set()):
            try:
                rv = RelationshipSetValidator()
                stage_findings = tuple(rv.validate_taxonomy(self._taxonomy))
                findings.extend(stage_findings)
                self._publish_findings(stage_findings)
            except Exception as exc:  # noqa: BLE001
                stage_findings = (ValidationFinding(
                    rule_id="internal:relationship-error",
                    severity=ValidationSeverity.ERROR,
                    message=f"Relationship-set validator failed unexpectedly: {exc}",
                    source="relationships",
                ),)
                findings.extend(stage_findings)
                self._publish_findings(stage_findings)

        # --- 2. Calculation (summation-item) checks -------------------------
        if not (self._cancel_event and self._cancel_event.is_set()):
            stage_started_at = time.perf_counter()
            if self._progress_callback:
                with contextlib.suppress(Exception):
                    self._progress_callback(1, 4, "Running calculation checks…")
            try:
                cv = CalculationConsistencyValidator()
                stage_findings = tuple(cv.validate(instance, self._taxonomy))
                findings.extend(stage_findings)
                self._publish_findings(stage_findings)
            except Exception as exc:  # noqa: BLE001
                stage_findings = (ValidationFinding(
                    rule_id="internal:calculation-error",
                    severity=ValidationSeverity.ERROR,
                    message=f"Calculation validator failed unexpectedly: {exc}",
                    source="calculation",
                ),)
                findings.extend(stage_findings)
                self._publish_findings(stage_findings)
            stage_timings.append(
                StageTiming("calculation", time.perf_counter() - stage_started_at)
            )

        # --- 3. Dimensional checks -------------------------------------------
        if not (self._cancel_event and self._cancel_event.is_set()):
            stage_started_at = time.perf_counter()
            if self._progress_callback:
                with contextlib.suppress(Exception):
                    self._progress_callback(2, 4, "Running dimensional checks…")
            try:
                dv = DimensionalConstraintValidator(self._taxonomy)
                stage_findings = tuple(dv.validate(instance))
                findings.extend(stage_findings)
                self._publish_findings(stage_findings)
            except Exception as exc:  # noqa: BLE001
                stage_findings = (ValidationFinding(
                    rule_id="internal:dimensional-error",
                    severity=ValidationSeverity.ERROR,
                    message=f"Dimensional validator failed unexpectedly: {exc}",
                    source="dimensional",
                ),)
                findings.extend(stage_findings)
                self._publish_findings(stage_findings)
            stage_timings.append(
                StageTiming("dimensional", time.perf_counter() - stage_started_at)
            )

        # --- 4. Formula assertions ------------------------------------------
        formula_available = bool(
            self._taxonomy.formula_assertion_set.assertions
        )
        if not (self._cancel_event and self._cancel_event.is_set()):
            stage_started_at = time.perf_counter()
            if self._progress_callback:
                with contextlib.suppress(Exception):
                    self._progress_callback(3, 4, "Evaluating formula assertions…")
            try:
                fe = FormulaEvaluator(
                    taxonomy=self._taxonomy,
                    progress_callback=self._progress_callback,
                    finding_callback=self._publish_findings,
                    cancel_event=self._cancel_event,
                )
                findings.extend(fe.evaluate(instance))
            except Exception as exc:  # noqa: BLE001
                stage_findings = (ValidationFinding(
                    rule_id="internal:formula-error",
                    severity=ValidationSeverity.ERROR,
                    message=f"Formula evaluator failed unexpectedly: {exc}",
                    source="formula",
                ),)
                findings.extend(stage_findings)
                self._publish_findings(stage_findings)
            stage_timings.append(
                StageTiming("formula", time.perf_counter() - stage_started_at)
            )

        if self._progress_callback:
            with contextlib.suppress(Exception):
                elapsed_total = sum(stage.elapsed_seconds for stage in stage_timings)
                self._progress_callback(4, 4, f"Validation complete ({elapsed_total:.2f}s)")

        meta = self._taxonomy.metadata
        return ValidationReport(
            instance_path=str(instance.source_path or ""),
            taxonomy_name=meta.name,
            taxonomy_version=meta.version,
            run_timestamp=datetime.now(),
            findings=tuple(findings),
            formula_linkbase_available=formula_available or (
                self._taxonomy.formula_linkbase_path is not None
            ),
            structural_checks_run=True,
            stage_timings=tuple(stage_timings),
        )

    def _publish_findings(self, findings: tuple[ValidationFinding, ...]) -> None:
        """Push completed findings to the caller as soon as they are ready."""
        if not findings or self._finding_callback is None:
            return
        with contextlib.suppress(Exception):
            self._finding_callback(findings)
