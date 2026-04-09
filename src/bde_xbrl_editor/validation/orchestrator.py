"""InstanceValidator — orchestrates the full XBRL validation pipeline.

Runs structural checks → dimensional checks → formula assertions in sequence,
assembling the results into an immutable ValidationReport. Never raises.
"""

from __future__ import annotations

import contextlib
import threading
from collections.abc import Callable
from datetime import datetime

from bde_xbrl_editor.instance.models import XbrlInstance
from bde_xbrl_editor.taxonomy.models import TaxonomyStructure
from bde_xbrl_editor.validation.dimensional import DimensionalConstraintValidator
from bde_xbrl_editor.validation.formula.evaluator import FormulaEvaluator
from bde_xbrl_editor.validation.models import (
    ValidationFinding,
    ValidationReport,
    ValidationSeverity,
)
from bde_xbrl_editor.validation.structural import StructuralConformanceValidator

ProgressCallback = Callable[[int, int, str], None]


class InstanceValidator:
    """Runs the full validation pipeline against a single XbrlInstance.

    Pure Python — no PySide6 dependency.
    """

    def __init__(
        self,
        taxonomy: TaxonomyStructure,
        progress_callback: ProgressCallback | None = None,
        cancel_event: threading.Event | None = None,
    ) -> None:
        self._taxonomy = taxonomy
        self._progress_callback = progress_callback
        self._cancel_event = cancel_event

    def validate_sync(self, instance: XbrlInstance) -> ValidationReport:
        """Run structural + dimensional + formula validation synchronously.

        Always returns a ValidationReport — never raises. Exceptions from
        individual validators are caught and turned into error findings.
        """
        findings: list[ValidationFinding] = []

        # --- 1. Structural checks -------------------------------------------
        if not (self._cancel_event and self._cancel_event.is_set()):
            if self._progress_callback:
                with contextlib.suppress(Exception):
                    self._progress_callback(0, 3, "Running structural checks…")
            try:
                sv = StructuralConformanceValidator()
                findings.extend(sv.validate(instance, self._taxonomy))
            except Exception as exc:  # noqa: BLE001
                findings.append(ValidationFinding(
                    rule_id="internal:structural-error",
                    severity=ValidationSeverity.ERROR,
                    message=f"Structural validator failed unexpectedly: {exc}",
                    source="structural",
                ))

        # --- 2. Dimensional checks -------------------------------------------
        if not (self._cancel_event and self._cancel_event.is_set()):
            if self._progress_callback:
                with contextlib.suppress(Exception):
                    self._progress_callback(1, 3, "Running dimensional checks…")
            try:
                dv = DimensionalConstraintValidator(self._taxonomy)
                findings.extend(dv.validate(instance))
            except Exception as exc:  # noqa: BLE001
                findings.append(ValidationFinding(
                    rule_id="internal:dimensional-error",
                    severity=ValidationSeverity.ERROR,
                    message=f"Dimensional validator failed unexpectedly: {exc}",
                    source="dimensional",
                ))

        # --- 3. Formula assertions ------------------------------------------
        formula_available = bool(
            self._taxonomy.formula_assertion_set.assertions
        )
        if not (self._cancel_event and self._cancel_event.is_set()):
            if self._progress_callback:
                with contextlib.suppress(Exception):
                    self._progress_callback(2, 3, "Evaluating formula assertions…")
            try:
                fe = FormulaEvaluator(
                    taxonomy=self._taxonomy,
                    progress_callback=self._progress_callback,
                    cancel_event=self._cancel_event,
                )
                findings.extend(fe.evaluate(instance))
            except Exception as exc:  # noqa: BLE001
                findings.append(ValidationFinding(
                    rule_id="internal:formula-error",
                    severity=ValidationSeverity.ERROR,
                    message=f"Formula evaluator failed unexpectedly: {exc}",
                    source="formula",
                ))

        if self._progress_callback:
            with contextlib.suppress(Exception):
                self._progress_callback(3, 3, "Validation complete")

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
        )
