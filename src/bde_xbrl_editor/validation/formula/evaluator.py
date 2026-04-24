"""FormulaEvaluator — evaluates XBRL formula assertions against an instance."""

from __future__ import annotations

import contextlib
import itertools
import re
import threading
import time
from collections.abc import Callable
from decimal import Decimal, InvalidOperation
from typing import Any

from lxml import etree

from bde_xbrl_editor.instance.models import Fact, XbrlInstance
from bde_xbrl_editor.taxonomy.models import (
    AssertionTextResource,
    ConsistencyAssertionDefinition,
    ExistenceAssertionDefinition,
    FormulaAssertion,
    FormulaAssertionSet,
    TaxonomyStructure,
    ValueAssertionDefinition,
)
from bde_xbrl_editor.validation.errors import ValidationEngineError
from bde_xbrl_editor.validation.formula.details import build_formula_display_details
from bde_xbrl_editor.validation.formula.filters import apply_filters
from bde_xbrl_editor.validation.formula.xfi_functions import (
    build_formula_parser,
    clear_evaluation_context,
    set_evaluation_context,
)
from bde_xbrl_editor.validation.models import (
    ValidationFinding,
    ValidationSeverity,
    ValidationStatus,
)

ProgressCallback = Callable[[int, int, str], None]
FindingCallback = Callable[[tuple[ValidationFinding, ...]], None]
_MESSAGE_EXPR_RE = re.compile(r"\{([^{}]+)\}")


