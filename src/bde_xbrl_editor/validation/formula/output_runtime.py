"""Conformance-scoped runtime evaluation for Formula output resources."""

from __future__ import annotations

from bde_xbrl_editor.instance.models import XbrlInstance
from bde_xbrl_editor.taxonomy.models import TaxonomyStructure
from bde_xbrl_editor.validation.formula.evaluator import FormulaEvaluator
from bde_xbrl_editor.validation.models import ValidationFinding, ValidationSeverity


class OutputFormulaRuntimeEvaluator:
    """Evaluates output formula value XPath and reports runtime XPath errors.

    This evaluator is intentionally isolated from the main validation flow and is
    used only by conformance execution paths where runtime XPath error codes are
    the expected outcome.
    """

    def __init__(self, taxonomy: TaxonomyStructure) -> None:
        self._taxonomy = taxonomy
        self._evaluator = FormulaEvaluator(taxonomy)

    def evaluate_runtime_errors(self, instance: XbrlInstance) -> tuple[ValidationFinding, ...]:
        findings: list[ValidationFinding] = []
        facts_by_concept = self._evaluator._facts_by_concept(instance)

        for formula in self._taxonomy.formula_assertion_set.output_formulas:
            if not formula.value_xpath.strip():
                continue
            bindings = self._evaluator._bind_variables(
                formula,  # type: ignore[arg-type]
                instance,
                facts_by_concept=facts_by_concept,
            )
            for resolved in bindings:
                if resolved.error is not None:
                    findings.append(self._error_finding(formula.formula_id, resolved.error))
                    continue
                try:
                    self._evaluator._eval_xpath(
                        formula.value_xpath,
                        resolved.fact_binding,
                        instance,
                        formula.namespaces,
                        general_values=resolved.general_values,
                        fact_bindings_as_elements=True,
                    )
                except Exception as exc:  # noqa: BLE001
                    findings.append(self._error_finding(formula.formula_id, exc))

        return tuple(findings)

    @staticmethod
    def _error_finding(formula_id: str, exc: Exception) -> ValidationFinding:
        code = getattr(exc, "code", None)
        rule_id = code if isinstance(code, str) and code else "formula:runtime-error"
        return ValidationFinding(
            rule_id=rule_id,
            severity=ValidationSeverity.ERROR,
            message=f"Output formula '{formula_id}' runtime error: {exc}",
            source="formula",
        )

