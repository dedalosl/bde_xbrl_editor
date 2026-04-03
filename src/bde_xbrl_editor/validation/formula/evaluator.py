"""FormulaEvaluator — evaluates XBRL formula assertions against an instance."""

from __future__ import annotations

import contextlib
import itertools
import threading
from collections.abc import Callable
from decimal import Decimal, InvalidOperation
from typing import Any

from bde_xbrl_editor.instance.models import Fact, XbrlInstance
from bde_xbrl_editor.taxonomy.models import (
    ConsistencyAssertionDefinition,
    ExistenceAssertionDefinition,
    FormulaAssertion,
    FormulaAssertionSet,
    TaxonomyStructure,
    ValueAssertionDefinition,
)
from bde_xbrl_editor.validation.errors import ValidationEngineError
from bde_xbrl_editor.validation.formula.filters import apply_filters
from bde_xbrl_editor.validation.formula.xfi_functions import (
    clear_evaluation_context,
    set_evaluation_context,
)
from bde_xbrl_editor.validation.models import ValidationFinding, ValidationSeverity

ProgressCallback = Callable[[int, int, str], None]


class FormulaEvaluator:
    """Evaluates formula assertions in a taxonomy against an XbrlInstance.

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

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def evaluate(self, instance: XbrlInstance) -> list[ValidationFinding]:
        """Evaluate all non-abstract assertions against instance.

        Returns findings list (may be empty). Never raises.
        Abstract assertions are silently skipped.
        If taxonomy has no formula linkbase, returns [].
        """
        assertion_set: FormulaAssertionSet = self._taxonomy.formula_assertion_set
        if not assertion_set.assertions:
            return []

        findings: list[ValidationFinding] = []
        non_abstract = [a for a in assertion_set.assertions if not a.abstract]
        total = len(non_abstract)

        for idx, assertion in enumerate(non_abstract):
            if self._cancel_event and self._cancel_event.is_set():
                break
            if self._progress_callback:
                with contextlib.suppress(Exception):
                    self._progress_callback(idx, total, assertion.assertion_id)

            try:
                bindings = self._bind_variables(assertion, instance)
                if isinstance(assertion, ValueAssertionDefinition):
                    findings.extend(
                        self._evaluate_value_assertion(assertion, bindings, instance)
                    )
                elif isinstance(assertion, ExistenceAssertionDefinition):
                    findings.extend(
                        self._evaluate_existence_assertion(assertion, bindings)
                    )
                elif isinstance(assertion, ConsistencyAssertionDefinition):
                    findings.extend(
                        self._evaluate_consistency_assertion(assertion, bindings, instance)
                    )
            except ValidationEngineError as exc:
                findings.append(ValidationFinding(
                    rule_id=assertion.assertion_id,
                    severity=ValidationSeverity.ERROR,
                    message=f"Evaluation error: {exc}",
                    source="formula",
                ))
            except Exception as exc:  # noqa: BLE001
                findings.append(ValidationFinding(
                    rule_id="internal:validator-error",
                    severity=ValidationSeverity.ERROR,
                    message=f"Unexpected error evaluating '{assertion.assertion_id}': {exc}",
                    source="formula",
                ))

        if self._progress_callback:
            with contextlib.suppress(Exception):
                self._progress_callback(total, total, "Formula evaluation complete")

        return findings

    # ------------------------------------------------------------------
    # Variable binding
    # ------------------------------------------------------------------

    def _bind_variables(
        self,
        assertion: FormulaAssertion,
        instance: XbrlInstance,
    ) -> list[dict[str, list[Fact]]]:
        """Produce the list of variable binding tuples for an assertion.

        Each binding maps variable_name → list of matching facts.
        Returns the Cartesian product of per-variable match sets.
        """
        all_facts = instance.facts

        per_variable: list[tuple[str, list[list[Fact]]]] = []
        for var_def in assertion.variables:
            matched = apply_filters(all_facts, var_def, instance)
            # Each fact is one binding candidate for this variable
            # We group as list[list[Fact]] where each inner list is [one_fact]
            if matched:
                candidates: list[list[Fact]] = [[f] for f in matched]
            elif var_def.fallback_value is not None:
                candidates = [[]]  # one binding with empty set (fallback applies)
            else:
                candidates = [[]]  # one empty binding
            per_variable.append((var_def.variable_name, candidates))

        if not per_variable:
            return [{}]

        # Cartesian product across all variables
        variable_names = [name for name, _ in per_variable]
        candidate_lists = [candidates for _, candidates in per_variable]
        result: list[dict[str, list[Fact]]] = []
        for combo in itertools.product(*candidate_lists):
            binding: dict[str, list[Fact]] = {
                name: facts for name, facts in zip(variable_names, combo, strict=False)
            }
            result.append(binding)
        return result

    # ------------------------------------------------------------------
    # Assertion evaluators
    # ------------------------------------------------------------------

    def _evaluate_value_assertion(
        self,
        assertion: ValueAssertionDefinition,
        bindings: list[dict[str, list[Fact]]],
        instance: XbrlInstance,
    ) -> list[ValidationFinding]:
        """Evaluate @test XPath for each binding tuple."""
        findings: list[ValidationFinding] = []
        if not assertion.test_xpath:
            return findings

        for binding in bindings:
            try:
                result = self._eval_xpath(assertion.test_xpath, binding, instance)
                passed = _to_bool(result)
            except Exception as exc:  # noqa: BLE001
                findings.append(ValidationFinding(
                    rule_id=assertion.assertion_id,
                    severity=_sev(assertion),
                    message=f"XPath evaluation failed: {exc}",
                    source="formula",
                ))
                continue

            if not passed:
                fact = _first_fact(binding)
                findings.append(ValidationFinding(
                    rule_id=assertion.assertion_id,
                    severity=_sev(assertion),
                    message=(
                        f"Value assertion '{assertion.assertion_id}' failed: "
                        f"test expression evaluated to false"
                    ),
                    source="formula",
                    concept_qname=fact.concept if fact else None,
                    context_ref=fact.context_ref if fact else None,
                ))
        return findings

    def _evaluate_existence_assertion(
        self,
        assertion: ExistenceAssertionDefinition,
        bindings: list[dict[str, list[Fact]]],
    ) -> list[ValidationFinding]:
        """Pass if at least one binding has a non-empty fact set."""
        for binding in bindings:
            for facts in binding.values():
                if facts:
                    return []  # at least one non-empty binding — passes

        return [ValidationFinding(
            rule_id=assertion.assertion_id,
            severity=_sev(assertion),
            message=(
                f"Existence assertion '{assertion.assertion_id}' failed: "
                f"no matching facts found"
            ),
            source="formula",
        )]

    def _evaluate_consistency_assertion(
        self,
        assertion: ConsistencyAssertionDefinition,
        bindings: list[dict[str, list[Fact]]],
        instance: XbrlInstance,
    ) -> list[ValidationFinding]:
        """Evaluate formula expression; compare computed vs. actual fact value."""
        findings: list[ValidationFinding] = []
        if not assertion.formula_xpath:
            return findings

        for binding in bindings:
            fact = _first_fact(binding)
            if fact is None:
                continue
            try:
                computed = self._eval_xpath(assertion.formula_xpath, binding, instance)
                # elementpath.select returns a list; unwrap single-element results
                if isinstance(computed, list):
                    if not computed:
                        continue
                    computed = computed[0]
                computed_val = Decimal(str(computed))
                actual_val = Decimal(fact.value)
            except (InvalidOperation, Exception):  # noqa: BLE001
                continue  # Cannot compare non-numeric values

            difference = abs(computed_val - actual_val)
            passes: bool
            if assertion.absolute_radius is not None:
                passes = difference <= assertion.absolute_radius
            elif assertion.relative_radius is not None and actual_val != 0:
                passes = (difference / abs(actual_val)) <= assertion.relative_radius
            else:
                passes = difference == 0

            if not passes:
                findings.append(ValidationFinding(
                    rule_id=assertion.assertion_id,
                    severity=_sev(assertion),
                    message=(
                        f"Consistency assertion '{assertion.assertion_id}' failed: "
                        f"computed={computed_val}, actual={actual_val}, diff={difference}"
                    ),
                    source="formula",
                    concept_qname=fact.concept,
                    context_ref=fact.context_ref,
                ))
        return findings

    # ------------------------------------------------------------------
    # XPath evaluation helper
    # ------------------------------------------------------------------

    def _eval_xpath(
        self,
        xpath_expr: str,
        binding: dict[str, list[Fact]],
        instance: XbrlInstance,
    ) -> Any:
        """Evaluate an XPath 2.0 expression with the current fact binding."""
        import elementpath  # type: ignore[import-untyped]

        # Build a variable map for elementpath: variable_name → value
        variables: dict[str, Any] = {}
        first_fact: Fact | None = None
        for var_name, facts in binding.items():
            if facts:
                variables[var_name] = _coerce_value(facts[0].value)
                if first_fact is None:
                    first_fact = facts[0]
            else:
                variables[var_name] = ""

        # Set xfi: context
        ctx_obj = None
        unit_obj = None
        if first_fact:
            ctx_obj = instance.contexts.get(first_fact.context_ref)
            if first_fact.unit_ref:
                unit_obj = instance.units.get(first_fact.unit_ref)

        set_evaluation_context({
            "_all_facts": instance.facts,
            "_current_fact": first_fact,
            "_context": ctx_obj,
            "_unit": unit_obj,
        })

        # elementpath requires either a root XML node or an `item` context.
        # For formula XPath (pure arithmetic / fact-value expressions) we
        # use the first fact's value as the context item (or True as a
        # harmless sentinel when no facts are bound).
        context_item = first_fact.value if first_fact is not None else True  # any non-None value satisfies elementpath

        try:
            result = elementpath.select(
                None, xpath_expr, variables=variables, item=context_item
            )
        finally:
            clear_evaluation_context()

        return result


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _sev(assertion: FormulaAssertion) -> ValidationSeverity:
    """Extract severity from assertion, defaulting to ERROR."""
    from bde_xbrl_editor.validation.models import ValidationSeverity as VS
    sev = assertion.severity
    if isinstance(sev, VS):
        return sev
    try:
        return VS(str(sev).lower())
    except ValueError:
        return VS.ERROR


def _first_fact(binding: dict[str, list[Fact]]) -> Fact | None:
    for facts in binding.values():
        if facts:
            return facts[0]
    return None


def _coerce_value(raw: str) -> Any:
    """Convert a raw fact value string to a Python numeric type when possible.

    XPath 2.0 (elementpath) is strictly typed — arithmetic on plain strings
    raises XPTY0004. Coercing to Decimal lets expressions like ``$a + $b``
    work correctly for numeric facts.
    """
    try:
        return Decimal(raw)
    except InvalidOperation:
        return raw


def _to_bool(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, list):
        return bool(value)
    if isinstance(value, str):
        return value.lower() not in ("", "false", "0")
    return bool(value)