class FormulaEvaluator:
    """Evaluates formula assertions in a taxonomy against an XbrlInstance.

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
        self._detail_cache: dict[str, dict[str, str]] = {}
        self._xpath_token_cache: dict[tuple[tuple[tuple[str, str], ...], str], Any] = {}
        self._progress_interval_seconds = 0.1

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
        last_progress_at = 0.0

        for idx, assertion in enumerate(non_abstract):
            if self._cancel_event and self._cancel_event.is_set():
                break
            now = time.perf_counter()
            if (
                self._progress_callback
                and (idx == 0 or idx + 1 == total or (now - last_progress_at) >= self._progress_interval_seconds)
            ):
                with contextlib.suppress(Exception):
                    self._progress_callback(idx, total, assertion.assertion_id)
                last_progress_at = now

            try:
                bindings = self._bind_variables(assertion, instance)
                if isinstance(assertion, ValueAssertionDefinition):
                    assertion_findings = tuple(
                        self._evaluate_value_assertion(assertion, bindings, instance)
                    )
                elif isinstance(assertion, ExistenceAssertionDefinition):
                    assertion_findings = tuple(
                        self._evaluate_existence_assertion(assertion, bindings, instance)
                    )
                elif isinstance(assertion, ConsistencyAssertionDefinition):
                    assertion_findings = tuple(
                        self._evaluate_consistency_assertion(assertion, bindings, instance)
                    )
                else:
                    assertion_findings = ()
                findings.extend(assertion_findings)
                self._publish_findings(assertion_findings)
            except ValidationEngineError as exc:
                assertion_findings = (
                    self._finding_for_assertion(
                        assertion,
                        status=ValidationStatus.FAIL,
                        default_message=f"Evaluation error: {exc}",
                    )
                )
                findings.extend(assertion_findings)
                self._publish_findings(assertion_findings)
            except Exception as exc:  # noqa: BLE001
                assertion_findings = (ValidationFinding(
                    rule_id="internal:validator-error",
                    severity=ValidationSeverity.ERROR,
                    message=f"Unexpected error evaluating '{assertion.assertion_id}': {exc}",
                    source="formula",
                    status=ValidationStatus.FAIL,
                    table_id=assertion.table_id,
                    table_label=assertion.table_label,
                    **self._formula_detail_kwargs(assertion),
                ),)
                findings.extend(assertion_findings)
                self._publish_findings(assertion_findings)

        if self._progress_callback:
            with contextlib.suppress(Exception):
                self._progress_callback(total, total, "Formula evaluation complete")

        return findings

    def _publish_findings(self, findings: tuple[ValidationFinding, ...]) -> None:
        if not findings or self._finding_callback is None:
            return
        with contextlib.suppress(Exception):
            self._finding_callback(findings)

    # ------------------------------------------------------------------
    # Variable binding
    # ------------------------------------------------------------------

    @staticmethod
    def _formula_detail_kwargs(assertion: FormulaAssertion) -> dict[str, str]:
        details = build_formula_display_details(assertion)
        return {
            "formula_assertion_type": details.assertion_type,
            "formula_expression": details.expression,
            "formula_operands_text": details.operands_text,
            "formula_precondition": details.precondition,
        }

    def _cached_formula_detail_kwargs(self, assertion: FormulaAssertion) -> dict[str, str]:
        cached = self._detail_cache.get(assertion.assertion_id)
        if cached is not None:
            return cached
        details = self._formula_detail_kwargs(assertion)
        self._detail_cache[assertion.assertion_id] = details
        return details

    @staticmethod
    def _resource_text(resource: AssertionTextResource | None) -> str | None:
        if resource is None:
            return None
        return resource.text.strip() or None

    def _finding_for_assertion(
        self,
        assertion: FormulaAssertion,
        *,
        status: ValidationStatus,
        default_message: str,
        fact: Fact | None = None,
        binding: dict[str, list[Fact]] | None = None,
        instance: XbrlInstance | None = None,
    ) -> ValidationFinding:
        label_resource = assertion.label_resources[0] if assertion.label_resources else None
        message_candidates = assertion.message_resources
        message_resource: AssertionTextResource | None = None
        if status == ValidationStatus.FAIL:
            message_resource = next(
                (resource for resource in message_candidates if "unsatisfied-message" in resource.arcrole),
                None,
            )
        else:
            message_resource = next(
                (resource for resource in message_candidates if "satisfied-message" in resource.arcrole),
                None,
            )

        evaluated_message = self._render_message_resource(
            assertion,
            message_resource,
            binding=binding,
            instance=instance,
        )
        template_message = self._resource_text(message_resource)
        if self._message_needs_fallback(evaluated_message, template_message):
            evaluated_message = self._build_evaluated_message_fallback(
                assertion,
                binding=binding,
                status=status,
            )
        elif evaluated_message is not None:
            evaluated_message = self._append_assertion_result(
                assertion,
                evaluated_message,
                status=status,
            )
        display_message = (
            evaluated_message
            or (self._resource_text(label_resource) if status == ValidationStatus.PASS else None)
            or default_message
        )
        return ValidationFinding(
            rule_id=assertion.assertion_id,
            severity=None if status == ValidationStatus.PASS else _sev(assertion),
            status=status,
            message=display_message,
            source="formula",
            table_id=assertion.table_id,
            table_label=assertion.table_label,
            concept_qname=fact.concept if fact else None,
            context_ref=fact.context_ref if fact else None,
            rule_label=self._resource_text(label_resource),
            rule_label_role=label_resource.role if label_resource else None,
            rule_message=template_message,
            evaluated_rule_message=evaluated_message if message_resource is not None else None,
            rule_message_role=message_resource.role if message_resource else None,
            **self._cached_formula_detail_kwargs(assertion),
        )

    def _render_message_resource(
        self,
        assertion: FormulaAssertion,
        resource: AssertionTextResource | None,
        *,
        binding: dict[str, list[Fact]] | None,
        instance: XbrlInstance | None,
    ) -> str | None:
        template = self._resource_text(resource)
        if template is None:
            return None
        if resource is None or binding is None or instance is None or "{" not in template:
            return template

        variables = self._build_message_variables(assertion, binding)
        if not variables:
            return template

        namespaces = dict(assertion.namespaces)
        namespaces.update(resource.namespaces)
        first_fact = _first_fact(binding)
        return self._render_message_template(
            template,
            variables=variables,
            instance=instance,
            namespaces=namespaces,
            first_fact=first_fact,
        )

    @staticmethod
    def _build_message_variables(
        assertion: FormulaAssertion,
        binding: dict[str, list[Fact]],
    ) -> dict[str, Any]:
        variables: dict[str, Any] = {}
        for var_def in assertion.variables:
            facts = binding.get(var_def.variable_name, [])
            if facts:
                fact_nodes = [_fact_to_message_element(fact) for fact in facts]
                variables[var_def.variable_name] = (
                    fact_nodes[0] if len(fact_nodes) == 1 else fact_nodes
                )
            elif var_def.fallback_value is not None:
                variables[var_def.variable_name] = _coerce_value(var_def.fallback_value)
            else:
                variables[var_def.variable_name] = []
        return variables

    def _render_message_template(
        self,
        template: str,
        *,
        variables: dict[str, Any],
        instance: XbrlInstance,
        namespaces: dict[str, str],
        first_fact: Fact | None,
    ) -> str:
        def replace_expr(match: re.Match[str]) -> str:
            expr = match.group(1).strip()
            if not expr:
                return ""
            try:
                return self._evaluate_message_expression(
                    expr,
                    variables=variables,
                    instance=instance,
                    namespaces=namespaces,
                    first_fact=first_fact,
                )
            except Exception:  # noqa: BLE001
                return match.group(0)

        return _MESSAGE_EXPR_RE.sub(replace_expr, template)

    @staticmethod
    def _message_needs_fallback(
        evaluated_message: str | None,
        template_message: str | None,
    ) -> bool:
        if template_message is None:
            return False
        if evaluated_message is None:
            return True
        normalized = evaluated_message.strip()
        return normalized == template_message.strip() or "fmt:" in normalized

    def _build_evaluated_message_fallback(
        self,
        assertion: FormulaAssertion,
        *,
        binding: dict[str, list[Fact]] | None,
        status: ValidationStatus,
    ) -> str | None:
        if binding is None:
            return None

        expression = (
            assertion.test_xpath if isinstance(assertion, ValueAssertionDefinition)
            else assertion.formula_xpath if isinstance(assertion, ConsistencyAssertionDefinition)
            else assertion.test_xpath if isinstance(assertion, ExistenceAssertionDefinition)
            else None
        )
        if not expression:
            return None

        rendered_expression = expression
        for var_def in assertion.variables:
            facts = binding.get(var_def.variable_name, [])
            if facts:
                replacement = facts[0].value
            elif var_def.fallback_value is not None:
                replacement = str(_coerce_value(var_def.fallback_value))
            else:
                replacement = "[]"
            rendered_expression = rendered_expression.replace(f"${var_def.variable_name}", replacement)

        rendered_expression = re.sub(r"\s+", " ", rendered_expression).strip()
        if not rendered_expression:
            return None

        if isinstance(assertion, (ValueAssertionDefinition, ExistenceAssertionDefinition)):
            result_text = "TRUE" if status == ValidationStatus.PASS else "FALSE"
            return f"{rendered_expression}\n{result_text}"
        return rendered_expression

    @staticmethod
    def _append_assertion_result(
        assertion: FormulaAssertion,
        evaluated_message: str,
        *,
        status: ValidationStatus,
    ) -> str:
        if not isinstance(assertion, (ValueAssertionDefinition, ExistenceAssertionDefinition)):
            return evaluated_message
        result_text = "TRUE" if status == ValidationStatus.PASS else "FALSE"
        stripped = evaluated_message.rstrip()
        if stripped.endswith(result_text):
            return evaluated_message
        return f"{stripped}\n{result_text}"

    def _evaluate_message_expression(
        self,
        expr: str,
        *,
        variables: dict[str, Any],
        instance: XbrlInstance,
        namespaces: dict[str, str],
        first_fact: Fact | None,
    ) -> str:
        import elementpath  # type: ignore[import-untyped]

        ctx_obj = None
        unit_obj = None
        if first_fact is not None:
            ctx_obj = instance.contexts.get(first_fact.context_ref)
            if first_fact.unit_ref:
                unit_obj = instance.units.get(first_fact.unit_ref)

        set_evaluation_context({
            "_all_facts": instance.facts,
            "_current_fact": first_fact,
            "_context": ctx_obj,
            "_unit": unit_obj,
            "_instance": instance,
            "_custom_functions": self._taxonomy.custom_functions,
        })

        context_item = next(
            (
                value
                for value in variables.values()
                if not isinstance(value, list) or value
            ),
            True,
        )

        token = self._get_xpath_token(expr, namespaces)
        try:
            ctx = elementpath.XPathContext(
                root=None,
                item=context_item,
                variables=variables,
            )
            result = list(token.select(ctx))
        finally:
            clear_evaluation_context()

        return _stringify_xpath_result(result)

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
            matched = apply_filters(
                all_facts,
                var_def,
                instance,
                custom_functions=self._taxonomy.custom_functions,
            )
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
                result = self._eval_xpath(
                    assertion.test_xpath, binding, instance, assertion.namespaces
                )
                passed = _to_bool(result)
            except Exception as exc:  # noqa: BLE001
                findings.append(
                    self._finding_for_assertion(
                        assertion,
                        status=ValidationStatus.FAIL,
                        default_message=f"XPath evaluation failed: {exc}",
                        binding=binding,
                        instance=instance,
                    )
                )
                continue

            fact = _first_fact(binding)
            findings.append(
                self._finding_for_assertion(
                    assertion,
                    status=ValidationStatus.PASS if passed else ValidationStatus.FAIL,
                    default_message=(
                        f"Value assertion '{assertion.assertion_id}' passed"
                        if passed else
                        f"Value assertion '{assertion.assertion_id}' failed: "
                        f"test expression evaluated to false"
                    ),
                    fact=fact,
                    binding=binding,
                    instance=instance,
                )
            )
        return findings

    def _evaluate_existence_assertion(
        self,
        assertion: ExistenceAssertionDefinition,
        bindings: list[dict[str, list[Fact]]],
        instance: XbrlInstance,
    ) -> list[ValidationFinding]:
        """Pass if at least one binding has a non-empty fact set."""
        for binding in bindings:
            for facts in binding.values():
                if facts:
                    return [
                        self._finding_for_assertion(
                            assertion,
                            status=ValidationStatus.PASS,
                            default_message=(
                                f"Existence assertion '{assertion.assertion_id}' passed"
                            ),
                            fact=facts[0],
                            binding=binding,
                            instance=instance,
                        )
                    ]

        return [
            self._finding_for_assertion(
                assertion,
                status=ValidationStatus.FAIL,
                default_message=(
                    f"Existence assertion '{assertion.assertion_id}' failed: "
                    f"no matching facts found"
                ),
                binding=bindings[0] if bindings else None,
                instance=instance,
            )
        ]

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
                computed = self._eval_xpath(
                    assertion.formula_xpath, binding, instance, assertion.namespaces
                )
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

            findings.append(
                self._finding_for_assertion(
                    assertion,
                    status=ValidationStatus.PASS if passes else ValidationStatus.FAIL,
                    default_message=(
                        f"Consistency assertion '{assertion.assertion_id}' passed"
                        if passes else
                        f"Consistency assertion '{assertion.assertion_id}' failed: "
                        f"computed={computed_val}, actual={actual_val}, diff={difference}"
                    ),
                    fact=fact,
                    binding=binding,
                    instance=instance,
                )
            )
        return findings

    # ------------------------------------------------------------------
    # XPath evaluation helper
    # ------------------------------------------------------------------

    def _eval_xpath(
        self,
        xpath_expr: str,
        binding: dict[str, list[Fact]],
        instance: XbrlInstance,
        namespaces: dict[str, str] | None = None,
    ) -> Any:
        """Evaluate an XPath 2.0 expression with the current fact binding."""
        import elementpath  # type: ignore[import-untyped]

        # Build a variable map: variable_name → Decimal (or "" for empty bindings).
        # Decimal values support XPath arithmetic; xfi: functions use the global
        # _eval_context for fact-level metadata.
        variables: dict[str, Any] = {}
        first_fact: Fact | None = None
        for var_name, facts in binding.items():
            if facts:
                variables[var_name] = _coerce_value(facts[0].value)
                if first_fact is None:
                    first_fact = facts[0]
            else:
                variables[var_name] = Decimal(0)

        # Populate the thread-local xfi: evaluation context
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
            "_instance": instance,
            "_custom_functions": self._taxonomy.custom_functions,
        })

        # Use the context item as a Decimal (for arithmetic) when available;
        # fall back to True as a harmless sentinel so elementpath stays happy.
        context_item: Any = (
            _coerce_value(first_fact.value) if first_fact is not None else True
        )

        token = self._get_xpath_token(xpath_expr, namespaces)
        try:
            ctx = elementpath.XPathContext(
                root=None,
                item=context_item,
                variables=variables,
            )
            result = list(token.select(ctx))
        finally:
            clear_evaluation_context()

        return result

    def _get_xpath_token(
        self,
        xpath_expr: str,
        namespaces: dict[str, str] | None = None,
    ) -> Any:
        namespace_items = tuple(sorted((namespaces or {}).items()))
        cache_key = (namespace_items, xpath_expr)
        cached = self._xpath_token_cache.get(cache_key)
        if cached is not None:
            return cached
        parser = build_formula_parser(
            dict(namespace_items),
            custom_functions=self._taxonomy.custom_functions,
            expression_hints=(xpath_expr,),
        )
        token = parser.parse(xpath_expr)
        self._xpath_token_cache[cache_key] = token
        return token


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


def _fact_to_message_element(fact: Fact) -> etree._Element:
    """Build a lightweight XML element for message XPath evaluation."""
    prefix = fact.concept.prefix or "fact"
    nsmap = {prefix: fact.concept.namespace} if fact.concept.namespace else None
    if fact.concept.namespace:
        tag = f"{{{fact.concept.namespace}}}{fact.concept.local_name}"
    else:
        tag = fact.concept.local_name

    element = etree.Element(tag, nsmap=nsmap)
    element.set("contextRef", fact.context_ref)
    if fact.unit_ref:
        element.set("unitRef", fact.unit_ref)
    if fact.decimals is not None:
        element.set("decimals", fact.decimals)
    element.text = fact.value
    return element


def _stringify_xpath_result(result: list[Any]) -> str:
    """Render an XPath result sequence as readable message text."""
    parts: list[str] = []
    for item in result:
        value = getattr(item, "value", item)
        text = str(value).strip()
        if text:
            parts.append(text)
    return " ".join(parts)


def _to_bool(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, list):
        if not value:
            return False
        first = value[0]
        if isinstance(first, bool):
            return first
        if isinstance(first, str):
            return first.lower() not in ("", "false", "0")
        return bool(first)
    if isinstance(value, str):
        return value.lower() not in ("", "false", "0")
    return bool(value)
