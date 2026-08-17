"""Backward-compatible access to output-formula runtime diagnostics."""

from __future__ import annotations

from bde_xbrl_editor.instance.models import XbrlInstance
from bde_xbrl_editor.taxonomy.models import FormulaOutputDefinition, TaxonomyStructure
from bde_xbrl_editor.validation.formula.output_instance import (
    FormulaOutputInstanceEvaluator,
)
from bde_xbrl_editor.validation.models import ValidationFinding


class OutputFormulaRuntimeEvaluator:
    """Expose runtime findings produced by the Formula output engine.

    New code should use :class:`FormulaOutputInstanceEvaluator`, which evaluates
    each output formula once and returns both the generated instance and its
    runtime diagnostics. This adapter remains for API compatibility.
    """

    def __init__(self, taxonomy: TaxonomyStructure) -> None:
        self._evaluator = FormulaOutputInstanceEvaluator(taxonomy)

    def evaluate_runtime_errors(self, instance: XbrlInstance) -> tuple[ValidationFinding, ...]:
        return self._evaluator.evaluate(instance).findings

    @staticmethod
    def _error_finding(
        formula: FormulaOutputDefinition,
        exc: Exception,
    ) -> ValidationFinding:
        return FormulaOutputInstanceEvaluator._runtime_finding(formula, exc)
