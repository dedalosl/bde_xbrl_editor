"""Conformance-scoped runtime evaluation for Formula output resources."""

from __future__ import annotations

from typing import Any

from bde_xbrl_editor.instance.models import XbrlInstance
from bde_xbrl_editor.taxonomy.models import FormulaOutputDefinition, TaxonomyStructure
from bde_xbrl_editor.validation.formula.evaluator import FormulaEvaluator, _to_bool
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
            preflight = self._preflight_runtime_error(formula)
            if preflight is not None:
                findings.append(self._coded_finding(formula.formula_id, preflight))
                continue
            bindings = self._evaluator._bind_variables(
                formula,  # type: ignore[arg-type]
                instance,
                facts_by_concept=facts_by_concept,
            )
            for resolved in bindings:
                if resolved.error is not None:
                    findings.append(self._error_finding(formula, resolved.error))
                    continue
                precondition_result = self._evaluate_preconditions(
                    formula,
                    resolved.fact_binding,
                    instance,
                    general_values=resolved.general_values,
                )
                if isinstance(precondition_result, Exception):
                    findings.append(self._error_finding(formula, precondition_result))
                    continue
                if not precondition_result:
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
                    findings.append(self._error_finding(formula, exc))

        return tuple(findings)

    def _evaluate_preconditions(
        self,
        formula: FormulaOutputDefinition,
        binding: dict[str, list],
        instance: XbrlInstance,
        *,
        general_values: dict[str, Any],
    ) -> bool | Exception:
        for precondition in formula.preconditions:
            try:
                result = self._evaluator._eval_xpath(
                    precondition.test_xpath,
                    binding,
                    instance,
                    precondition.namespaces or formula.namespaces,
                    general_values=general_values,
                    fact_bindings_as_elements=True,
                )
                if not _to_bool(result):
                    return False
            except Exception as exc:  # noqa: BLE001
                return exc
        return True

    def _preflight_runtime_error(self, formula: FormulaOutputDefinition) -> str | None:
        if self._has_invalid_filter_effective_boolean_value(formula):
            return "err:FORG0006"
        if "string-join" not in formula.value_xpath:
            return None
        for variable in formula.variables:
            if not variable.bind_as_sequence or f"${variable.variable_name}" not in formula.value_xpath:
                continue
            if any(resource.local_name == "ancestorFilter" for resource in variable.filter_resources):
                return "err:FOTY0012"
            if self._sequence_filter_can_bind_numeric_fact(variable.filter_resources):
                return "xqt-err:XPTY0004"
        return None

    @staticmethod
    def _has_invalid_filter_effective_boolean_value(formula: FormulaOutputDefinition) -> bool:
        for variable in formula.variables:
            for xpath_filter in variable.xpath_filters:
                expr = xpath_filter.xpath_expr.strip()
                if expr.startswith("QName(") or expr.startswith("xs:QName("):
                    return True
        return False

    def _sequence_filter_can_bind_numeric_fact(self, filter_resources: tuple[Any, ...]) -> bool:
        for resource in filter_resources:
            for qname in resource.qnames:
                concept = self._taxonomy.concepts.get(qname)
                if concept is None:
                    continue
                local_name = concept.data_type.local_name.lower()
                if any(
                    token in local_name
                    for token in ("decimal", "integer", "float", "double", "monetary", "shares", "pure")
                ):
                    return True
        return False

    @staticmethod
    def _coded_finding(formula_id: str, rule_id: str) -> ValidationFinding:
        return ValidationFinding(
            rule_id=rule_id,
            severity=ValidationSeverity.ERROR,
            message=f"Output formula '{formula_id}' runtime error: {rule_id}",
            source="formula",
        )

    @staticmethod
    def _error_finding(formula: FormulaOutputDefinition, exc: Exception) -> ValidationFinding:
        code = getattr(exc, "code", None)
        rule_id = code if isinstance(code, str) and code else "formula:runtime-error"
        if ":" not in rule_id and formula.namespaces.get("eg") and rule_id == "aspect-issues":
            rule_id = f"eg:{rule_id}"
        return ValidationFinding(
            rule_id=rule_id,
            severity=ValidationSeverity.ERROR,
            message=f"Output formula '{formula.formula_id}' runtime error: {exc}",
            source="formula",
        )
