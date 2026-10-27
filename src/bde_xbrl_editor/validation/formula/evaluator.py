"""FormulaEvaluator — evaluates XBRL formula assertions against an instance."""

from __future__ import annotations

import contextlib
import itertools
import re
import threading
import time
from collections.abc import Callable, Iterable, Iterator
from dataclasses import dataclass, field, replace
from datetime import timedelta
from decimal import Decimal, InvalidOperation
from functools import cache, lru_cache
from pathlib import Path
from typing import Any
from urllib.parse import unquote, urldefrag, urljoin, urlsplit

from lxml import etree

from bde_xbrl_editor.instance.constants import XBRLDI_NS, XBRLI_NS
from bde_xbrl_editor.instance.models import Fact, XbrlInstance
from bde_xbrl_editor.instance.s_equal import (
    canonical_context_refs_by_s_equal,
    canonical_unit_refs_by_structure,
    context_s_equal_key,
    unit_structure_key,
)
from bde_xbrl_editor.taxonomy.models import (
    AssertionTextResource,
    BooleanFilterDefinition,
    ConsistencyAssertionDefinition,
    DimensionFilter,
    ExistenceAssertionDefinition,
    FactVariableDefinition,
    FormulaAssertion,
    FormulaAssertionSet,
    FormulaOutputDefinition,
    QName,
    TaxonomyStructure,
    TypedDimensionFilter,
    ValueAssertionDefinition,
    XPathFilterDefinition,
)
from bde_xbrl_editor.taxonomy.type_traits import concept_is_numeric, concept_type_category
from bde_xbrl_editor.validation.errors import ValidationEngineError
from bde_xbrl_editor.validation.formula.details import build_formula_display_details
from bde_xbrl_editor.validation.formula.filters import apply_filters
from bde_xbrl_editor.validation.formula.xfi_functions import (
    build_formula_parser,
    clear_evaluation_context,
    normalize_formula_xpath_expression,
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
_SIMPLE_COMPARISON_RE = re.compile(
    r"^\s*\$([A-Za-z_][\w:.-]*)\s*(?:=|!=|eq|ne|lt|le|gt|ge)\s*(.+?)\s*$",
    re.DOTALL,
)
_FINDING_BATCH_SIZE = 100


@dataclass(frozen=True)
class _VariableBinding:
    fact_binding: dict[str, list[Fact]]
    general_values: dict[str, Any] = field(default_factory=dict)
    uses_fallback: bool = False
    error: Exception | None = None


@dataclass(frozen=True)
class ExternalFormulaParameter:
    """A client-supplied Formula parameter identified by expanded QName."""

    name: str
    datatype: str
    lexical_value: str


@dataclass(frozen=True)
class _ResolvedFormulaRelationship:
    parent: QName
    child: QName
    link_role: str
    arcrole: str
    attributes: dict[QName, str]


class _FactDecimal(Decimal):
    """XPath decimal retaining the source fact identity for xfi functions."""

    def __new__(cls, value: Decimal, fact: Fact) -> _FactDecimal:
        result = super().__new__(cls, value)
        result.context_ref = fact.context_ref
        result.unit_ref = fact.unit_ref
        result.decimals = fact.decimals
        return result


class _FactString(str):
    """XPath string retaining the source fact identity for xfi functions."""

    def __new__(cls, value: str, fact: Fact) -> _FactString:
        result = super().__new__(cls, value)
        result.context_ref = fact.context_ref
        result.unit_ref = fact.unit_ref
        result.decimals = fact.decimals
        return result


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
        general_variable_values: dict[str, str] | None = None,
        external_parameters: Iterable[ExternalFormulaParameter] = (),
    ) -> None:
        self._taxonomy = taxonomy
        self._progress_callback = progress_callback
        self._finding_callback = finding_callback
        self._cancel_event = cancel_event
        self._general_variable_values = dict(general_variable_values or {})
        self._external_parameter_values = {
            parameter.name: _cast_external_parameter(parameter)
            for parameter in external_parameters
        }
        self._detail_cache: dict[str, dict[str, str]] = {}
        self._xpath_token_cache: dict[tuple[tuple[tuple[str, str], ...], str, str | None], Any] = {}
        self._xpath_filter_token_cache: dict[tuple[tuple[tuple[str, str], ...], str], Any] = {}
        self._variable_match_cache: dict[tuple[Any, ...], list[Fact]] = {}
        (
            self._schema_element_types,
            self._schema_attribute_types,
        ) = _schema_atomic_type_maps(taxonomy.schema_files)
        self._progress_interval_seconds = 0.1
        self._current_formula_relationships: tuple[_ResolvedFormulaRelationship, ...] = ()

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
        facts_by_concept = self._facts_by_concept(instance)
        self._variable_match_cache.clear()

        for idx, assertion in enumerate(non_abstract):
            if self._cancel_event and self._cancel_event.is_set():
                break
            now = time.perf_counter()
            if self._progress_callback and (
                idx == 0
                or idx + 1 == total
                or (now - last_progress_at) >= self._progress_interval_seconds
            ):
                with contextlib.suppress(Exception):
                    self._progress_callback(idx, total, assertion.assertion_id)
                last_progress_at = now

            try:
                self._current_formula_relationships = self._resolve_custom_relationships(assertion)
                bindings = self._bind_variables(
                    assertion,
                    instance,
                    facts_by_concept=facts_by_concept,
                )
                if assertion.implicit_filtering and len(assertion.variables) > 1:
                    bindings = self._implicit_formula_bindings(
                        assertion,
                        bindings,
                        instance,
                    )
                if isinstance(assertion, ValueAssertionDefinition):
                    assertion_findings = self._evaluate_value_assertion(
                        assertion, bindings, instance
                    )
                elif isinstance(assertion, ExistenceAssertionDefinition):
                    assertion_findings = self._evaluate_existence_assertion(
                        assertion, bindings, instance
                    )
                elif isinstance(assertion, ConsistencyAssertionDefinition):
                    assertion_findings = self._evaluate_consistency_assertion(
                        assertion, bindings, instance
                    )
                else:
                    assertion_findings = []
                findings.extend(assertion_findings)
            except ValidationEngineError as exc:
                assertion_findings = (
                    self._finding_for_assertion(
                        assertion,
                        status=ValidationStatus.FAIL,
                        default_message=f"Evaluation error: {exc}",
                    ),
                )
                findings.extend(assertion_findings)
                self._publish_findings(assertion_findings)
            except Exception as exc:  # noqa: BLE001
                assertion_findings = (
                    ValidationFinding(
                        rule_id="internal:validator-error",
                        severity=ValidationSeverity.ERROR,
                        message=f"Unexpected error evaluating '{assertion.assertion_id}': {exc}",
                        source="formula",
                        status=ValidationStatus.FAIL,
                        table_id=assertion.table_id,
                        table_label=assertion.table_label,
                        **self._formula_detail_kwargs(assertion),
                    ),
                )
                findings.extend(assertion_findings)
                self._publish_findings(assertion_findings)

        if self._progress_callback:
            with contextlib.suppress(Exception):
                self._progress_callback(total, total, "Formula evaluation complete")

        return findings

    def _resolve_custom_relationships(
        self,
        assertion: FormulaAssertion,
    ) -> tuple[_ResolvedFormulaRelationship, ...]:
        concepts_by_id = {
            concept.xml_id: qname
            for qname, concept in self._taxonomy.concepts.items()
            if concept.xml_id
        }
        resolved: list[_ResolvedFormulaRelationship] = []
        for relationship in assertion.custom_relationships:
            parent = concepts_by_id.get(relationship.from_fragment)
            child = concepts_by_id.get(relationship.to_fragment)
            if parent is None or child is None:
                continue
            resolved.append(
                _ResolvedFormulaRelationship(
                    parent=parent,
                    child=child,
                    link_role=relationship.link_role,
                    arcrole=relationship.arcrole,
                    attributes=dict(relationship.attributes),
                )
            )
        return tuple(resolved)

    def _publish_findings(self, findings: tuple[ValidationFinding, ...]) -> None:
        if not findings or self._finding_callback is None:
            return
        with contextlib.suppress(Exception):
            self._finding_callback(findings)

    def _append_and_maybe_publish(
        self,
        findings: list[ValidationFinding],
        pending_publish: list[ValidationFinding],
        finding: ValidationFinding,
    ) -> None:
        findings.append(finding)
        if self._finding_callback is None:
            return
        pending_publish.append(finding)
        if len(pending_publish) >= _FINDING_BATCH_SIZE:
            self._publish_findings(tuple(pending_publish))
            pending_publish.clear()

    def _publish_pending(self, pending_publish: list[ValidationFinding]) -> None:
        if not pending_publish:
            return
        self._publish_findings(tuple(pending_publish))
        pending_publish.clear()

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
        rule_id: str | None = None,
        fact: Fact | None = None,
        binding: dict[str, list[Fact]] | None = None,
        instance: XbrlInstance | None = None,
        message_variables: dict[str, Any] | None = None,
    ) -> ValidationFinding:
        label_resource = assertion.label_resources[0] if assertion.label_resources else None
        message_candidates = assertion.message_resources
        message_resource: AssertionTextResource | None = None
        if status == ValidationStatus.FAIL:
            message_resource = next(
                (
                    resource
                    for resource in message_candidates
                    if "unsatisfied-message" in resource.arcrole
                ),
                None,
            )
        elif status == ValidationStatus.PASS:
            message_resource = next(
                (
                    resource
                    for resource in message_candidates
                    if "satisfied-message" in resource.arcrole
                ),
                None,
            )

        evaluated_message = self._render_message_resource(
            assertion,
            message_resource,
            binding=binding,
            instance=instance,
            message_variables=message_variables,
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
            rule_id=rule_id or assertion.assertion_id,
            severity=None if status != ValidationStatus.FAIL else _sev(assertion),
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
        message_variables: dict[str, Any] | None = None,
    ) -> str | None:
        template = self._resource_text(resource)
        if template is None:
            return None
        if resource is None or binding is None or instance is None or "{" not in template:
            return template

        variables = self._build_message_variables(assertion, binding)
        variables.update(message_variables or {})
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
        return _with_equivalent_variable_prefixes(variables, assertion.namespaces)

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
            if expr == "." and "__context_item" in variables:
                return str(variables["__context_item"])
            if expr in variables and expr != "__context_item":
                return _stringify_message_value(variables[expr])
            uncovered = self._evaluate_uncovered_message_expression(
                expr,
                first_fact=first_fact,
                instance=instance,
                namespaces=namespaces,
            )
            if uncovered is not None:
                return uncovered
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
    def _evaluate_uncovered_message_expression(
        expression: str,
        *,
        first_fact: Fact | None,
        instance: XbrlInstance,
        namespaces: dict[str, str],
    ) -> str | None:
        if "uncovered-aspect" not in expression or first_fact is None:
            return None
        if "'concept'" in expression or '"concept"' in expression:
            prefix = next(
                (
                    candidate
                    for candidate, namespace in namespaces.items()
                    if namespace == first_fact.concept.namespace
                ),
                first_fact.concept.prefix,
            )
            return (
                f"{prefix}:{first_fact.concept.local_name}"
                if prefix
                else first_fact.concept.local_name
            )
        context = instance.contexts.get(first_fact.context_ref)
        if context is None or "'period'" not in expression and '"period"' not in expression:
            return None
        if "period-start" in expression and context.period.start_date is not None:
            return context.period.start_date.isoformat()
        if "period-end" in expression and context.period.end_date is not None:
            return context.period.end_date.isoformat()
        return None

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
            assertion.test_xpath
            if isinstance(assertion, ValueAssertionDefinition)
            else assertion.formula_xpath
            if isinstance(assertion, ConsistencyAssertionDefinition)
            else assertion.test_xpath
            if isinstance(assertion, ExistenceAssertionDefinition)
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
            rendered_expression = rendered_expression.replace(
                f"${var_def.variable_name}", replacement
            )

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
        if status == ValidationStatus.NOT_EVALUATED:
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

        set_evaluation_context(
            {
                "_all_facts": instance.facts,
                "_current_fact": first_fact,
                "_context": ctx_obj,
                "_unit": unit_obj,
                "_instance": instance,
                "_taxonomy": self._taxonomy,
                "_formula_relationships": self._current_formula_relationships,
                "_custom_functions": self._taxonomy.custom_functions,
            }
        )

        context_item = next(
            (value for value in variables.values() if not isinstance(value, list) or value),
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
        *,
        facts_by_concept: dict[object, list[Fact]] | None = None,
    ) -> Iterator[_VariableBinding]:
        """Yield variable binding tuples for an assertion.

        Each binding maps variable_name → list of matching facts.
        The Cartesian product is streamed so large filings do not allocate all
        binding combinations before the assertion can start evaluating.
        """
        all_facts = instance.facts
        filter_xpath_variables = self._independent_general_variable_values(assertion, instance)
        filter_xpath_variables.update(
            self._resolve_parameter_values(
                assertion.parameters,
                {},
                instance,
                namespaces=assertion.namespaces,
                existing=filter_xpath_variables,
            )
        )
        fact_variable_names = {variable.variable_name for variable in assertion.variables}

        per_variable: list[tuple[str, list[list[Fact]]]] = []
        for var_def in assertion.variables:
            candidate_facts = all_facts
            if self._variable_requests_tuple_facts(var_def, instance.tuple_facts):
                candidate_facts = all_facts + instance.tuple_facts
            independent_var_def = replace(
                var_def,
                xpath_filters=tuple(
                    xpath_filter
                    for xpath_filter in var_def.xpath_filters
                    if not (_xpath_variable_names(xpath_filter.xpath_expr) & fact_variable_names)
                ),
            )
            matched = self._matching_facts_for_variable(
                candidate_facts,
                independent_var_def,
                instance,
                facts_by_concept=facts_by_concept,
                xpath_variables=filter_xpath_variables,
            )
            has_dependent_filters = any(
                resource.variable
                and resource.local_name in {"locationFilter", "siblingFilter"}
                for resource in var_def.filter_resources
            )
            # Each fact is one binding candidate for this variable
            # We group as list[list[Fact]] where each inner list is [one_fact]
            if matched:
                if var_def.bind_as_sequence and assertion.aspect_model is not None:
                    candidates = list(
                        self._group_matched_sequence(
                            matched,
                            var_def,
                            instance,
                            assertion.aspect_model,
                        )
                    )
                else:
                    candidates = [matched] if var_def.bind_as_sequence else [[f] for f in matched]
                if (
                    len(assertion.variables) > 1
                    and var_def.fallback_value is not None
                    and (assertion.implicit_filtering or has_dependent_filters)
                ):
                    candidates.append([])
            elif var_def.fallback_value is not None:
                candidates = [[]]  # one binding with empty set (fallback applies)
            else:
                candidates = [[]]  # one empty binding
            per_variable.append((var_def.variable_name, candidates))

        if not per_variable:
            general_values, uses_general_fallback, general_error = (
                self._resolve_general_variable_bindings(
                    assertion,
                    {},
                    instance,
                )[0]
            )
            yield _VariableBinding(
                fact_binding={},
                general_values=general_values,
                uses_fallback=uses_general_fallback,
                error=general_error,
            )
            return

        # Cartesian product across all variables
        variable_names = [name for name, _ in per_variable]
        candidate_lists = [candidates for _, candidates in per_variable]
        seen_binding_signatures: set[tuple[Any, ...]] = set()
        for combo in itertools.product(*candidate_lists):
            fact_binding: dict[str, list[Fact]] = {
                name: facts for name, facts in zip(variable_names, combo, strict=False)
            }
            uses_fact_fallback = any(
                not facts
                and any(
                    var_def.variable_name == name and var_def.fallback_value is not None
                    for var_def in assertion.variables
                )
                for name, facts in fact_binding.items()
            )
            for (
                general_values,
                uses_general_fallback,
                general_error,
            ) in self._resolve_general_variable_bindings(
                assertion,
                fact_binding,
                instance,
            ):
                expanded_bindings = self._expand_dependent_concept_bindings(
                    assertion,
                    fact_binding,
                    general_values,
                    instance,
                    facts_by_concept=facts_by_concept,
                )
                for expanded_binding in expanded_bindings:
                    if not self._binding_matches_dependent_variable_filters(
                        assertion,
                        expanded_binding,
                        instance,
                        general_values=general_values,
                    ):
                        continue
                    effective_general_values = general_values
                    effective_error = general_error
                    if expanded_binding != fact_binding:
                        effective_general_values, refresh_error = (
                            self._refresh_fact_dependent_general_values(
                                assertion,
                                expanded_binding,
                                general_values,
                                instance,
                            )
                        )
                        effective_error = effective_error or refresh_error
                    binding = _VariableBinding(
                        fact_binding=expanded_binding,
                        general_values=effective_general_values,
                        uses_fallback=uses_fact_fallback or uses_general_fallback,
                        error=effective_error,
                    )
                    signature = self._binding_signature(binding)
                    if signature in seen_binding_signatures:
                        continue
                    seen_binding_signatures.add(signature)
                    yield binding

    def _variable_requests_tuple_facts(
        self,
        variable: FactVariableDefinition,
        tuple_facts: list[Fact],
    ) -> bool:
        """Return whether a static concept filter explicitly selects a tuple."""
        tuple_concepts = {fact.concept for fact in tuple_facts}
        if variable.concept_filter in tuple_concepts:
            return True
        if any(
            resource.local_name == "conceptName"
            and (
                any(qname in tuple_concepts for qname in resource.qnames)
                or (
                    resource.complement
                    and any(qname not in resource.qnames for qname in tuple_concepts)
                )
            )
            for resource in variable.filter_resources
        ):
            return True
        return any(
            resource.local_name == "conceptSubstitutionGroup"
            and any(
                qname.namespace == "http://www.xbrl.org/2003/instance"
                and qname.local_name == "tuple"
                for qname in resource.qnames
            )
            for resource in variable.filter_resources
        )

    def _binding_matches_dependent_variable_filters(
        self,
        assertion: FormulaAssertion,
        fact_binding: dict[str, list[Fact]],
        instance: XbrlInstance,
        *,
        general_values: dict[str, Any],
        only_variable_names: set[str] | None = None,
    ) -> bool:
        """Apply filters whose result depends on another fact-variable binding."""
        fact_variable_names = {variable.variable_name for variable in assertion.variables}
        variables_by_name = {variable.variable_name: variable for variable in assertion.variables}
        dependent_expressions = tuple(
            xpath_filter.xpath_expr
            for variable in assertion.variables
            for xpath_filter in variable.xpath_filters
            if _xpath_variable_names(xpath_filter.xpath_expr) & fact_variable_names
        )
        dependent_xpath_variables = self._build_general_select_variables(
            fact_binding,
            general_values,
            namespaces=assertion.namespaces,
            fact_bindings_as_elements=_expressions_need_fact_nodes(dependent_expressions),
            fact_bindings_with_identity=_expressions_need_fact_identity(dependent_expressions),
        )
        for variable in assertion.variables:
            if not fact_binding.get(variable.variable_name) and variable.fallback_value is not None:
                dependent_xpath_variables[variable.variable_name] = self._evaluate_fallback_xpath(
                    variable.fallback_value,
                    dependent_xpath_variables,
                    assertion.namespaces,
                )
        dependent_xpath_variables = _with_equivalent_variable_prefixes(
            dependent_xpath_variables,
            assertion.namespaces,
        )
        for variable in assertion.variables:
            if only_variable_names is not None and variable.variable_name not in only_variable_names:
                continue
            candidates = fact_binding.get(variable.variable_name, ())
            has_dependent_filters = any(
                resource.variable
                and resource.local_name in {"locationFilter", "siblingFilter"}
                for resource in variable.filter_resources
            )
            if (
                not candidates
                and variable.fallback_value is not None
                and has_dependent_filters
                and not assertion.implicit_filtering
            ):
                independent_variable = replace(
                    variable,
                    xpath_filters=tuple(
                        xpath_filter
                        for xpath_filter in variable.xpath_filters
                        if not (
                            _xpath_variable_names(xpath_filter.xpath_expr) & fact_variable_names
                        )
                    ),
                )
                possible_facts = self._matching_facts_for_variable(
                    instance.facts,
                    independent_variable,
                    instance,
                    facts_by_concept=None,
                    xpath_variables=dependent_xpath_variables,
                )
                has_dependent_match = any(
                    self._binding_matches_dependent_variable_filters(
                        assertion,
                        {**fact_binding, variable.variable_name: [candidate]},
                        instance,
                        general_values=general_values,
                        only_variable_names={variable.variable_name},
                    )
                    for candidate in possible_facts
                )
                if has_dependent_match:
                    return False
                continue
            dependent_xpath_filters = tuple(
                xpath_filter
                for xpath_filter in variable.xpath_filters
                if _xpath_variable_names(xpath_filter.xpath_expr) & fact_variable_names
            )
            if dependent_xpath_filters:
                filter_only_variable = FactVariableDefinition(
                    variable_name=variable.variable_name,
                    nils=True,
                    xpath_filters=dependent_xpath_filters,
                )
                matched_candidates = apply_filters(
                    list(candidates),
                    filter_only_variable,
                    instance,
                    custom_functions=self._taxonomy.custom_functions,
                    xpath_token_cache=self._xpath_filter_token_cache,
                    xpath_variables=dependent_xpath_variables,
                    concepts=self._taxonomy.concepts,
                )
                if len(matched_candidates) != len(candidates):
                    return False
            for resource in variable.filter_resources:
                if resource.local_name == "typedDimension" and resource.test_xpath:
                    xpath_variables = self._build_general_select_variables(
                        fact_binding,
                        general_values,
                        namespaces=resource.namespaces or assertion.namespaces,
                        fact_bindings_as_elements=True,
                    )
                    matched = bool(candidates) and all(
                        self._typed_dimension_filter_test_matches(
                            candidate,
                            resource,
                            instance,
                            xpath_variables=xpath_variables,
                        )
                        for candidate in candidates
                    )
                    if matched == bool(resource.complement):
                        return False
                    continue
                if resource.local_name == "specificScheme" and "$" in resource.attributes.get(
                    "scheme", ""
                ):
                    try:
                        result = self._eval_xpath(
                            resource.attributes["scheme"],
                            fact_binding,
                            instance,
                            resource.namespaces or assertion.namespaces,
                            assertion=assertion,
                            fact_bindings_as_elements=True,
                        )
                    except Exception:  # noqa: BLE001
                        result = []
                    matched = bool(candidates and len(result) == 1) and all(
                        (context := instance.contexts.get(candidate.context_ref)) is not None
                        and context.entity.scheme == str(result[0])
                        for candidate in candidates
                    )
                    if matched == bool(resource.complement):
                        return False
                    continue
                references = fact_binding.get(resource.variable or "", ())
                if resource.local_name == "relativeFilter":
                    reference_variable = variables_by_name.get(resource.variable or "")
                    matched = bool(candidates and references and reference_variable) and all(
                        self._facts_match_relative_filter_aspects(
                            candidate,
                            variable,
                            reference,
                            instance,
                            aspect_model=assertion.aspect_model,
                            equality_tests=getattr(assertion, "typed_dimension_equality_tests", ()),
                        )
                        for candidate in candidates
                        for reference in references
                    )
                elif (
                    resource.local_name == "explicitDimension"
                    and resource.variable
                    and resource.qnames
                    and not variable.bind_as_sequence
                ):
                    dimension_matches = tuple(
                        self._facts_match_dimension_member_variable(
                            candidate,
                            reference,
                            instance,
                            resource.qnames[0],
                            resource,
                        )
                        for candidate in candidates
                        for reference in references
                    )
                    matched = bool(dimension_matches) and all(dimension_matches)
                elif resource.local_name in {"siblingFilter", "locationFilter"}:
                    matched = bool(candidates and references) and all(
                        _tuple_variable_filter_matches(candidate, reference, resource)
                        for candidate in candidates
                        for reference in references
                    )
                elif resource.local_name == "instantDuration":
                    matched = bool(candidates and references) and all(
                        _instant_duration_filter_matches(
                            candidate,
                            reference,
                            resource.attributes.get("boundary", ""),
                            instance,
                        )
                        for candidate in candidates
                        for reference in references
                    )
                elif resource.local_name == "matchPeriod":
                    period_matches = tuple(
                        _facts_have_matching_period(candidate, reference, instance)
                        for candidate in candidates
                        for reference in references
                    )
                    matched = bool(period_matches) and (
                        any(period_matches) if resource.match_any else all(period_matches)
                    )
                elif resource.local_name == "matchConcept":
                    concept_matches = tuple(
                        candidate.concept == reference.concept
                        for candidate in candidates
                        for reference in references
                    )
                    matched = bool(concept_matches) and (
                        any(concept_matches) if resource.match_any else all(concept_matches)
                    )
                elif resource.local_name == "matchEntityIdentifier":
                    entity_identifier_matches = tuple(
                        _facts_have_matching_entity_identifier(candidate, reference, instance)
                        for candidate in candidates
                        for reference in references
                    )
                    matched = bool(entity_identifier_matches) and (
                        any(entity_identifier_matches)
                        if resource.match_any
                        else all(entity_identifier_matches)
                    )
                elif resource.local_name == "matchUnit":
                    unit_matches = tuple(
                        _facts_have_matching_unit(candidate, reference, instance)
                        for candidate in candidates
                        for reference in references
                    )
                    matched = bool(unit_matches) and (
                        any(unit_matches) if resource.match_any else all(unit_matches)
                    )
                elif resource.local_name == "matchLocation":
                    location_matches = tuple(
                        candidate.position_path[:-1] == reference.position_path[:-1]
                        for candidate in candidates
                        for reference in references
                    )
                    matched = bool(location_matches) and (
                        any(location_matches) if resource.match_any else all(location_matches)
                    )
                elif resource.local_name == "matchSegment":
                    segment_matches = tuple(
                        _facts_have_matching_complete_segment(
                            candidate,
                            reference,
                            instance,
                            self._taxonomy,
                        )
                        for candidate in candidates
                        for reference in references
                    )
                    matched = bool(segment_matches) and (
                        any(segment_matches) if resource.match_any else all(segment_matches)
                    )
                elif resource.local_name == "matchNonXDTSegment":
                    segment_matches = tuple(
                        _facts_have_matching_non_xdt_segment(
                            candidate,
                            reference,
                            instance,
                            self._taxonomy,
                        )
                        for candidate in candidates
                        for reference in references
                    )
                    matched = bool(segment_matches) and (
                        any(segment_matches) if resource.match_any else all(segment_matches)
                    )
                elif resource.local_name == "matchScenario":
                    scenario_matches = tuple(
                        _facts_have_matching_complete_scenario(
                            candidate,
                            reference,
                            instance,
                            self._taxonomy,
                        )
                        for candidate in candidates
                        for reference in references
                    )
                    matched = bool(scenario_matches) and (
                        any(scenario_matches) if resource.match_any else all(scenario_matches)
                    )
                elif resource.local_name == "matchNonXDTScenario":
                    scenario_matches = tuple(
                        _facts_have_matching_non_xdt_scenario(
                            candidate,
                            reference,
                            instance,
                            self._taxonomy,
                        )
                        for candidate in candidates
                        for reference in references
                    )
                    matched = bool(scenario_matches) and (
                        any(scenario_matches) if resource.match_any else all(scenario_matches)
                    )
                elif resource.local_name == "matchDimension" and resource.qnames:
                    dimension_matches = tuple(
                        _facts_have_matching_dimension(
                            candidate,
                            reference,
                            instance,
                            resource.qnames[0],
                            equality_tests=getattr(assertion, "typed_dimension_equality_tests", ()),
                            schema_element_types=self._schema_element_types,
                            schema_attribute_types=self._schema_attribute_types,
                        )
                        for candidate in candidates
                        for reference in references
                    )
                    matched = bool(dimension_matches) and (
                        any(dimension_matches) if resource.match_any else all(dimension_matches)
                    )
                else:
                    continue
                if matched == bool(resource.complement):
                    return False
        return True

    def _facts_match_dimension_member_variable(
        self,
        candidate: Fact,
        reference: Fact,
        instance: XbrlInstance,
        dimension: QName,
        resource: Any,
    ) -> bool:
        """Match a dimension member selected relative to a bound fact variable."""
        candidate_context = instance.contexts.get(candidate.context_ref)
        reference_context = instance.contexts.get(reference.context_ref)
        if candidate_context is None or reference_context is None:
            return False
        dimension_model = self._taxonomy.dimensions.get(dimension)
        default_member = dimension_model.default_member if dimension_model is not None else None
        candidate_member = candidate_context.dimensions.get(dimension, default_member)
        reference_member = reference_context.dimensions.get(dimension, default_member)
        if candidate_member is None or reference_member is None:
            return False

        axis = resource.attributes.get("axis", "").strip()
        if not axis or axis == "self":
            return candidate_member == reference_member

        linkrole = resource.attributes.get("linkrole", "").strip()
        arcrole = resource.attributes.get("arcrole", "").strip()
        arcs = [
            arc
            for role, role_arcs in self._taxonomy.definition.items()
            for arc in role_arcs
            if (not linkrole or role == linkrole or arc.extended_link_role == linkrole)
            and (not arcrole or arc.arcrole == arcrole)
        ]
        children = {arc.target for arc in arcs if arc.source == reference_member}
        if axis == "child":
            return candidate_member in children
        if axis == "child-or-self":
            return candidate_member == reference_member or candidate_member in children

        descendants: set[QName] = set()
        frontier = set(children)
        while frontier:
            descendants.update(frontier)
            frontier = {arc.target for arc in arcs if arc.source in frontier} - descendants
        if axis == "descendant":
            return candidate_member in descendants
        if axis == "descendant-or-self":
            return candidate_member == reference_member or candidate_member in descendants
        return False

    def _typed_dimension_filter_test_matches(
        self,
        candidate: Fact,
        resource: Any,
        instance: XbrlInstance,
        *,
        xpath_variables: dict[str, Any],
    ) -> bool:
        """Evaluate ``df:typedDimension/@test`` on its typed-member content."""
        import elementpath  # type: ignore[import-untyped]

        if not resource.qnames:
            return False
        context = instance.contexts.get(candidate.context_ref)
        if context is None:
            return False
        dimension = resource.qnames[0]
        typed_xml = context.typed_dimension_xml.get(dimension)
        if typed_xml is None:
            return False
        try:
            typed_element = etree.fromstring(typed_xml)
            element_qname = _xml_name_qname(str(typed_element.tag))
            schema_type = self._schema_element_types.get(element_qname)
            schema, wrapper_tag = _typed_dimension_schema_proxy(
                element_qname.namespace,
                element_qname.local_name,
                schema_type.namespace if schema_type is not None else "",
                schema_type.local_name if schema_type is not None else "",
                (typed_element.text or "").strip(),
            )
            wrapper = etree.Element(wrapper_tag, nsmap=typed_element.nsmap)
            wrapper.append(typed_element)
            expression = normalize_formula_xpath_expression(resource.test_xpath)
            parser = build_formula_parser(
                resource.namespaces,
                self._taxonomy.custom_functions,
                (expression,),
            )
            token = parser.parse(expression)
        except Exception:  # noqa: BLE001
            return False

        unit = instance.units.get(candidate.unit_ref or "")
        set_evaluation_context(
            {
                "_all_facts": instance.facts,
                "_current_fact": candidate,
                "_context": context,
                "_unit": unit,
                "_instance": instance,
                "_taxonomy": self._taxonomy,
                "_formula_relationships": self._current_formula_relationships,
                "_custom_functions": self._taxonomy.custom_functions,
            }
        )
        try:
            xpath_context = elementpath.XPathContext(
                root=wrapper,
                item=wrapper,
                schema=schema,
                variables=xpath_variables,
            )
            return _to_bool(list(token.select(xpath_context)))
        except Exception:  # noqa: BLE001
            return False
        finally:
            clear_evaluation_context()

    def _expand_dependent_concept_bindings(
        self,
        assertion: FormulaAssertion,
        fact_binding: dict[str, list[Fact]],
        general_values: dict[str, Any],
        instance: XbrlInstance,
        *,
        facts_by_concept: dict[object, list[Fact]] | None,
    ) -> tuple[dict[str, list[Fact]], ...]:
        dynamic_variables: list[
            tuple[FactVariableDefinition, tuple[XPathFilterDefinition, ...], tuple[Any, ...]]
        ] = []
        for variable in assertion.variables:
            concept_expressions = tuple(
                xpath_filter
                for xpath_filter in variable.xpath_filters
                if xpath_filter.filter_type == "concept"
                and re.search(r"\$[A-Za-z_]", xpath_filter.xpath_expr)
            )
            relation_resources = tuple(
                resource
                for resource in variable.filter_resources
                if resource.local_name == "conceptRelation"
            )
            if concept_expressions or relation_resources:
                dynamic_variables.append((variable, concept_expressions, relation_resources))

        if not dynamic_variables:
            return (fact_binding,)

        dynamic_names = {variable.variable_name for variable, _, _ in dynamic_variables}
        ordered_variables: list[
            tuple[FactVariableDefinition, tuple[XPathFilterDefinition, ...], tuple[Any, ...]]
        ] = []
        remaining = list(dynamic_variables)
        resolved: set[str] = set()
        while remaining:
            ready = [
                item
                for item in remaining
                if not (
                    _dependent_fact_variable_names(item[1], item[2]) & (dynamic_names - resolved)
                )
            ]
            if not ready:
                # Cyclic dependencies retain document order; XPath evaluation
                # will then produce the normal empty/error outcome.
                ordered_variables.extend(remaining)
                break
            for item in ready:
                ordered_variables.append(item)
                resolved.add(item[0].variable_name)
                remaining.remove(item)

        expanded: list[dict[str, list[Fact]]] = [
            {name: list(facts) for name, facts in fact_binding.items()}
        ]
        for variable, concept_expressions, relation_resources in ordered_variables:
            next_bindings: list[dict[str, list[Fact]]] = []
            for candidate_binding in expanded:
                if concept_expressions:
                    expression_texts = tuple(
                        expression.xpath_expr for expression in concept_expressions
                    )
                    xpath_variables = self._build_general_select_variables(
                        candidate_binding,
                        general_values,
                        namespaces=assertion.namespaces,
                        fact_bindings_as_elements=_expressions_need_fact_nodes(expression_texts),
                        fact_bindings_with_identity=_expressions_need_fact_identity(
                            expression_texts
                        ),
                    )
                    xpath_variables.update(
                        self._resolve_parameter_values(
                            assertion.parameters,
                            candidate_binding,
                            instance,
                            namespaces=assertion.namespaces,
                            existing={**general_values, **xpath_variables},
                        )
                    )
                    for fact_variable in assertion.variables:
                        if (
                            not candidate_binding.get(fact_variable.variable_name)
                            and fact_variable.fallback_value is not None
                        ):
                            xpath_variables[fact_variable.variable_name] = (
                                self._evaluate_fallback_xpath(
                                    fact_variable.fallback_value,
                                    xpath_variables,
                                    assertion.namespaces,
                                )
                            )
                    xpath_variables = _with_equivalent_variable_prefixes(
                        xpath_variables,
                        assertion.namespaces,
                    )
                    matched = self._matching_facts_for_variable(
                        instance.facts,
                        variable,
                        instance,
                        facts_by_concept=facts_by_concept,
                        xpath_variables=xpath_variables,
                    )
                else:
                    matched = self._matching_concept_relation_facts(
                        relation_resources,
                        candidate_binding,
                        instance,
                        general_values=general_values,
                        namespaces=assertion.namespaces,
                    )

                if matched:
                    choices = (
                        [matched] if variable.bind_as_sequence else [[fact] for fact in matched]
                    )
                else:
                    choices = [[]]
                for facts in choices:
                    next_binding = {
                        name: list(bound_facts) for name, bound_facts in candidate_binding.items()
                    }
                    next_binding[variable.variable_name] = list(facts)
                    next_bindings.append(next_binding)
            expanded = next_bindings

        return tuple(expanded)

    def _matching_concept_relation_facts(
        self,
        resources: tuple[Any, ...],
        fact_binding: dict[str, list[Fact]],
        instance: XbrlInstance,
        *,
        general_values: dict[str, Any] | None = None,
        namespaces: dict[str, str] | None = None,
    ) -> list[Fact]:
        matched: list[Fact] = []
        canonical_contexts = canonical_context_refs_by_s_equal(instance, self._taxonomy)
        canonical_units = canonical_unit_refs_by_structure(instance)
        general_values = general_values or {}
        namespaces = namespaces or {}

        def expression_value(expression: str, first_fact: Fact | None = None) -> Any | None:
            values = self._evaluate_general_variable_select(
                expression,
                variables=general_values,
                instance=instance,
                namespaces=namespaces,
                first_fact=first_fact,
            )
            if isinstance(values, list):
                return values[0] if values else None
            return values

        def expression_string(resource: Any, name: str, first_fact: Fact | None) -> str:
            fixed = resource.attributes.get(name, "").strip()
            expression = resource.attributes.get(f"{name}Expression", "").strip()
            if not expression:
                return fixed
            value = expression_value(expression, first_fact)
            return str(value or "")

        def qname_value(value: Any, resource: Any) -> QName | None:
            if value is None:
                return None
            namespace = getattr(value, "namespace", None)
            local_name = getattr(value, "local_name", None)
            if namespace is not None and local_name:
                return QName(str(namespace), str(local_name))
            lexical = str(value)
            if lexical.startswith("{") and "}" in lexical:
                uri, local = lexical[1:].split("}", 1)
                return QName(uri, local)
            if ":" in lexical:
                prefix, local = lexical.split(":", 1)
                resolved = resource.namespaces.get(prefix) or namespaces.get(prefix)
                if resolved is not None:
                    return QName(resolved, local)
            return QName(resource.namespaces.get("", namespaces.get("", "")), lexical)

        def network_arcs(arcrole: str, linkrole: str) -> list[tuple[QName, QName]]:
            if arcrole.endswith("/parent-child"):
                return [
                    (arc.parent, arc.child)
                    for role, network in self._taxonomy.presentation.items()
                    if not linkrole or role == linkrole or network.extended_link_role == linkrole
                    for arc in network.arcs
                ]
            return [
                (arc.source, arc.target)
                for role, arcs in self._taxonomy.definition.items()
                for arc in arcs
                if (not linkrole or role == linkrole or arc.extended_link_role == linkrole)
                and (not arcrole or arc.arcrole == arcrole)
            ]

        def related_concepts(
            source: QName,
            axis: str,
            arcs: list[tuple[QName, QName]],
            generations: int | None,
        ) -> set[QName]:
            is_root = source.namespace == "http://www.xbrl.org/2008/function/instance"
            is_root = is_root and source.local_name == "root"
            if is_root:
                roots = {parent for parent, _ in arcs} - {child for _, child in arcs}
                return roots if axis in {"sibling", "sibling-or-self", "child"} else set()
            children = {child for parent, child in arcs if parent == source}
            parents = {parent for parent, child in arcs if child == source}
            if axis == "child":
                return children
            if axis == "child-or-self":
                return children | {source}
            if axis in {"sibling", "sibling-or-self"}:
                siblings = {
                    child
                    for parent, child in arcs
                    if parent in parents and (axis.endswith("or-self") or child != source)
                }
                return siblings
            forward = axis in {"descendant", "descendant-or-self"}
            reverse = axis in {"ancestor", "ancestor-or-self"}
            if not forward and not reverse:
                return set()
            result = {source} if axis.endswith("or-self") else set()
            frontier = {source}
            depth = 0
            while frontier and (generations is None or depth < generations):
                next_frontier = {
                    target if forward else origin
                    for origin, target in arcs
                    if (origin if forward else target) in frontier
                } - result
                result.update(next_frontier)
                frontier = next_frontier
                depth += 1
            return result

        for resource in resources:
            parent_facts = fact_binding.get(resource.variable, ()) if resource.variable else ()
            first_fact = parent_facts[0] if parent_facts else _first_fact(fact_binding)
            arcrole = expression_string(resource, "arcrole", first_fact)
            linkrole = expression_string(resource, "linkrole", first_fact)
            axis = resource.attributes.get("axis", "child").strip() or "child"
            generations_text = resource.attributes.get("generations", "").strip()
            generations = int(generations_text) if generations_text.isdigit() else None
            source_concept = parent_facts[0].concept if parent_facts else None
            if source_concept is None and resource.qname_expressions:
                source_concept = qname_value(
                    expression_value(resource.qname_expressions[0], first_fact),
                    resource,
                )
            if source_concept is None and resource.qnames:
                source_concept = resource.qnames[0]

            if (
                source_concept is not None
                and not arcrole.endswith("/summation-item")
                and not resource.test_xpath
            ):
                concepts = related_concepts(
                    source_concept,
                    axis,
                    network_arcs(arcrole, linkrole),
                    generations,
                )
                if concepts:
                    if parent_facts:
                        parent = parent_facts[0]
                        parent_context = canonical_contexts.get(
                            parent.context_ref, parent.context_ref
                        )
                        parent_unit = canonical_units.get(
                            parent.unit_ref or "", parent.unit_ref or ""
                        )
                        matched.extend(
                            fact
                            for fact in instance.facts
                            if fact.concept in concepts
                            and canonical_contexts.get(fact.context_ref, fact.context_ref)
                            == parent_context
                            and canonical_units.get(fact.unit_ref or "", fact.unit_ref or "")
                            == parent_unit
                        )
                    else:
                        matched.extend(fact for fact in instance.facts if fact.concept in concepts)
                continue
            if not parent_facts and resource.qnames:
                item_facts = fact_binding.get("item", ())
                parent_facts = item_facts
                source_concept = resource.qnames[0]
                custom_relationships = [
                    relationship
                    for relationship in self._current_formula_relationships
                    if relationship.parent == source_concept
                    and (
                        not resource.attributes.get("linkrole")
                        or relationship.link_role == resource.attributes.get("linkrole")
                    )
                    and (
                        not resource.attributes.get("arcrole")
                        or relationship.arcrole == resource.attributes.get("arcrole")
                    )
                ]
                for item in item_facts:
                    relationship = next(
                        (
                            candidate
                            for candidate in custom_relationships
                            if candidate.child == item.concept
                        ),
                        None,
                    )
                    if relationship is None:
                        continue
                    minimum = next(
                        (
                            value
                            for qname, value in relationship.attributes.items()
                            if qname.local_name == "minRequiredPrecision"
                        ),
                        None,
                    )
                    try:
                        if minimum is not None and Decimal(minimum) > Decimal(item.decimals or "0"):
                            matched.append(item)
                    except InvalidOperation:
                        continue
                continue
            if not parent_facts:
                continue
            parent = parent_facts[0]
            if axis != "child":
                continue
            wanted_weight: Decimal | None = None
            weight_match = re.search(
                r"\bweight\b.*?\beq\s+(-?\d+(?:\.\d+)?)",
                resource.test_xpath or "",
            )
            if weight_match:
                wanted_weight = Decimal(weight_match.group(1))
            child_concepts = {
                arc.child
                for arcs in self._taxonomy.calculation.values()
                for arc in arcs
                if arc.parent == parent.concept
                and (not arcrole or arcrole.endswith("summation-item"))
                and (not linkrole or arc.extended_link_role == linkrole)
                and (wanted_weight is None or Decimal(str(arc.weight)) == wanted_weight)
            }
            parent_context = canonical_contexts.get(parent.context_ref, parent.context_ref)
            parent_unit = canonical_units.get(parent.unit_ref or "", parent.unit_ref or "")
            matched.extend(
                fact
                for fact in instance.facts
                if fact.concept in child_concepts
                and canonical_contexts.get(fact.context_ref, fact.context_ref) == parent_context
                and canonical_units.get(fact.unit_ref or "", fact.unit_ref or "") == parent_unit
            )
        return matched

    def _group_matched_sequence(
        self,
        facts: list[Fact],
        variable: FactVariableDefinition,
        instance: XbrlInstance,
        aspect_model: str,
    ) -> tuple[list[Fact], ...]:
        groups: dict[tuple[Any, ...], list[Fact]] = {}
        canonical_contexts = canonical_context_refs_by_s_equal(instance, self._taxonomy)
        canonical_units = canonical_unit_refs_by_structure(instance)
        covered, covered_dimensions = self._covered_formula_aspects(variable)

        def aspect_key(
            fact: Fact,
            omitted: set[str],
            omitted_dimensions: set[object],
        ) -> tuple[Any, ...]:
            context = instance.contexts.get(fact.context_ref)
            if context is None and {"entity", "period", "dimensions"} <= omitted:
                context_key = (None, None, (), ())
            elif context is None:
                context_key: Any = canonical_contexts.get(fact.context_ref, fact.context_ref)
            elif (
                not omitted_dimensions
                and "dimensions" not in omitted
                and "entity" not in omitted
                and "period" not in omitted
                and "remainder" not in omitted
            ):
                if aspect_model == "dimensional":
                    s_equal_key = context_s_equal_key(
                        context,
                        dict(self._taxonomy.element_defaults),
                    )
                    dimension_tags = {
                        f"{{{XBRLDI_NS}}}explicitMember",
                        f"{{{XBRLDI_NS}}}typedMember",
                    }
                    scenario, segment = s_equal_key[4:6]
                    dimension_members = tuple(
                        sorted(
                            (
                                child
                                for child in (*scenario, *segment)
                                if child[0] in dimension_tags
                            ),
                            key=repr,
                        )
                    )
                    context_key = (
                        *s_equal_key[:4],
                        tuple(child for child in scenario if child[0] not in dimension_tags),
                        tuple(child for child in segment if child[0] not in dimension_tags),
                        dimension_members,
                    )
                else:
                    context_key = canonical_contexts.get(fact.context_ref, fact.context_ref)
            else:
                context_key = (
                    None if "entity" in omitted else repr(context.entity),
                    None if "period" in omitted else repr(context.period),
                    ()
                    if "dimensions" in omitted
                    else tuple(
                        sorted(
                            (str(dimension), str(member))
                            for dimension, member in context.dimensions.items()
                            if dimension not in omitted_dimensions
                        )
                    ),
                    ()
                    if "dimensions" in omitted
                    else tuple(
                        sorted(
                            (str(dimension), value)
                            for dimension, value in context.typed_dimensions.items()
                            if dimension not in omitted_dimensions
                        )
                    ),
                )
            return (
                None if "concept" in omitted else fact.concept,
                context_key,
                None
                if "unit" in omitted
                else canonical_units.get(fact.unit_ref or "", fact.unit_ref or ""),
                None if "location" in omitted else fact.tuple_path,
            )

        for fact in facts:
            groups.setdefault(aspect_key(fact, covered, covered_dimensions), []).append(fact)
        if variable.matches or "location" in covered:
            return tuple(groups.values())

        evaluations: list[list[Fact]] = []
        for source_group in groups.values():
            duplicate_buckets: dict[tuple[Any, ...], list[Fact]] = {}
            for fact in source_group:
                duplicate_buckets.setdefault(aspect_key(fact, set(), set()), []).append(fact)
            evaluation_count = max(len(bucket) for bucket in duplicate_buckets.values())
            for index in range(evaluation_count):
                evaluations.append(
                    [bucket[min(index, len(bucket) - 1)] for bucket in duplicate_buckets.values()]
                )
        return tuple(evaluations)

    def _independent_general_variable_values(
        self,
        assertion: FormulaAssertion,
        instance: XbrlInstance,
    ) -> dict[str, Any]:
        """Resolve general variables that do not depend on fact-variable bindings."""
        fact_names = {variable.variable_name for variable in assertion.variables}
        values: dict[str, Any] = {}
        for variable in _dependency_ordered_general_variables(assertion):
            if fact_names.intersection(variable.referenced_names):
                continue
            try:
                selected = self._evaluate_general_variable_select(
                    variable.select_xpath,
                    variables=values,
                    instance=instance,
                    namespaces=variable.namespaces or assertion.namespaces,
                    first_fact=None,
                    base_uri=getattr(assertion, "xpath_base_uri", None),
                )
            except Exception:  # noqa: BLE001
                continue
            if selected is None:
                continue
            if variable.bind_as_sequence:
                values[variable.variable_name] = selected
            elif isinstance(selected, list):
                values[variable.variable_name] = selected[0] if selected else []
            else:
                values[variable.variable_name] = selected
        values.update(
            self._resolve_parameter_values(
                assertion.parameters,
                {},
                instance,
                namespaces=assertion.namespaces,
                existing=values,
            )
        )
        return values

    def _resolve_general_variable_bindings(
        self,
        assertion: FormulaAssertion,
        fact_binding: dict[str, list[Fact]],
        instance: XbrlInstance,
    ) -> list[tuple[dict[str, Any], bool, Exception | None]]:
        if not assertion.general_variables:
            return [({}, False, None)]
        candidates: list[tuple[dict[str, Any], bool, Exception | None]] = [({}, False, None)]
        first_fact = _first_fact(fact_binding)
        for variable in _dependency_ordered_general_variables(assertion):
            next_candidates: list[tuple[dict[str, Any], bool, Exception | None]] = []
            for candidate, candidate_uses_fallback, candidate_error in candidates:
                if candidate_error is not None:
                    next_candidates.append((candidate, candidate_uses_fallback, candidate_error))
                    continue
                if variable.variable_name in self._general_variable_values:
                    value = _coerce_fallback_value(
                        self._general_variable_values[variable.variable_name]
                    )
                    expanded = [value]
                    selected_from_fallback = False
                else:
                    eval_vars = self._build_general_select_variables(
                        fact_binding,
                        candidate,
                        namespaces=assertion.namespaces,
                        fact_bindings_as_elements=(
                            "xfi:fact-" in variable.select_xpath
                            or "xfi:concept-" in variable.select_xpath
                            or "node-name(" in variable.select_xpath
                        ),
                    )
                    for fact_variable in assertion.variables:
                        if (
                            not fact_binding.get(fact_variable.variable_name)
                            and fact_variable.fallback_value is not None
                        ):
                            eval_vars.setdefault(
                                fact_variable.variable_name,
                                _coerce_fallback_value(fact_variable.fallback_value),
                            )
                    try:
                        selected = self._evaluate_general_variable_select(
                            variable.select_xpath,
                            variables=eval_vars,
                            instance=instance,
                            namespaces=variable.namespaces or assertion.namespaces,
                            first_fact=first_fact,
                            base_uri=getattr(assertion, "xpath_base_uri", None),
                        )
                    except Exception as exc:  # noqa: BLE001
                        next_candidates.append((dict(candidate), candidate_uses_fallback, exc))
                        continue
                    if selected is None:
                        if variable.fallback_value is None:
                            expanded = [[]]
                            selected_from_fallback = False
                        else:
                            expanded = [_coerce_fallback_value(variable.fallback_value)]
                            selected_from_fallback = True
                    elif variable.bind_as_sequence:
                        expanded = [selected]
                        selected_from_fallback = False
                    elif isinstance(selected, list):
                        expanded = list(selected) if selected else [[]]
                        selected_from_fallback = False
                    else:
                        expanded = [selected]
                        selected_from_fallback = False

                for value in expanded:
                    next_candidate = dict(candidate)
                    next_candidate[variable.variable_name] = value
                    next_candidates.append(
                        (
                            next_candidate,
                            candidate_uses_fallback or selected_from_fallback,
                            None,
                        )
                    )
            candidates = next_candidates or candidates
        return candidates

    def _refresh_fact_dependent_general_values(
        self,
        assertion: FormulaAssertion,
        fact_binding: dict[str, list[Fact]],
        current_values: dict[str, Any],
        instance: XbrlInstance,
    ) -> tuple[dict[str, Any], Exception | None]:
        """Re-evaluate general variables affected by a dynamic fact binding."""
        values = dict(current_values)
        dirty_names = {variable.variable_name for variable in assertion.variables}
        first_fact = _first_fact(fact_binding)
        for variable in _dependency_ordered_general_variables(assertion):
            if not dirty_names.intersection(variable.referenced_names):
                continue
            eval_vars = self._build_general_select_variables(
                fact_binding,
                values,
                namespaces=assertion.namespaces,
                fact_bindings_as_elements=(
                    "xfi:fact-" in variable.select_xpath
                    or "xfi:concept-" in variable.select_xpath
                    or "node-name(" in variable.select_xpath
                ),
            )
            for fact_variable in assertion.variables:
                if (
                    not fact_binding.get(fact_variable.variable_name)
                    and fact_variable.fallback_value is not None
                ):
                    eval_vars.setdefault(
                        fact_variable.variable_name,
                        _coerce_fallback_value(fact_variable.fallback_value),
                    )
            try:
                selected = self._evaluate_general_variable_select(
                    variable.select_xpath,
                    variables=eval_vars,
                    instance=instance,
                    namespaces=variable.namespaces or assertion.namespaces,
                    first_fact=first_fact,
                    base_uri=getattr(assertion, "xpath_base_uri", None),
                )
            except Exception as exc:  # noqa: BLE001
                return values, exc
            if selected is None and variable.fallback_value is not None:
                selected = _coerce_fallback_value(variable.fallback_value)
            if variable.bind_as_sequence:
                values[variable.variable_name] = selected or []
            elif isinstance(selected, list):
                values[variable.variable_name] = selected[0] if selected else []
            else:
                values[variable.variable_name] = selected
            dirty_names.add(variable.variable_name)
        return values, None

    @classmethod
    def _binding_signature(cls, binding: _VariableBinding) -> tuple[Any, ...]:
        return (
            cls._binding_trail_key(binding.fact_binding),
            tuple(
                sorted(
                    (name, cls._value_signature(value))
                    for name, value in binding.general_values.items()
                )
            ),
        )

    @staticmethod
    def _value_signature(value: Any) -> Any:
        if isinstance(value, list):
            return tuple(FormulaEvaluator._value_signature(item) for item in value)
        if hasattr(value, "value"):
            return value.value
        return str(value)

    @staticmethod
    def _binding_trail_key(binding: dict[str, list[Fact]]) -> tuple[Any, ...]:
        trail: list[tuple[str, tuple[tuple[Any, ...], ...]]] = []
        for name in sorted(binding):
            facts = binding[name]
            serialized = tuple(
                (
                    str(fact.concept),
                    fact.context_ref,
                    fact.unit_ref,
                    fact.value,
                    fact.decimals,
                    fact.is_nil,
                    fact.tuple_path,
                    fact.position_path,
                )
                for fact in facts
            )
            trail.append((name, serialized))
        return tuple(trail)

    def _build_general_select_variables(
        self,
        fact_binding: dict[str, list[Fact]],
        general_values: dict[str, Any],
        *,
        namespaces: dict[str, str],
        fact_bindings_as_elements: bool = False,
        fact_bindings_with_identity: bool = False,
    ) -> dict[str, Any]:
        variables: dict[str, Any] = dict(general_values)
        for fact_name, facts in fact_binding.items():
            if not facts:
                continue
            if fact_bindings_as_elements:
                fact_values = [_fact_to_message_element(fact) for fact in facts]
                variables[fact_name] = fact_values[0] if len(fact_values) == 1 else fact_values
                continue
            fact_values = [
                self._coerce_fact_xpath_value(
                    fact,
                    namespaces=namespaces,
                    xpath_expr="",
                )
                for fact in facts
            ]
            if fact_bindings_with_identity:
                fact_values = [
                    _atomic_value_with_fact_identity(value, fact)
                    for value, fact in zip(fact_values, facts, strict=False)
                ]
            variables[fact_name] = fact_values[0] if len(fact_values) == 1 else fact_values
        return _with_equivalent_variable_prefixes(variables, namespaces)

    def _matching_facts_for_variable(
        self,
        all_facts: list[Fact],
        var_def: FactVariableDefinition,
        instance: XbrlInstance,
        *,
        facts_by_concept: dict[object, list[Fact]] | None,
        xpath_variables: dict[str, Any] | None = None,
    ) -> list[Fact]:
        original_var_def = var_def
        var_def = self._with_expanded_dimension_members(var_def)
        if var_def is not original_var_def and any(
            dimension_filter.member_axis and not dimension_filter.member_qnames
            for dimension_filter in var_def.dimension_filters
        ):
            # A network-selection axis whose traversal selects no domain members
            # denotes the empty filter result (Formula erratum 1), not "any member".
            return []
        cache_key = (
            self._variable_match_cache_key(var_def),
            tuple(
                sorted(
                    (name, self._value_signature(value))
                    for name, value in (xpath_variables or {}).items()
                )
            ),
        )
        cached = self._variable_match_cache.get(cache_key)
        if cached is not None:
            return cached

        matched = apply_filters(
            all_facts,
            var_def,
            instance,
            custom_functions=self._taxonomy.custom_functions,
            facts_by_concept=facts_by_concept,
            xpath_token_cache=self._xpath_filter_token_cache,
            xpath_variables=xpath_variables,
            dimension_defaults={
                qname: dimension.default_member
                for qname, dimension in self._taxonomy.dimensions.items()
                if dimension.default_member is not None
            },
            concepts=self._taxonomy.concepts,
        )
        self._variable_match_cache[cache_key] = matched
        return matched

    def _with_expanded_dimension_members(
        self,
        var_def: FactVariableDefinition,
    ) -> FactVariableDefinition:
        expanded_filters: list[DimensionFilter] = []
        changed = False
        for dimension_filter in var_def.dimension_filters:
            if not dimension_filter.member_axis or not dimension_filter.member_qnames:
                expanded_filters.append(dimension_filter)
                continue
            arcs = list(self._taxonomy.definition.get(dimension_filter.member_linkrole or "", ()))
            if dimension_filter.member_arcrole:
                arcs = [arc for arc in arcs if arc.arcrole == dimension_filter.member_arcrole]
            members = set(dimension_filter.member_qnames)
            frontier = set(dimension_filter.member_qnames)
            descendants: set[QName] = set()
            while frontier:
                next_frontier = {arc.target for arc in arcs if arc.source in frontier} - descendants
                descendants.update(next_frontier)
                frontier = next_frontier
            if dimension_filter.member_axis == "child":
                selected = {arc.target for arc in arcs if arc.source in members}
            elif dimension_filter.member_axis == "child-or-self":
                selected = {arc.target for arc in arcs if arc.source in members} | members
            elif dimension_filter.member_axis == "descendant":
                selected = descendants
            elif dimension_filter.member_axis == "descendant-or-self":
                selected = descendants | members
            else:
                selected = members
            expanded_filters.append(
                DimensionFilter(
                    dimension_qname=dimension_filter.dimension_qname,
                    member_qnames=tuple(sorted(selected, key=str)),
                    exclude=dimension_filter.exclude,
                    member_linkrole=dimension_filter.member_linkrole,
                    member_arcrole=dimension_filter.member_arcrole,
                    member_axis=dimension_filter.member_axis,
                )
            )
            changed = True
        if not changed:
            return var_def
        from dataclasses import replace

        return replace(var_def, dimension_filters=tuple(expanded_filters))

    @staticmethod
    def _facts_by_concept(instance: XbrlInstance) -> dict[object, list[Fact]]:
        by_concept: dict[object, list[Fact]] = {}
        for fact in (*instance.facts, *instance.tuple_facts):
            by_concept.setdefault(fact.concept, []).append(fact)
        return by_concept

    @classmethod
    def _variable_match_cache_key(cls, var_def: FactVariableDefinition) -> tuple[Any, ...]:
        return (
            var_def.concept_filter,
            var_def.nils,
            var_def.period_filter,
            var_def.dimension_filters,
            var_def.typed_dimension_filters,
            var_def.unit_filter,
            var_def.unit_filter_exclude,
            tuple(cls._xpath_filter_key(xf) for xf in var_def.xpath_filters),
            tuple(cls._boolean_filter_key(bf) for bf in var_def.boolean_filters),
            tuple(cls._filter_resource_key(resource) for resource in var_def.filter_resources),
        )

    @staticmethod
    def _filter_resource_key(resource: Any) -> tuple[Any, ...]:
        return (
            resource.namespace,
            resource.local_name,
            tuple(sorted(resource.attributes.items())),
            resource.test_xpath,
            resource.variable,
            resource.match_any,
            resource.cover,
            resource.complement,
            resource.aspects,
            resource.qnames,
            resource.qname_expressions,
        )

    @staticmethod
    def _xpath_filter_key(xf: XPathFilterDefinition) -> tuple[Any, ...]:
        return (xf.xpath_expr, tuple(sorted((xf.namespaces or {}).items())))

    @classmethod
    def _boolean_filter_key(cls, bf: BooleanFilterDefinition) -> tuple[Any, ...]:
        return (
            bf.filter_type,
            bf.complement,
            tuple(cls._filter_key(child) for child in bf.children),
        )

    @classmethod
    def _filter_key(cls, filter_def: Any) -> tuple[Any, ...]:
        if isinstance(filter_def, DimensionFilter):
            return (
                "dimension",
                filter_def.dimension_qname,
                filter_def.member_qnames,
                filter_def.exclude,
            )
        if isinstance(filter_def, TypedDimensionFilter):
            return (
                "typed-dimension",
                filter_def.dimension_qname,
                filter_def.exclude,
            )
        if isinstance(filter_def, XPathFilterDefinition):
            return ("xpath", *cls._xpath_filter_key(filter_def))
        if isinstance(filter_def, BooleanFilterDefinition):
            return ("boolean", *cls._boolean_filter_key(filter_def))
        return ("unknown", repr(filter_def))

    # ------------------------------------------------------------------
    # Assertion evaluators
    # ------------------------------------------------------------------

    def _evaluate_value_assertion(
        self,
        assertion: ValueAssertionDefinition,
        bindings: Iterable[_VariableBinding],
        instance: XbrlInstance,
    ) -> list[ValidationFinding]:
        """Evaluate @test XPath for each binding tuple."""
        findings: list[ValidationFinding] = []
        if not assertion.test_xpath:
            return findings

        pending_publish: list[ValidationFinding] = []
        successful_non_fallback_trails: set[tuple[Any, ...]] = set()
        for resolved_binding in bindings:
            binding = resolved_binding.fact_binding
            if resolved_binding.error is not None:
                self._append_and_maybe_publish(
                    findings,
                    pending_publish,
                    self._finding_for_assertion(
                        assertion,
                        status=ValidationStatus.FAIL,
                        default_message=f"XPath evaluation failed: {resolved_binding.error}",
                        rule_id=_xpath_error_code(resolved_binding.error),
                        binding=binding,
                        instance=instance,
                    ),
                )
                continue
            general_values = dict(resolved_binding.general_values)
            general_values.update(
                self._resolve_parameter_values(
                    assertion.parameters,
                    binding,
                    instance,
                    namespaces=assertion.namespaces,
                    existing=general_values,
                )
            )
            if not self._assertion_preconditions_pass(
                assertion,
                binding,
                instance,
                general_values=general_values,
            ):
                continue
            trail_key = self._binding_trail_key(binding)
            if resolved_binding.uses_fallback and trail_key in successful_non_fallback_trails:
                continue
            if self._value_assertion_not_evaluated(assertion, binding):
                self._append_and_maybe_publish(
                    findings,
                    pending_publish,
                    self._finding_for_assertion(
                        assertion,
                        status=ValidationStatus.NOT_EVALUATED,
                        default_message=(
                            f"Value assertion '{assertion.assertion_id}' not evaluated: "
                            "no matching facts found for the required operands"
                        ),
                        binding=binding,
                        instance=instance,
                    ),
                )
                continue
            type_error_code = self._simple_comparison_type_error(assertion, binding)
            if type_error_code is not None:
                self._append_and_maybe_publish(
                    findings,
                    pending_publish,
                    self._finding_for_assertion(
                        assertion,
                        status=ValidationStatus.FAIL,
                        default_message=(
                            f"XPath evaluation failed: incompatible item types in "
                            f"value assertion '{assertion.assertion_id}'"
                        ),
                        rule_id=type_error_code,
                        binding=binding,
                        instance=instance,
                    ),
                )
                continue

            try:
                result = self._eval_xpath(
                    assertion.test_xpath,
                    binding,
                    instance,
                    assertion.namespaces,
                    assertion=assertion,
                    general_values=general_values,
                )
                passed = _to_bool(result)
            except Exception as exc:  # noqa: BLE001
                self._append_and_maybe_publish(
                    findings,
                    pending_publish,
                    self._finding_for_assertion(
                        assertion,
                        status=ValidationStatus.FAIL,
                        default_message=f"XPath evaluation failed: {exc}",
                        rule_id=_xpath_error_code(exc),
                        binding=binding,
                        instance=instance,
                    ),
                )
                continue
            if passed and not resolved_binding.uses_fallback:
                successful_non_fallback_trails.add(trail_key)

            fact = _first_fact(binding)
            self._append_and_maybe_publish(
                findings,
                pending_publish,
                self._finding_for_assertion(
                    assertion,
                    status=ValidationStatus.PASS if passed else ValidationStatus.FAIL,
                    default_message=(
                        f"Value assertion '{assertion.assertion_id}' passed"
                        if passed
                        else f"Value assertion '{assertion.assertion_id}' failed: "
                        f"test expression evaluated to false"
                    ),
                    fact=fact,
                    binding=binding,
                    instance=instance,
                ),
            )
        self._publish_pending(pending_publish)
        return findings

    @staticmethod
    def _value_assertion_not_evaluated(
        assertion: ValueAssertionDefinition,
        binding: dict[str, list[Fact]],
    ) -> bool:
        if not assertion.variables:
            return False

        has_fact = False
        for var_def in assertion.variables:
            facts = binding.get(var_def.variable_name, [])
            if facts:
                has_fact = True
                continue
            if var_def.fallback_value is None:
                return True
        return not has_fact

    def _simple_comparison_type_error(
        self,
        assertion: ValueAssertionDefinition,
        binding: dict[str, list[Fact]],
    ) -> str | None:
        """Catch Formula/XPath comparison type errors elementpath treats loosely.

        The Formula conformance suite expects dynamic ``err:XPTY0004`` results
        when simple value assertions compare facts of unlike XML Schema atomic
        types.  Python's bool/date comparison semantics can otherwise turn some
        of those into plain true/false outcomes before XPath raises.
        """
        match = _SIMPLE_COMPARISON_RE.match(assertion.test_xpath or "")
        if match is None:
            return None
        variable_name, rhs = match.groups()
        rhs_type = _comparison_rhs_type(rhs)
        if rhs_type is None:
            return None
        facts = binding.get(variable_name, ())
        for fact in facts:
            fact_type = self._fact_atomic_type(fact)
            if fact_type is not None and fact_type != rhs_type:
                return "err:XPTY0004"
        return None

    def _fact_atomic_type(self, fact: Fact) -> str | None:
        concept = self._taxonomy.concepts.get(fact.concept)
        if concept is None:
            return None
        return "decimal" if concept_is_numeric(concept) else concept_type_category(concept)

    def _coerce_fact_xpath_value(
        self,
        fact: Fact,
        *,
        namespaces: dict[str, str],
        xpath_expr: str,
    ) -> Any:
        if fact.is_nil:
            return []
        concept = self._taxonomy.concepts.get(fact.concept)
        if concept is None:
            return _coerce_xpath_variable_value(
                fact.value,
                namespaces=namespaces,
                xpath_expr=xpath_expr,
            )
        return _coerce_typed_fact_value(
            fact.value,
            concept,
            namespaces=namespaces,
            xpath_expr=xpath_expr,
        )

    def _evaluate_existence_assertion(
        self,
        assertion: ExistenceAssertionDefinition,
        bindings: Iterable[_VariableBinding],
        instance: XbrlInstance,
    ) -> list[ValidationFinding]:
        """Evaluate the existence test once with variable-set cardinality as context."""
        cardinality = 0
        first_binding: dict[str, list[Fact]] = {}
        general_values: dict[str, Any] = {}
        for resolved_binding in bindings:
            binding = resolved_binding.fact_binding
            if resolved_binding.error is not None:
                finding = self._finding_for_assertion(
                    assertion,
                    status=ValidationStatus.FAIL,
                    default_message=f"XPath evaluation failed: {resolved_binding.error}",
                    rule_id=_xpath_error_code(resolved_binding.error),
                    binding=binding,
                    instance=instance,
                )
                self._publish_findings((finding,))
                return [finding]
            binding_values = dict(resolved_binding.general_values)
            binding_values.update(
                self._resolve_parameter_values(
                    assertion.parameters,
                    binding,
                    instance,
                    namespaces=assertion.namespaces,
                    existing=binding_values,
                )
            )
            if not self._assertion_preconditions_pass(
                assertion,
                binding,
                instance,
                general_values=binding_values,
            ):
                continue
            has_required_binding = not assertion.variables or all(
                binding.get(variable.variable_name) or variable.fallback_value is not None
                for variable in assertion.variables
            )
            has_fact_binding = not assertion.variables or any(binding.values())
            if not has_required_binding or not has_fact_binding:
                continue
            if cardinality == 0:
                first_binding = binding
                general_values = binding_values
            cardinality += 1

        passed = cardinality > 0
        if assertion.test_xpath:
            try:
                result = self._eval_xpath_with_context_item(
                    assertion.test_xpath,
                    cardinality,
                    variables=general_values,
                    namespaces=assertion.namespaces,
                    instance=instance,
                )
                passed = _to_bool(result)
            except Exception as exc:  # noqa: BLE001
                finding = self._finding_for_assertion(
                    assertion,
                    status=ValidationStatus.FAIL,
                    default_message=f"XPath evaluation failed: {exc}",
                    rule_id=_xpath_error_code(exc),
                    binding=first_binding,
                    instance=instance,
                )
                self._publish_findings((finding,))
                return [finding]

        fact = _first_fact(first_binding)
        finding = self._finding_for_assertion(
            assertion,
            status=ValidationStatus.PASS if passed else ValidationStatus.FAIL,
            default_message=(
                f"Existence assertion '{assertion.assertion_id}' passed"
                if passed
                else f"Existence assertion '{assertion.assertion_id}' failed: "
                f"cardinality={cardinality}"
            ),
            fact=fact,
            binding=first_binding,
            instance=instance,
            message_variables={
                **general_values,
                "ea:test-expression": assertion.test_xpath or "",
                "__context_item": cardinality,
            },
        )
        self._publish_findings((finding,))
        return [finding]

    def _eval_xpath_with_context_item(
        self,
        expression: str,
        context_item: Any,
        *,
        variables: dict[str, Any],
        namespaces: dict[str, str],
        instance: XbrlInstance,
    ) -> list[Any]:
        import elementpath  # type: ignore[import-untyped]

        set_evaluation_context(
            {
                "_all_facts": instance.facts,
                "_instance": instance,
                "_taxonomy": self._taxonomy,
                "_formula_relationships": self._current_formula_relationships,
                "_custom_functions": self._taxonomy.custom_functions,
            }
        )
        token = self._get_xpath_token(expression, namespaces)
        try:
            context = elementpath.XPathContext(
                root=None,
                item=context_item,
                variables=variables,
            )
            return list(token.select(context))
        finally:
            clear_evaluation_context()

    def _assertion_preconditions_pass(
        self,
        assertion: FormulaAssertion,
        binding: dict[str, list[Fact]],
        instance: XbrlInstance,
        *,
        general_values: dict[str, Any],
    ) -> bool:
        for precondition in assertion.preconditions:
            try:
                result = self._eval_xpath(
                    precondition.test_xpath,
                    binding,
                    instance,
                    precondition.namespaces or assertion.namespaces,
                    assertion=assertion,
                    general_values=general_values,
                )
                if not _to_bool(result):
                    return False
            except Exception:  # noqa: BLE001
                return False
        return True

    def _evaluate_consistency_assertion(
        self,
        assertion: ConsistencyAssertionDefinition,
        bindings: Iterable[_VariableBinding],
        instance: XbrlInstance,
    ) -> list[ValidationFinding]:
        """Evaluate linked output formulas and compare them with aspect-matched facts."""
        if assertion.formula_ids:
            return self._evaluate_linked_consistency_assertion(assertion, instance)

        # Preserve support for programmatically-created legacy assertions whose
        # expression and variables live directly on the assertion resource.
        findings: list[ValidationFinding] = []
        if not assertion.formula_xpath:
            return findings

        pending_publish: list[ValidationFinding] = []
        for resolved_binding in bindings:
            binding = resolved_binding.fact_binding
            fact = _first_fact(binding)
            if fact is None:
                continue
            try:
                computed = self._eval_xpath(
                    assertion.formula_xpath,
                    binding,
                    instance,
                    assertion.namespaces,
                    assertion=assertion,
                    general_values=resolved_binding.general_values,
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

            self._append_and_maybe_publish(
                findings,
                pending_publish,
                self._finding_for_assertion(
                    assertion,
                    status=ValidationStatus.PASS if passes else ValidationStatus.FAIL,
                    default_message=(
                        f"Consistency assertion '{assertion.assertion_id}' passed"
                        if passes
                        else f"Consistency assertion '{assertion.assertion_id}' failed: "
                        f"computed={computed_val}, actual={actual_val}, diff={difference}"
                    ),
                    fact=fact,
                    binding=binding,
                    instance=instance,
                ),
            )
        self._publish_pending(pending_publish)
        return findings

    def _evaluate_linked_consistency_assertion(
        self,
        assertion: ConsistencyAssertionDefinition,
        instance: XbrlInstance,
    ) -> list[ValidationFinding]:
        formulas_by_id = {
            formula.formula_id: formula
            for formula in self._taxonomy.formula_assertion_set.output_formulas
        }
        facts_by_concept = self._facts_by_concept(instance)
        canonical_contexts = canonical_context_refs_by_s_equal(instance, self._taxonomy)
        canonical_units = canonical_unit_refs_by_structure(instance)
        findings: list[ValidationFinding] = []
        pending_publish: list[ValidationFinding] = []

        for formula_id in assertion.formula_ids:
            formula = formulas_by_id.get(formula_id)
            if formula is None or not formula.value_xpath.strip():
                continue
            raw_bindings = self._bind_variables(
                formula,  # type: ignore[arg-type]
                instance,
                facts_by_concept=facts_by_concept,
            )
            for resolved in self._implicit_formula_bindings(formula, raw_bindings, instance):
                if resolved.error is not None:
                    continue
                binding = resolved.fact_binding
                source_fact = self._formula_source_fact(formula, binding)
                if source_fact is None:
                    continue

                general_values = dict(resolved.general_values)
                general_values.update(
                    self._resolve_parameter_values(
                        formula.parameters,
                        binding,
                        instance,
                        namespaces=formula.namespaces,
                        existing=general_values,
                    )
                )
                if not self._formula_preconditions_pass(
                    formula,
                    binding,
                    instance,
                    general_values=general_values,
                ):
                    continue

                try:
                    computed_result = self._eval_xpath(
                        formula.value_xpath,
                        binding,
                        instance,
                        formula.namespaces,
                        assertion=formula,  # type: ignore[arg-type]
                        general_values=general_values,
                    )
                except Exception:  # noqa: BLE001
                    continue

                computed_items = (
                    computed_result if isinstance(computed_result, list) else [computed_result]
                )
                computed_nil = not computed_items
                computed = computed_items[0] if computed_items else None
                output_concept = self._formula_output_concept(formula, source_fact)
                candidates = [
                    fact
                    for fact in instance.facts
                    if not fact.is_nil
                    and fact.concept == output_concept
                    and canonical_contexts.get(fact.context_ref, fact.context_ref)
                    == canonical_contexts.get(source_fact.context_ref, source_fact.context_ref)
                    and canonical_units.get(fact.unit_ref or "", fact.unit_ref or "")
                    == canonical_units.get(source_fact.unit_ref or "", source_fact.unit_ref or "")
                ]

                if not candidates:
                    if not assertion.strict:
                        continue
                    passed = computed_nil
                    self._append_and_maybe_publish(
                        findings,
                        pending_publish,
                        self._finding_for_assertion(
                            assertion,
                            status=ValidationStatus.PASS if passed else ValidationStatus.FAIL,
                            default_message=(
                                f"Consistency assertion '{assertion.assertion_id}' passed"
                                if passed
                                else f"Consistency assertion '{assertion.assertion_id}' failed: "
                                "no aspect-matched reported fact"
                            ),
                            fact=source_fact,
                            binding=binding,
                            instance=instance,
                        ),
                    )
                    continue

                for actual_fact in candidates:
                    passed = False
                    if not computed_nil:
                        passed = self._consistency_values_match(
                            assertion,
                            formula,
                            computed,
                            actual_fact,
                            binding,
                            instance,
                            general_values=general_values,
                        )
                        if passed is None:
                            continue
                    self._append_and_maybe_publish(
                        findings,
                        pending_publish,
                        self._finding_for_assertion(
                            assertion,
                            status=ValidationStatus.PASS if passed else ValidationStatus.FAIL,
                            default_message=(
                                f"Consistency assertion '{assertion.assertion_id}' passed"
                                if passed
                                else f"Consistency assertion '{assertion.assertion_id}' failed: "
                                f"computed={computed!s}, actual={actual_fact.value}"
                            ),
                            fact=actual_fact,
                            binding=binding,
                            instance=instance,
                        ),
                    )

        self._publish_pending(pending_publish)
        return findings

    def _implicit_formula_bindings(
        self,
        formula: FormulaAssertion | FormulaOutputDefinition,
        bindings: Iterable[_VariableBinding],
        instance: XbrlInstance,
    ) -> Iterator[_VariableBinding]:
        """Apply Formula implicit filtering to raw Cartesian variable bindings."""
        definitions = {variable.variable_name: variable for variable in formula.variables}
        filtered_bindings: list[_VariableBinding] = []
        for resolved in bindings:
            if resolved.error is not None or not formula.implicit_filtering:
                filtered_bindings.append(resolved)
                continue
            binding = {name: list(facts) for name, facts in resolved.fact_binding.items()}
            anchors = [
                (name, facts[0])
                for name, facts in binding.items()
                if facts and not definitions[name].bind_as_sequence
            ]
            compatible = True
            for index, (left_name, left_fact) in enumerate(anchors):
                for right_name, right_fact in anchors[index + 1 :]:
                    if not self._facts_match_uncovered_aspects(
                        left_fact,
                        definitions[left_name],
                        right_fact,
                        definitions[right_name],
                        instance,
                        aspect_model=formula.aspect_model,
                        equality_tests=getattr(formula, "typed_dimension_equality_tests", ()),
                    ):
                        compatible = False
                        break
                if not compatible:
                    break
            if not compatible:
                continue

            if anchors:
                source_fact = self._formula_source_fact(formula, binding)
                anchor_name, anchor_fact = next(
                    ((name, fact) for name, fact in anchors if source_fact is fact),
                    anchors[0],
                )
                for name, facts in binding.items():
                    definition = definitions[name]
                    if not definition.bind_as_sequence or not facts:
                        continue
                    filtered_facts = self._filter_sequence_dimension_members(
                        anchor_fact,
                        facts,
                        definition,
                        instance,
                    )
                    binding[name] = [
                        fact
                        for fact in filtered_facts
                        if self._facts_match_uncovered_aspects(
                            anchor_fact,
                            definitions[anchor_name],
                            fact,
                            definition,
                            instance,
                            aspect_model=formula.aspect_model,
                            equality_tests=getattr(formula, "typed_dimension_equality_tests", ()),
                        )
                    ]
                    if not binding[name] and definition.fallback_value is None:
                        compatible = False
                        break
            if not compatible:
                continue
            uses_filtered_fallback = resolved.uses_fallback or any(
                not binding.get(name) and definition.fallback_value is not None
                for name, definition in definitions.items()
            )
            if formula.general_variables and binding != resolved.fact_binding:
                for general_values, uses_fallback, error in self._resolve_general_variable_bindings(
                    formula,  # type: ignore[arg-type]
                    binding,
                    instance,
                ):
                    filtered_bindings.append(
                        _VariableBinding(
                            fact_binding=binding,
                            general_values=general_values,
                            uses_fallback=uses_filtered_fallback or uses_fallback,
                            error=error,
                        )
                    )
                continue
            filtered_bindings.append(
                _VariableBinding(
                    fact_binding=binding,
                    general_values=resolved.general_values,
                    uses_fallback=uses_filtered_fallback,
                    error=resolved.error,
                )
            )

        yielded_signatures: set[tuple[Any, ...]] = set()
        for resolved in filtered_bindings:
            if resolved.uses_fallback and any(
                candidate.error is None
                and self._binding_strictly_extends(
                    candidate.fact_binding,
                    resolved.fact_binding,
                    definitions,
                    instance,
                )
                for candidate in filtered_bindings
            ):
                continue
            signature = self._binding_signature(resolved)
            if signature in yielded_signatures:
                continue
            yielded_signatures.add(signature)
            yield resolved

    def _binding_strictly_extends(
        self,
        candidate: dict[str, list[Fact]],
        fallback_binding: dict[str, list[Fact]],
        definitions: dict[str, FactVariableDefinition],
        instance: XbrlInstance,
    ) -> bool:
        """Return whether candidate supersedes a fallback in one aspect group."""
        strictly_extended = False
        preserves_bound_facts = True
        for name, facts in fallback_binding.items():
            candidate_facts = candidate.get(name, ())
            if facts and list(candidate_facts) != facts:
                preserves_bound_facts = False
                break
            if not facts and candidate_facts:
                strictly_extended = True
        if preserves_bound_facts and strictly_extended:
            return True

        candidate_fallbacks = {
            name
            for name, definition in definitions.items()
            if definition.fallback_value is not None and not candidate.get(name)
        }
        binding_fallbacks = {
            name
            for name, definition in definitions.items()
            if definition.fallback_value is not None and not fallback_binding.get(name)
        }
        if not candidate_fallbacks < binding_fallbacks:
            return False

        fact_variable_names = set(definitions)
        dependent_filter_variables = {
            name
            for name, definition in definitions.items()
            if any(
                _xpath_variable_names(xpath_filter.xpath_expr) & fact_variable_names
                for xpath_filter in definition.xpath_filters
            )
            or any(
                resource.local_name == "conceptRelation" and resource.variable
                for resource in definition.filter_resources
            )
        }
        if not dependent_filter_variables:
            return False
        for name, facts in fallback_binding.items():
            candidate_facts = candidate.get(name, ())
            if facts and list(candidate_facts) != facts and name not in dependent_filter_variables:
                return False

        candidate_anchor = next(
            ((name, facts[0]) for name, facts in candidate.items() if facts),
            None,
        )
        fallback_anchor = next(
            ((name, facts[0]) for name, facts in fallback_binding.items() if facts),
            None,
        )
        if fallback_anchor is None:
            return candidate_anchor is not None
        if candidate_anchor is None:
            return False
        _, candidate_fact = candidate_anchor
        _, fallback_fact = fallback_anchor
        canonical_contexts = canonical_context_refs_by_s_equal(instance, self._taxonomy)
        return canonical_contexts.get(
            candidate_fact.context_ref, candidate_fact.context_ref
        ) == canonical_contexts.get(fallback_fact.context_ref, fallback_fact.context_ref)

    def _filter_sequence_dimension_members(
        self,
        anchor_fact: Fact,
        sequence: list[Fact],
        variable: FactVariableDefinition,
        instance: XbrlInstance,
    ) -> list[Fact]:
        """Apply the common dimension-member child-axis sequence pattern."""
        anchor_context = instance.contexts.get(anchor_fact.context_ref)
        if anchor_context is None:
            return sequence
        filtered = sequence
        domain_member_arcrole = "http://xbrl.org/int/dim/arcrole/domain-member"
        for dimension_filter in variable.dimension_filters:
            if dimension_filter.member_axis is None or dimension_filter.member_qnames:
                continue
            source_member = anchor_context.dimensions.get(dimension_filter.dimension_qname)
            if source_member is None:
                continue
            child_members = {
                arc.target
                for arcs in self._taxonomy.definition.values()
                for arc in arcs
                if arc.arcrole == domain_member_arcrole and arc.source == source_member
            }
            if not child_members:
                return []
            filtered = [
                fact
                for fact in filtered
                if (
                    (context := instance.contexts.get(fact.context_ref)) is not None
                    and context.dimensions.get(dimension_filter.dimension_qname) in child_members
                )
            ]
        return filtered

    @staticmethod
    def _covered_formula_aspects(variable: FactVariableDefinition) -> tuple[set[str], set[object]]:
        covered: set[str] = set()
        covered_dimensions: set[object] = set()
        if variable.concept_filter is not None:
            covered.add("concept")
        for resource in variable.filter_resources:
            if resource.cover is False:
                continue
            local_name = resource.local_name.lower()
            if local_name == "aspectcover":
                normalized_aspects = {aspect.lower() for aspect in resource.aspects}
                if "all" in normalized_aspects:
                    covered.update(
                        {"concept", "entity", "period", "unit", "dimensions", "location"}
                    )
                if "concept" in normalized_aspects:
                    covered.add("concept")
                if "entity-identifier" in normalized_aspects:
                    covered.add("entity")
                if "period" in normalized_aspects:
                    covered.add("period")
                if "unit" in normalized_aspects:
                    covered.add("unit")
                if "location" in normalized_aspects:
                    covered.add("location")
                if "dimensions" in normalized_aspects:
                    covered.add("dimensions")
                if any(
                    "segment" in aspect or "scenario" in aspect for aspect in normalized_aspects
                ):
                    covered.add("remainder")
                if any("segment" in aspect for aspect in normalized_aspects):
                    covered.add("segment")
                if any("scenario" in aspect for aspect in normalized_aspects):
                    covered.add("scenario")
                covered_dimensions.update(resource.qnames)
                for expression in resource.qname_expressions:
                    match = re.fullmatch(
                        r"\s*QName\(\s*['\"]([^'\"]+)['\"]\s*,\s*['\"](?:[^:'\"]+:)?([^'\"]+)['\"]\s*\)\s*",
                        expression,
                    )
                    if match:
                        covered_dimensions.add(QName(match.group(1), match.group(2)))
                continue
            if "concept" in local_name:
                covered.add("concept")
            elif any(
                token in local_name for token in ("ancestor", "parent", "sibling", "location")
            ):
                covered.add("location")
            elif (
                resource.namespace == "http://xbrl.org/2008/filter/period" or "period" in local_name
            ):
                covered.add("period")
            elif "entity" in local_name or "identifier" in local_name:
                covered.add("entity")
            elif "unit" in local_name or "measure" in local_name:
                covered.add("unit")
            elif "segment" in local_name:
                covered.add("segment")
            elif "scenario" in local_name:
                covered.add("scenario")
            elif "dimension" in local_name and resource.qnames:
                covered_dimensions.add(resource.qnames[0])
        uncovered_resource_dimensions = {
            resource.qnames[0]
            for resource in variable.filter_resources
            if resource.cover is False
            and "dimension" in resource.local_name.lower()
            and resource.qnames
        }
        covered_dimensions.update(
            dimension_filter.dimension_qname
            for dimension_filter in variable.dimension_filters
            if dimension_filter.dimension_qname not in uncovered_resource_dimensions
        )
        covered_dimensions.update(
            typed_filter.dimension_qname
            for typed_filter in variable.typed_dimension_filters
            if typed_filter.dimension_qname not in uncovered_resource_dimensions
        )
        return covered, covered_dimensions

    def _facts_match_uncovered_aspects(
        self,
        left: Fact,
        left_variable: FactVariableDefinition,
        right: Fact,
        right_variable: FactVariableDefinition,
        instance: XbrlInstance,
        *,
        aspect_model: str | None,
        equality_tests: tuple[str, ...] = (),
    ) -> bool:
        left_covered, left_dimensions = self._covered_formula_aspects(left_variable)
        right_covered, right_dimensions = self._covered_formula_aspects(right_variable)
        if "concept" not in left_covered | right_covered and left.concept != right.concept:
            return False
        if "location" not in left_covered | right_covered and left.tuple_path != right.tuple_path:
            return False
        left_context = instance.contexts.get(left.context_ref)
        right_context = instance.contexts.get(right.context_ref)
        if left_context is None or right_context is None:
            return left.context_ref == right.context_ref
        if (
            "entity" not in left_covered | right_covered
            and left_context.entity != right_context.entity
        ):
            return False
        if (
            "period" not in left_covered | right_covered
            and left_context.period != right_context.period
        ):
            return False
        if left.context_ref != right.context_ref:
            covered = left_covered | right_covered
            if "segment" not in covered and "remainder" not in covered:
                segment_matches = (
                    _facts_have_matching_complete_segment
                    if aspect_model == "non-dimensional"
                    else _facts_have_matching_non_xdt_segment
                )
                if not segment_matches(left, right, instance, self._taxonomy):
                    return False
            if "scenario" not in covered and "remainder" not in covered:
                scenario_matches = (
                    _facts_have_matching_complete_scenario
                    if aspect_model == "non-dimensional"
                    else _facts_have_matching_non_xdt_scenario
                )
                if not scenario_matches(left, right, instance, self._taxonomy):
                    return False
        dimensions = (
            set(left_context.dimensions)
            | set(right_context.dimensions)
            | set(left_context.typed_dimensions)
            | set(right_context.typed_dimensions)
        )
        for dimension in dimensions - left_dimensions - right_dimensions:
            if left_context.dimensions.get(dimension) != right_context.dimensions.get(dimension):
                return False
            if not _typed_dimension_values_equal(
                left_context,
                right_context,
                dimension,
                equality_tests=equality_tests,
            ):
                return False
        if "unit" not in left_covered | right_covered:
            canonical_units = canonical_unit_refs_by_structure(instance)
            if canonical_units.get(left.unit_ref or "", left.unit_ref or "") != canonical_units.get(
                right.unit_ref or "", right.unit_ref or ""
            ):
                return False
        return True

    def _facts_match_relative_filter_aspects(
        self,
        candidate: Fact,
        candidate_variable: FactVariableDefinition,
        reference: Fact,
        instance: XbrlInstance,
        *,
        aspect_model: str | None,
        equality_tests: tuple[str, ...] = (),
    ) -> bool:
        """Match the candidate's uncovered aspects against a reference fact."""
        covered, covered_dimensions = self._covered_formula_aspects(candidate_variable)
        if "concept" not in covered and candidate.concept != reference.concept:
            return False
        if "location" not in covered and candidate.tuple_path != reference.tuple_path:
            return False

        candidate_context = instance.contexts.get(candidate.context_ref)
        reference_context = instance.contexts.get(reference.context_ref)
        if candidate_context is None or reference_context is None:
            return candidate.context_ref == reference.context_ref
        if "entity" not in covered and candidate_context.entity != reference_context.entity:
            return False
        if "period" not in covered and candidate_context.period != reference_context.period:
            return False

        if "remainder" not in covered:
            if aspect_model == "non-dimensional":
                candidate_key = context_s_equal_key(
                    candidate_context, dict(self._taxonomy.element_defaults)
                )
                reference_key = context_s_equal_key(
                    reference_context, dict(self._taxonomy.element_defaults)
                )
                if candidate_key[4:] != reference_key[4:]:
                    return False
            elif not (
                _facts_have_matching_non_xdt_segment(candidate, reference, instance, self._taxonomy)
                and _facts_have_matching_non_xdt_scenario(
                    candidate, reference, instance, self._taxonomy
                )
            ):
                return False

        if aspect_model != "non-dimensional":
            candidate_dimensions = set(candidate_context.dimensions) | set(
                candidate_context.typed_dimensions
            )
            applicable_dimensions = {
                dimension
                for hypercube in self._taxonomy.hypercubes
                if hypercube.arcrole == "all" and candidate.concept in hypercube.primary_items
                for dimension in hypercube.dimensions
            }
            default_members = {
                dimension: model.default_member
                for dimension, model in self._taxonomy.dimensions.items()
                if model.default_member is not None
            }
            candidate_dimensions.update(applicable_dimensions & default_members.keys())
            for dimension in candidate_dimensions - covered_dimensions:
                candidate_typed = dimension in candidate_context.typed_dimensions
                reference_typed = dimension in reference_context.typed_dimensions
                if candidate_typed or reference_typed:
                    if not (candidate_typed and reference_typed):
                        return False
                    if not _typed_dimension_values_equal(
                        candidate_context,
                        reference_context,
                        dimension,
                        equality_tests=equality_tests,
                        schema_element_types=self._schema_element_types,
                        schema_attribute_types=self._schema_attribute_types,
                    ):
                        return False
                    continue
                candidate_member = candidate_context.dimensions.get(
                    dimension, default_members.get(dimension)
                )
                reference_member = reference_context.dimensions.get(
                    dimension, default_members.get(dimension)
                )
                if candidate_member != reference_member:
                    return False

        if "unit" not in covered:
            canonical_units = canonical_unit_refs_by_structure(instance)
            if canonical_units.get(
                candidate.unit_ref or "", candidate.unit_ref or ""
            ) != canonical_units.get(reference.unit_ref or "", reference.unit_ref or ""):
                return False
        return True

    @staticmethod
    def _formula_source_fact(
        formula: FormulaAssertion | FormulaOutputDefinition,
        binding: dict[str, list[Fact]],
    ) -> Fact | None:
        source = getattr(formula, "source", None)
        if source and source not in {"formula:uncovered", "formula:uncovered-aspect"}:
            facts = binding.get(source, ())
            if facts:
                return facts[0]
        return _first_fact(binding)

    @staticmethod
    def _formula_output_concept(
        formula: FormulaOutputDefinition,
        source_fact: Fact,
    ) -> object:
        for rule in formula.aspect_rules:
            if rule.aspect == "concept" and rule.qname is not None:
                return rule.qname
        return source_fact.concept

    def _formula_preconditions_pass(
        self,
        formula: FormulaOutputDefinition,
        binding: dict[str, list[Fact]],
        instance: XbrlInstance,
        *,
        general_values: dict[str, Any],
    ) -> bool:
        for precondition in formula.preconditions:
            try:
                result = self._eval_xpath(
                    precondition.test_xpath,
                    binding,
                    instance,
                    precondition.namespaces or formula.namespaces,
                    assertion=formula,  # type: ignore[arg-type]
                    general_values=general_values,
                    fact_bindings_as_elements=True,
                    context_item_is_instance=True,
                )
                if not _to_bool(result):
                    return False
            except Exception:  # noqa: BLE001
                return False
        return True

    def _resolve_parameter_values(
        self,
        parameters: Iterable[Any],
        binding: dict[str, list[Fact]],
        instance: XbrlInstance,
        *,
        namespaces: dict[str, str],
        existing: dict[str, Any],
    ) -> dict[str, Any]:
        values: dict[str, Any] = {}
        for parameter in parameters:
            external_name = parameter.resource_name or parameter.parameter_name
            if external_name in self._external_parameter_values:
                values[parameter.parameter_name] = self._external_parameter_values[external_name]
                continue
            if not parameter.select_xpath:
                continue
            try:
                result = self._eval_xpath(
                    parameter.select_xpath,
                    binding,
                    instance,
                    parameter.namespaces or namespaces,
                    general_values={**existing, **values},
                )
            except Exception:  # noqa: BLE001
                continue
            if isinstance(result, list):
                if not result:
                    continue
                values[parameter.parameter_name] = result[0] if len(result) == 1 else result
            else:
                values[parameter.parameter_name] = result
        return values

    def _consistency_values_match(
        self,
        assertion: ConsistencyAssertionDefinition,
        formula: FormulaOutputDefinition,
        computed: Any,
        actual_fact: Fact,
        binding: dict[str, list[Fact]],
        instance: XbrlInstance,
        *,
        general_values: dict[str, Any],
    ) -> bool | None:
        computed_value = getattr(computed, "value", computed)
        try:
            computed_decimal = Decimal(str(computed_value))
            actual_decimal = Decimal(actual_fact.value)
        except InvalidOperation:
            return str(computed_value) == actual_fact.value

        difference = abs(computed_decimal - actual_decimal)
        assertion_parameters = self._resolve_parameter_values(
            assertion.parameters,
            {"__reported_fact": [actual_fact], **binding},
            instance,
            namespaces=assertion.namespaces,
            existing=general_values,
        )
        evaluation_values = {**general_values, **assertion_parameters}
        absolute_radius = self._consistency_radius(
            assertion.absolute_radius,
            assertion.absolute_radius_xpath,
            actual_fact,
            binding,
            instance,
            assertion.namespaces,
            evaluation_values,
        )
        relative_radius = self._consistency_radius(
            assertion.relative_radius,
            assertion.relative_radius_xpath,
            actual_fact,
            binding,
            instance,
            assertion.namespaces,
            evaluation_values,
        )
        if absolute_radius is not None:
            return difference <= absolute_radius
        if relative_radius is not None:
            return difference <= abs(computed_decimal) * relative_radius

        accuracy = self._formula_numeric_accuracy(
            formula,
            computed_decimal,
            binding,
            instance,
            general_values,
        )
        if accuracy is None:
            return None
        return difference < accuracy if accuracy else difference == 0

    def _consistency_radius(
        self,
        literal: Decimal | None,
        expression: str | None,
        actual_fact: Fact,
        binding: dict[str, list[Fact]],
        instance: XbrlInstance,
        namespaces: dict[str, str],
        general_values: dict[str, Any],
    ) -> Decimal | None:
        if literal is not None:
            return literal
        if not expression:
            return None
        try:
            radius_binding = {"__reported_fact": [actual_fact], **binding}
            result = self._eval_xpath(
                expression,
                radius_binding,
                instance,
                namespaces,
                general_values=general_values,
            )
            if isinstance(result, list):
                if not result:
                    return None
                result = result[0]
            return Decimal(str(getattr(result, "value", result)))
        except Exception:  # noqa: BLE001
            return None

    def _formula_numeric_accuracy(
        self,
        formula: FormulaOutputDefinition,
        value: Decimal,
        binding: dict[str, list[Fact]],
        instance: XbrlInstance,
        general_values: dict[str, Any],
    ) -> Decimal | None:
        expression = formula.decimals_xpath or formula.precision_xpath
        if expression is None:
            return None
        normalized_expression = expression.strip().strip("'\"").upper()
        if normalized_expression == "INF":
            return Decimal(0)
        try:
            result = self._eval_xpath(
                expression,
                binding,
                instance,
                formula.namespaces,
                assertion=formula,  # type: ignore[arg-type]
                general_values=general_values,
            )
            if isinstance(result, list):
                if not result:
                    return None
                result = result[0]
            accuracy_value = int(Decimal(str(getattr(result, "value", result))))
        except Exception:  # noqa: BLE001
            return None
        if formula.precision_xpath is not None:
            if accuracy_value <= 0:
                return None
            exponent = value.copy_abs().adjusted() - accuracy_value + 1 if value else 0
        else:
            exponent = -accuracy_value
        return Decimal("0.5") * (Decimal(10) ** exponent)

    # ------------------------------------------------------------------
    # XPath evaluation helper
    # ------------------------------------------------------------------

    def _eval_xpath(
        self,
        xpath_expr: str,
        binding: dict[str, list[Fact]],
        instance: XbrlInstance,
        namespaces: dict[str, str] | None = None,
        *,
        assertion: FormulaAssertion | FormulaOutputDefinition | None = None,
        general_values: dict[str, Any] | None = None,
        fact_bindings_as_elements: bool = False,
        context_item_is_instance: bool = False,
    ) -> Any:
        """Evaluate an XPath 2.0 expression with the current fact binding."""
        import elementpath  # type: ignore[import-untyped]

        namespaces = {
            **(assertion.namespaces if assertion is not None else {}),
            **(namespaces or {}),
        }
        fact_bindings_as_elements = fact_bindings_as_elements or _expressions_need_fact_nodes(
            (xpath_expr,)
        )

        # Build a variable map: variable_name → Decimal, fallback value, or empty sequence.
        # Decimal values support XPath arithmetic; xfi: functions use the global
        # _eval_context for fact-level metadata.
        #
        # When *fact_bindings_as_elements* is True (output-formula conformance runtime),
        # bind each fact variable to lightweight XBRL-shaped elements so xfi:period($var)
        # can resolve context; atomization still yields typed/plain values for arithmetic.
        variables: dict[str, Any] = {}
        pending_fallbacks: dict[str, str] = {}
        first_fact: Fact | None = None
        xpath_root: Any | None = None
        xpath_elements: dict[int, Any] = {}
        xpath_element_types: dict[int, str] = {}
        if fact_bindings_as_elements:
            xpath_root = etree.Element(
                f"{{{XBRLI_NS}}}xbrl" if context_item_is_instance else "formula-instance"
            )
            if context_item_is_instance:
                for context_id in instance.contexts:
                    etree.SubElement(
                        xpath_root,
                        f"{{{XBRLI_NS}}}context",
                        id=context_id,
                    )
            bound_fact_ids = {id(fact) for facts in binding.values() for fact in facts}
            ordered_facts = [fact for fact in instance.facts if id(fact) in bound_fact_ids]
            ordered_ids = {id(fact) for fact in ordered_facts}
            ordered_facts.extend(
                fact for facts in binding.values() for fact in facts if id(fact) not in ordered_ids
            )
            for fact in ordered_facts:
                concept = self._taxonomy.concepts.get(fact.concept)
                default_value = (
                    concept.schema_default_value
                    if concept is not None and not fact.is_nil and not fact.value
                    else None
                )
                element = _fact_to_message_element(
                    fact,
                    default_value=default_value,
                    xsd_type=(
                        _fact_node_xsd_type(concept, fact.value)
                        if concept is not None
                        else None
                    ),
                )
                xpath_root.append(element)
                xpath_elements[id(fact)] = element
                xsd_type = (
                    _fact_node_xsd_type(concept, fact.value)
                    if concept is not None
                    else None
                )
                if xsd_type is not None:
                    xpath_element_types[id(element)] = xsd_type
            xpath_root, typed_nodes = _typed_xpath_tree(xpath_root, xpath_element_types)
            xpath_elements = {
                fact_id: typed_nodes[id(element)]
                for fact_id, element in xpath_elements.items()
            }
        fallback_by_name = (
            {
                var_def.variable_name: var_def.fallback_value
                for var_def in assertion.variables
                if var_def.fallback_value is not None
            }
            if assertion is not None
            else {}
        )
        for var_name, facts in binding.items():
            if facts:
                if fact_bindings_as_elements:
                    if len(facts) > 1:
                        variables[var_name] = [xpath_elements[id(fact)] for fact in facts]
                    else:
                        variables[var_name] = xpath_elements[id(facts[0])]
                elif len(facts) > 1:
                    variables[var_name] = [
                        self._coerce_fact_xpath_value(
                            fact,
                            namespaces=namespaces or {},
                            xpath_expr=xpath_expr,
                        )
                        for fact in facts
                    ]
                else:
                    variables[var_name] = self._coerce_fact_xpath_value(
                        facts[0],
                        namespaces=namespaces or {},
                        xpath_expr=xpath_expr,
                    )
                if first_fact is None:
                    first_fact = facts[0]
            elif var_name in fallback_by_name:
                variables[var_name] = []
                pending_fallbacks[var_name] = fallback_by_name[var_name]
            else:
                variables[var_name] = Decimal(0)
        if general_values is not None:
            for name, value in general_values.items():
                variables.setdefault(name, value)
        elif assertion is not None:
            variables.update(
                self._general_variable_xpath_values(
                    assertion,
                    binding,
                    instance,
                    namespaces=namespaces or {},
                )
            )
        for name, value in self._general_variable_values.items():
            variables.setdefault(name, _coerce_fallback_value(value))
        variables = _with_equivalent_variable_prefixes(variables, namespaces or {})
        for name, fallback_xpath in pending_fallbacks.items():
            variables[name] = self._evaluate_fallback_xpath(
                fallback_xpath,
                variables,
                namespaces or {},
            )
        variables = _with_equivalent_variable_prefixes(variables, namespaces or {})

        # Populate the thread-local xfi: evaluation context
        ctx_obj = None
        unit_obj = None
        if first_fact:
            ctx_obj = instance.contexts.get(first_fact.context_ref)
            if first_fact.unit_ref:
                unit_obj = instance.units.get(first_fact.unit_ref)

        set_evaluation_context(
            {
                "_all_facts": instance.facts,
                "_current_fact": first_fact,
                "_context": ctx_obj,
                "_unit": unit_obj,
                "_instance": instance,
                "_taxonomy": self._taxonomy,
                "_formula_relationships": self._current_formula_relationships,
                "_custom_functions": self._taxonomy.custom_functions,
            }
        )

        # Use the context item as a Decimal (for arithmetic) when available;
        # fall back to True as a harmless sentinel so elementpath stays happy.
        if context_item_is_instance and xpath_root is not None:
            context_item: Any = xpath_root
        elif first_fact is None:
            context_item: Any = True
        elif fact_bindings_as_elements:
            context_item = xpath_elements[id(first_fact)]
        else:
            context_item = _coerce_value(first_fact.value)

        xpath_base_uri = getattr(assertion, "xpath_base_uri", None)
        token = self._get_xpath_token(xpath_expr, namespaces, base_uri=xpath_base_uri)
        try:
            ctx = elementpath.XPathContext(
                root=xpath_root,
                item=context_item,
                variables=variables,
                documents=_xpath_literal_documents(xpath_expr, xpath_base_uri),
            )
            result = list(token.select(ctx))
        finally:
            clear_evaluation_context()

        return result

    def _evaluate_fallback_xpath(
        self,
        expression: str,
        variables: dict[str, Any],
        namespaces: dict[str, str],
    ) -> Any:
        """Evaluate a fact-variable fallback as an XPath expression."""
        import elementpath  # type: ignore[import-untyped]

        try:
            token = self._get_xpath_token(expression, namespaces)
            context = elementpath.XPathContext(
                root=None,
                item=True,
                variables=variables,
            )
            result = list(token.select(context))
        except Exception:  # noqa: BLE001
            return _coerce_fallback_value(expression)
        if len(result) == 1:
            return result[0]
        return result

    def _general_variable_xpath_values(
        self,
        assertion: FormulaAssertion,
        binding: dict[str, list[Fact]],
        instance: XbrlInstance,
        *,
        namespaces: dict[str, str],
    ) -> dict[str, Any]:
        values: dict[str, Any] = {}
        eval_variables: dict[str, Any] = {}
        first_fact = _first_fact(binding)
        for fact_name, facts in binding.items():
            if not facts:
                continue
            if len(facts) == 1:
                eval_variables[fact_name] = self._coerce_fact_xpath_value(
                    facts[0],
                    namespaces=namespaces,
                    xpath_expr="",
                )
            else:
                eval_variables[fact_name] = [
                    self._coerce_fact_xpath_value(
                        fact,
                        namespaces=namespaces,
                        xpath_expr="",
                    )
                    for fact in facts
                ]

        for variable in assertion.general_variables:
            if variable.variable_name in self._general_variable_values:
                values[variable.variable_name] = _coerce_fallback_value(
                    self._general_variable_values[variable.variable_name]
                )
                eval_variables[variable.variable_name] = values[variable.variable_name]
                continue

            selected = self._evaluate_general_variable_select(
                variable.select_xpath,
                variables=eval_variables,
                instance=instance,
                namespaces=variable.namespaces or namespaces,
                first_fact=first_fact,
                base_uri=getattr(assertion, "xpath_base_uri", None),
            )
            if selected is not None:
                if variable.bind_as_sequence:
                    values[variable.variable_name] = selected
                elif isinstance(selected, list):
                    values[variable.variable_name] = selected[0] if selected else []
                else:
                    values[variable.variable_name] = selected
                eval_variables[variable.variable_name] = values[variable.variable_name]
            elif variable.fallback_value is not None:
                values[variable.variable_name] = _coerce_fallback_value(variable.fallback_value)
                eval_variables[variable.variable_name] = values[variable.variable_name]
        return values

    def _evaluate_general_variable_select(
        self,
        select_xpath: str,
        *,
        variables: dict[str, Any],
        instance: XbrlInstance,
        namespaces: dict[str, str],
        first_fact: Fact | None,
        base_uri: str | None = None,
    ) -> Any | None:
        import elementpath  # type: ignore[import-untyped]

        if not select_xpath.strip():
            return None
        if first_fact is None and select_xpath.strip() == ".":
            return None
        xpath_root = _instance_xpath_root(instance) if "/" in select_xpath else None
        ctx_obj = None
        unit_obj = None
        if first_fact is not None:
            ctx_obj = instance.contexts.get(first_fact.context_ref)
            if first_fact.unit_ref:
                unit_obj = instance.units.get(first_fact.unit_ref)

        set_evaluation_context(
            {
                "_all_facts": instance.facts,
                "_current_fact": first_fact,
                "_context": ctx_obj,
                "_unit": unit_obj,
                "_instance": instance,
                "_taxonomy": self._taxonomy,
                "_formula_relationships": self._current_formula_relationships,
                "_custom_functions": self._taxonomy.custom_functions,
            }
        )
        token = self._get_xpath_token(select_xpath, namespaces, base_uri=base_uri)
        try:
            ctx = elementpath.XPathContext(
                root=xpath_root,
                item=(
                    xpath_root
                    if xpath_root is not None
                    else _coerce_value(first_fact.value)
                    if first_fact is not None
                    else True
                ),
                variables=variables,
                documents=_xpath_literal_documents(select_xpath, base_uri),
            )
            return list(token.select(ctx))
        finally:
            clear_evaluation_context()

    def _get_xpath_token(
        self,
        xpath_expr: str,
        namespaces: dict[str, str] | None = None,
        *,
        base_uri: str | None = None,
    ) -> Any:
        xpath_expr = normalize_formula_xpath_expression(xpath_expr)
        namespace_items = tuple(sorted((namespaces or {}).items()))
        cache_key = (namespace_items, xpath_expr, base_uri)
        cached = self._xpath_token_cache.get(cache_key)
        if cached is not None:
            return cached
        parser = build_formula_parser(
            dict(namespace_items),
            custom_functions=self._taxonomy.custom_functions,
            expression_hints=(xpath_expr,),
            base_uri=base_uri,
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


def _cast_external_parameter(parameter: ExternalFormulaParameter) -> Any:
    """Cast an external lexical value to its declared XPath atomic type."""
    datatype = parameter.datatype
    local_name = datatype.rsplit("}", 1)[-1] if datatype.startswith("{") else datatype.split(":")[-1]
    value = parameter.lexical_value
    if local_name == "date":
        from elementpath.datatypes import Date10  # type: ignore[import-untyped]

        return Date10.fromstring(value)
    if local_name == "dateTime":
        from elementpath.datatypes import DateTime10  # type: ignore[import-untyped]

        return DateTime10.fromstring(value)
    if local_name == "boolean":
        return value.strip() in {"true", "1"}
    if local_name in {"decimal", "integer", "float", "double"}:
        number = Decimal(value)
        return int(number) if local_name == "integer" else number
    return value


def _atomic_value_with_fact_identity(value: Any, fact: Fact) -> Any:
    """Attach fact identity to atomic XPath values consumed by xfi functions."""
    if isinstance(value, Decimal):
        return _FactDecimal(value, fact)
    if isinstance(value, str):
        return _FactString(value, fact)
    return value


def _instance_xpath_root(instance: XbrlInstance) -> etree._Element:
    """Build the instance element view used by path-based general variables."""
    root = etree.Element("formula-instance")
    top_level_facts = [
        fact
        for fact in (*instance.facts, *instance.tuple_facts)
        if not fact.tuple_path and fact.source_element_xml is not None
    ]
    for fact in sorted(top_level_facts, key=lambda item: item.position_path):
        try:
            root.append(etree.fromstring(fact.source_element_xml))
        except (etree.XMLSyntaxError, ValueError, TypeError):
            continue
    return root


def _xpath_literal_documents(
    expression: str,
    base_uri: str | None,
) -> dict[str, Any]:
    """Load local documents referenced by literal ``fn:doc`` calls."""
    if base_uri is None:
        return {}
    documents: dict[str, Any] = {}
    for match in re.finditer(r"\bdoc\s*\(\s*(['\"])(.*?)\1\s*\)", expression):
        document_uri, _fragment = urldefrag(urljoin(base_uri, match.group(2)))
        parsed_uri = urlsplit(document_uri)
        if parsed_uri.scheme != "file" or parsed_uri.netloc not in {"", "localhost"}:
            continue
        document_path = Path(unquote(parsed_uri.path))
        if not document_path.is_file():
            continue
        parser = etree.XMLParser(resolve_entities=False, no_network=True)
        document_tree = etree.parse(str(document_path), parser)
        documents[document_uri] = _schema_annotated_xpath_document(
            document_tree,
            document_uri,
        )
    return documents


def _schema_annotated_xpath_document(
    document_tree: etree._ElementTree,
    document_uri: str,
) -> Any:
    """Apply an instance document's local schema annotations to its XPath tree."""
    xsi_namespace = "http://www.w3.org/2001/XMLSchema-instance"
    root = document_tree.getroot()
    root_namespace = etree.QName(root).namespace or ""
    schema_location = root.get(f"{{{xsi_namespace}}}schemaLocation", "").split()
    locations = dict(zip(schema_location[::2], schema_location[1::2], strict=False))
    location = locations.get(root_namespace)
    if location is None and not root_namespace:
        location = root.get(f"{{{xsi_namespace}}}noNamespaceSchemaLocation")
    if not location:
        return document_tree

    schema_uri, _fragment = urldefrag(urljoin(document_uri, location))
    parsed_schema_uri = urlsplit(schema_uri)
    if parsed_schema_uri.scheme != "file" or parsed_schema_uri.netloc not in {"", "localhost"}:
        return document_tree
    schema_path = Path(unquote(parsed_schema_uri.path))
    if not schema_path.is_file():
        return document_tree

    try:
        import xmlschema  # type: ignore[import-untyped]
        from elementpath.tree_builders import get_node_tree  # type: ignore[import-untyped]
        from xmlschema.xpath import XMLSchemaProxy  # type: ignore[import-untyped]

        schema = XMLSchemaProxy(xmlschema.XMLSchema(str(schema_path)))
        document_node = get_node_tree(document_tree, uri=document_uri)
        document_node.apply_schema(schema)
        return document_node
    except Exception:  # noqa: BLE001 - an unusable annotation leaves the document untyped
        return document_tree


def _xpath_error_code(exc: Exception) -> str | None:
    code = getattr(exc, "code", None)
    if isinstance(code, str) and code:
        return code
    return None


def _coerce_fallback_value(raw: str) -> Any:
    """Convert formula fallbackValue text to the XPath variable value."""
    if raw.strip() == "()":
        return []
    return _coerce_value(raw)


def _dependency_ordered_general_variables(assertion: FormulaAssertion) -> tuple[Any, ...]:
    """Order general variables after the general variables they reference.

    Variable-set arcs do not prescribe evaluation order.  Linkbase document
    order therefore cannot be used when one general variable consumes another.
    Cycles retain their original stable order and are handled by normal XPath
    evaluation errors.
    """
    remaining = list(assertion.general_variables)
    general_names = {variable.variable_name for variable in remaining}
    ordered: list[Any] = []
    resolved: set[str] = set()
    while remaining:
        ready = [
            variable
            for variable in remaining
            if not (set(variable.referenced_names) & general_names - resolved)
        ]
        if not ready:
            ordered.extend(remaining)
            break
        for variable in ready:
            ordered.append(variable)
            resolved.add(variable.variable_name)
            remaining.remove(variable)
    return tuple(ordered)


def _dependent_fact_variable_names(
    concept_expressions: tuple[XPathFilterDefinition, ...],
    relation_resources: tuple[Any, ...],
) -> set[str]:
    """Return fact-variable names consumed by dynamic concept filters."""
    dependencies = {
        match
        for xpath_filter in concept_expressions
        for match in re.findall(r"\$([A-Za-z_][\w:.-]*)", xpath_filter.xpath_expr)
    }
    dependencies.update(resource.variable for resource in relation_resources if resource.variable)
    return dependencies


def _xpath_variable_names(expression: str) -> set[str]:
    """Return lexical variable QNames referenced by an XPath expression."""
    return set(re.findall(r"\$([A-Za-z_][\w:.-]*)", expression))


def _expressions_need_fact_nodes(expressions: Iterable[str]) -> bool:
    """Return whether XPath expressions inspect fact nodes instead of atomic values."""
    return any(
        token in expression
        for expression in expressions
        for token in (
            "node-name(",
            "local-name(",
            "namespace-uri(",
            "name(",
            "nilled(",
            "instance of element(",
            "/@",
            " | ",
            " intersect ",
            " except ",
            " union ",
        )
    )


def _expressions_need_fact_identity(expressions: Iterable[str]) -> bool:
    """Return whether xfi functions need atomic values tied to source facts."""
    return any("xfi:" in expression for expression in expressions)


def _schema_atomic_type_maps(
    schema_files: Iterable[Any],
) -> tuple[dict[QName, QName], dict[tuple[QName, QName], QName]]:
    """Collect declared element and attribute types used by typed members."""
    xsd_namespace = "http://www.w3.org/2001/XMLSchema"
    element_tag = f"{{{xsd_namespace}}}element"
    attribute_tag = f"{{{xsd_namespace}}}attribute"
    element_types: dict[QName, QName] = {}
    attribute_types: dict[tuple[QName, QName], QName] = {}

    def declared_type(node: etree._Element) -> QName | None:
        value = (node.get("type") or "").strip()
        if not value:
            return None
        if ":" in value:
            prefix, local_name = value.split(":", 1)
            return QName(node.nsmap.get(prefix, ""), local_name, prefix)
        return QName(xsd_namespace, value)

    for schema_file in schema_files:
        try:
            root = etree.parse(str(schema_file)).getroot()
        except (OSError, etree.XMLSyntaxError):
            continue
        target_namespace = root.get("targetNamespace", "")
        for element in root.findall(element_tag):
            element_name = (element.get("name") or "").strip()
            if not element_name:
                continue
            element_qname = QName(target_namespace, element_name)
            element_type = declared_type(element)
            if element_type is not None:
                element_types[element_qname] = element_type
            for attribute in element.iter(attribute_tag):
                attribute_name = (attribute.get("name") or "").strip()
                attribute_type = declared_type(attribute)
                if not attribute_name or attribute_type is None:
                    continue
                attribute_namespace = (
                    target_namespace if attribute.get("form") == "qualified" else ""
                )
                attribute_types[(element_qname, QName(attribute_namespace, attribute_name))] = (
                    attribute_type
                )
    return element_types, attribute_types


def _xml_name_qname(name: str) -> QName:
    if name.startswith("{"):
        namespace, local_name = name[1:].split("}", 1)
        return QName(namespace, local_name)
    return QName("", name)


@lru_cache(maxsize=128)
def _typed_dimension_schema_proxy(
    namespace: str,
    local_name: str,
    type_namespace: str,
    type_local_name: str,
    lexical_value: str,
) -> tuple[Any, str]:
    """Build a small schema that types a simple typed-domain context node."""
    import xmlschema  # type: ignore[import-untyped]
    from xmlschema.xpath import XMLSchemaProxy  # type: ignore[import-untyped]

    xsd_namespace = "http://www.w3.org/2001/XMLSchema"
    wrapper_name = "_formulaTypedMemberContext"
    if not namespace:
        return None, wrapper_name

    type_name = type_local_name.lower()
    if type_name == "dateunion":
        atomic_type = "dateTime" if "T" in lexical_value else "date"
    elif type_namespace == xsd_namespace:
        atomic_type = type_local_name
    elif "datetime" in type_name:
        atomic_type = "dateTime"
    elif "date" in type_name:
        atomic_type = "date"
    elif any(token in type_name for token in ("decimal", "integer", "monetary")):
        atomic_type = "decimal"
    elif "boolean" in type_name:
        atomic_type = "boolean"
    elif "qname" in type_name:
        atomic_type = "QName"
    else:
        atomic_type = "string"

    schema_element = etree.Element(
        f"{{{xsd_namespace}}}schema",
        nsmap={"xs": xsd_namespace, "typed": namespace},
        targetNamespace=namespace,
        elementFormDefault="qualified",
    )
    etree.SubElement(
        schema_element,
        f"{{{xsd_namespace}}}element",
        name=local_name,
        type=f"xs:{atomic_type}",
        nillable="true",
    )
    wrapper_element = etree.SubElement(
        schema_element,
        f"{{{xsd_namespace}}}element",
        name=wrapper_name,
    )
    complex_type = etree.SubElement(wrapper_element, f"{{{xsd_namespace}}}complexType")
    sequence = etree.SubElement(complex_type, f"{{{xsd_namespace}}}sequence")
    etree.SubElement(
        sequence,
        f"{{{xsd_namespace}}}element",
        ref=f"typed:{local_name}",
    )
    schema = XMLSchemaProxy(xmlschema.XMLSchema(etree.tostring(schema_element)))
    return schema, f"{{{namespace}}}{wrapper_name}"


def _typed_dimension_values_equal(
    left_context: Any,
    right_context: Any,
    dimension: Any,
    *,
    equality_tests: tuple[str, ...] = (),
    schema_element_types: dict[QName, QName] | None = None,
    schema_attribute_types: dict[tuple[QName, QName], QName] | None = None,
) -> bool:
    """Compare typed members using their schema-like atomic value semantics."""
    left_xml = getattr(left_context, "typed_dimension_xml", {}).get(dimension)
    right_xml = getattr(right_context, "typed_dimension_xml", {}).get(dimension)
    if left_xml is None or right_xml is None:
        return left_context.typed_dimensions.get(dimension) == right_context.typed_dimensions.get(
            dimension
        )
    try:
        equality_expression = " ".join(equality_tests)
        custom = bool(equality_tests)
        ignore_case = "lower-case(" in equality_expression
        normalize_date_union = "dateTime(" in equality_expression
        return _canonical_typed_member(
            etree.fromstring(left_xml),
            ignore_child_order=custom,
            ignore_case=ignore_case,
            normalize_date_union=normalize_date_union,
            schema_element_types=schema_element_types,
            schema_attribute_types=schema_attribute_types,
        ) == _canonical_typed_member(
            etree.fromstring(right_xml),
            ignore_child_order=custom,
            ignore_case=ignore_case,
            normalize_date_union=normalize_date_union,
            schema_element_types=schema_element_types,
            schema_attribute_types=schema_attribute_types,
        )
    except (etree.XMLSyntaxError, ValueError):
        return False


def _facts_have_matching_complete_segment(
    left: Fact,
    right: Fact,
    instance: XbrlInstance,
    taxonomy: TaxonomyStructure,
) -> bool:
    """Compare complete segment child sequences using XBRL S-equality."""
    left_context = instance.contexts.get(left.context_ref)
    right_context = instance.contexts.get(right.context_ref)
    if left_context is None or right_context is None:
        return left_context is right_context
    left_key = context_s_equal_key(left_context, dict(taxonomy.element_defaults))
    right_key = context_s_equal_key(right_context, dict(taxonomy.element_defaults))
    return left_key[5] == right_key[5]


def _facts_have_matching_non_xdt_segment(
    left: Fact,
    right: Fact,
    instance: XbrlInstance,
    taxonomy: TaxonomyStructure,
) -> bool:
    """Compare the ordered non-XDT child sequences of two complete segments."""
    left_context = instance.contexts.get(left.context_ref)
    right_context = instance.contexts.get(right.context_ref)
    if left_context is None or right_context is None:
        return left_context is right_context
    dimension_tags = {
        f"{{{XBRLDI_NS}}}explicitMember",
        f"{{{XBRLDI_NS}}}typedMember",
    }

    def non_xdt_key(context: Any) -> tuple[Any, ...]:
        segment_key = context_s_equal_key(context, dict(taxonomy.element_defaults))[5]
        return tuple(child for child in segment_key if child[0] not in dimension_tags)

    return non_xdt_key(left_context) == non_xdt_key(right_context)


def _facts_have_matching_complete_scenario(
    left: Fact,
    right: Fact,
    instance: XbrlInstance,
    taxonomy: TaxonomyStructure,
) -> bool:
    """Compare complete scenario child sequences using XBRL S-equality."""
    left_context = instance.contexts.get(left.context_ref)
    right_context = instance.contexts.get(right.context_ref)
    if left_context is None or right_context is None:
        return left_context is right_context
    left_key = context_s_equal_key(left_context, dict(taxonomy.element_defaults))
    right_key = context_s_equal_key(right_context, dict(taxonomy.element_defaults))
    return left_key[4] == right_key[4]


def _facts_have_matching_non_xdt_scenario(
    left: Fact,
    right: Fact,
    instance: XbrlInstance,
    taxonomy: TaxonomyStructure,
) -> bool:
    """Compare the ordered non-XDT child sequences of two complete scenarios."""
    left_context = instance.contexts.get(left.context_ref)
    right_context = instance.contexts.get(right.context_ref)
    if left_context is None or right_context is None:
        return left_context is right_context
    dimension_tags = {
        f"{{{XBRLDI_NS}}}explicitMember",
        f"{{{XBRLDI_NS}}}typedMember",
    }

    def non_xdt_key(context: Any) -> tuple[Any, ...]:
        scenario_key = context_s_equal_key(context, dict(taxonomy.element_defaults))[4]
        return tuple(child for child in scenario_key if child[0] not in dimension_tags)

    return non_xdt_key(left_context) == non_xdt_key(right_context)


def _canonical_typed_member(
    element: etree._Element,
    *,
    ignore_child_order: bool = False,
    ignore_case: bool = False,
    normalize_date_union: bool = False,
    schema_element_types: dict[QName, QName] | None = None,
    schema_attribute_types: dict[tuple[QName, QName], QName] | None = None,
) -> tuple[Any, ...]:
    element_qname = _xml_name_qname(str(element.tag))
    attributes = tuple(
        sorted(
            (
                name,
                _canonical_typed_atomic(
                    value,
                    etree.QName(name).localname,
                    element,
                    ignore_case=ignore_case,
                    normalize_date_union=normalize_date_union,
                    schema_type=(schema_attribute_types or {}).get(
                        (element_qname, _xml_name_qname(name))
                    ),
                ),
            )
            for name, value in element.attrib.items()
        )
    )
    local_name = etree.QName(element).localname
    text = _canonical_typed_atomic(
        (element.text or "").strip(),
        local_name,
        element,
        ignore_case=ignore_case,
        normalize_date_union=normalize_date_union,
        schema_type=(schema_element_types or {}).get(element_qname),
    )
    child_values = [
        _canonical_typed_member(
            child,
            ignore_child_order=ignore_child_order,
            ignore_case=ignore_case,
            normalize_date_union=normalize_date_union,
            schema_element_types=schema_element_types,
            schema_attribute_types=schema_attribute_types,
        )
        for child in element
        if isinstance(child.tag, str)
    ]
    if ignore_child_order:
        child_values.sort(key=repr)
    children = tuple(child_values)
    return str(element.tag), attributes, text, children


def _canonical_typed_atomic(
    value: str,
    local_name: str,
    element: etree._Element,
    *,
    ignore_case: bool,
    normalize_date_union: bool,
    schema_type: QName | None = None,
) -> Any:
    lowered = local_name.lower()
    type_name = schema_type.local_name.lower() if schema_type is not None else ""
    if any(token in lowered for token in ("dec", "dbl", "int")) or type_name in {
        "decimal",
        "double",
        "float",
        "integer",
        "nonnegativeinteger",
        "nonpositiveinteger",
        "negativeinteger",
        "positiveinteger",
        "long",
        "int",
        "short",
        "byte",
        "unsignedlong",
        "unsignedint",
        "unsignedshort",
        "unsignedbyte",
    }:
        try:
            return Decimal(value)
        except InvalidOperation:
            return value
    if "qname" in lowered:
        if ":" in value:
            prefix, name = value.split(":", 1)
            return element.nsmap.get(prefix, ""), name
        return element.nsmap.get(None, ""), value
    if normalize_date_union and "date" in lowered:
        from datetime import date, datetime, time, timedelta

        try:
            if "T" in value:
                return datetime.fromisoformat(value.replace("Z", "+00:00"))
            return datetime.combine(date.fromisoformat(value), time()) + timedelta(days=1)
        except ValueError:
            return value
    if ignore_case and "str" in lowered:
        return value.casefold()
    return value


def _coerce_xpath_variable_value(
    raw: str,
    *,
    namespaces: dict[str, str],
    xpath_expr: str,
) -> Any:
    """Convert a fact value to the best Python value for XPath variable binding."""
    value = _coerce_value(raw)
    if not isinstance(value, str):
        return value
    if "QName(" not in xpath_expr or ":" not in value:
        return value
    prefix, _local_name = value.split(":", 1)
    namespace = namespaces.get(prefix)
    if not namespace:
        return value
    try:
        from elementpath.datatypes import QName as XPathQName  # type: ignore[import-untyped]

        return XPathQName(namespace, value)
    except Exception:  # noqa: BLE001
        return value


def _coerce_typed_fact_value(
    raw: str,
    concept: Any,
    *,
    namespaces: dict[str, str],
    xpath_expr: str,
) -> Any:
    category = concept_type_category(concept)
    if category == "integer":
        try:
            return int(raw.strip())
        except ValueError:
            return raw
    if category in {"float", "double"}:
        try:
            return _builtin_xsd_type(category).decode(raw.strip())
        except Exception:  # noqa: BLE001
            return raw
    if category == "boolean":
        value = raw.strip()
        if value in {"true", "1"}:
            return True
        if value in {"false", "0"}:
            return False
    if category == "date":
        try:
            from elementpath.datatypes import Date  # type: ignore[import-untyped]

            return Date.fromstring(raw.strip())
        except Exception:  # noqa: BLE001
            return raw
    if category == "dateTime":
        try:
            from elementpath.datatypes import DateTime  # type: ignore[import-untyped]

            return DateTime.fromstring(raw.strip())
        except Exception:  # noqa: BLE001
            return raw
    if category == "qname":
        if ":" in raw:
            prefix, _local_name = raw.split(":", 1)
            namespace = namespaces.get(prefix)
            if namespace:
                try:
                    from elementpath.datatypes import (  # type: ignore[import-untyped]
                        QName as XPathQName,
                    )

                    return XPathQName(namespace, raw)
                except Exception:  # noqa: BLE001
                    return raw
        return raw
    if category in {"string", "fraction"}:
        return raw
    return _coerce_xpath_variable_value(
        raw,
        namespaces=namespaces,
        xpath_expr=xpath_expr,
    )


def _comparison_rhs_type(rhs: str) -> str | None:
    expr = rhs.strip()
    if expr in {"true()", "false()"}:
        return "boolean"
    if re.fullmatch(r"[+-]?(?:\d+(?:\.\d*)?|\.\d+)", expr):
        return "decimal"
    if (expr.startswith("'") and expr.endswith("'")) or (
        expr.startswith('"') and expr.endswith('"')
    ):
        return "string"
    constructor_match = re.match(r"^xs:([A-Za-z][\w.-]*)\s*\(", expr)
    if constructor_match is None:
        return None
    constructor = constructor_match.group(1).lower()
    if constructor in {"boolean", "date", "datetime", "qname", "string"}:
        return "dateTime" if constructor == "datetime" else constructor
    if constructor in {"decimal", "integer", "float", "double"}:
        return "decimal"
    return None


def _fact_to_message_element(
    fact: Fact,
    *,
    default_value: str | None = None,
    xsd_type: str | None = None,
) -> etree._Element:
    """Build a lightweight XML element for message XPath evaluation."""
    prefix = fact.concept.prefix or "fact"
    nsmap = {prefix: fact.concept.namespace} if fact.concept.namespace else {}
    if xsd_type is not None:
        nsmap["xs"] = "http://www.w3.org/2001/XMLSchema"
    if fact.concept.namespace:
        tag = f"{{{fact.concept.namespace}}}{fact.concept.local_name}"
    else:
        tag = fact.concept.local_name

    element = etree.Element(tag, nsmap=nsmap)
    if xsd_type is not None:
        element.set(
            "{http://www.w3.org/2001/XMLSchema-instance}type",
            f"xs:{xsd_type}",
        )
    element.set("contextRef", fact.context_ref)
    if fact.unit_ref:
        element.set("unitRef", fact.unit_ref)
    if fact.decimals is not None:
        element.set("decimals", fact.decimals)
    if fact.precision is not None:
        element.set("precision", fact.precision)
    if fact.is_nil:
        element.set("{http://www.w3.org/2001/XMLSchema-instance}nil", "true")
    element.text = default_value if default_value is not None else fact.value
    return element


def _fact_node_xsd_type(concept: Any, lexical_value: str) -> str | None:
    """Map an XBRL item type and lexical value to its XPath atomic type."""
    category = concept_type_category(concept)
    if category == "dateTime":
        return "dateTime" if "T" in lexical_value else "date"
    if category in {"date", "boolean", "string"}:
        return category
    if category in {"float", "double", "integer"}:
        return category
    if category in {"monetary", "decimal"}:
        return "decimal"
    if category == "qname":
        return "QName"
    return None


@cache
def _builtin_xsd_type(type_name: str) -> Any:
    import xmlschema  # type: ignore[import-untyped]

    return xmlschema.XMLSchema10.builtin_types()[type_name]


def _typed_xpath_tree(
    root: etree._Element,
    element_types: dict[int, str],
) -> tuple[Any, dict[int, Any]]:
    """Build an elementpath tree and attach PSVI-equivalent atomic types."""
    from elementpath.tree_builders import get_node_tree  # type: ignore[import-untyped]

    node_root = get_node_tree(root)
    nodes_by_element: dict[int, Any] = {}
    for node in node_root.iter():
        element = getattr(node, "elem", None)
        if element is None:
            continue
        element_id = id(element)
        nodes_by_element[element_id] = node
        type_name = element_types.get(element_id)
        if type_name is not None:
            node.xsd_type = _builtin_xsd_type(type_name)
    return node_root, nodes_by_element


def _tuple_variable_filter_matches(candidate: Fact, reference: Fact, resource: Any) -> bool:
    """Evaluate tuple filters that compare a candidate with a bound fact node."""
    if resource.local_name == "siblingFilter":
        return candidate.position_path[:-1] == reference.position_path[:-1]

    location = (resource.attributes.get("location") or "").strip()
    if not location:
        return False
    current_path = candidate.position_path
    target_path = reference.position_path
    for step in (part.strip() for part in location.split("/")):
        if not step or step == ".":
            continue
        if step == "..":
            if not current_path:
                return False
            current_path = current_path[:-1]
            continue

        # A downward step can only select the referenced fact if its node path
        # continues from the current location.  Tuple paths retain the QName
        # of every intermediary tuple so named child steps can be checked too.
        if (
            len(target_path) <= len(current_path)
            or target_path[: len(current_path)] != current_path
        ):
            return False
        current_path = target_path[: len(current_path) + 1]
        if step != "*":
            selected_qname = _fact_path_qname(reference, current_path)
            wanted_qname = _resolve_location_step_qname(step, resource.namespaces)
            if selected_qname is None or wanted_qname is None or selected_qname != wanted_qname:
                return False
    return current_path == target_path


def _instant_duration_filter_matches(
    candidate: Fact,
    reference: Fact,
    boundary: str,
    instance: XbrlInstance,
) -> bool:
    """Compare an instant candidate with a bound duration-fact boundary."""
    candidate_context = instance.contexts.get(candidate.context_ref)
    reference_context = instance.contexts.get(reference.context_ref)
    if candidate_context is None or reference_context is None:
        return False
    instant_period = candidate_context.period
    duration_period = reference_context.period
    if instant_period.period_type != "instant" or duration_period.period_type != "duration":
        return False
    if instant_period.instant_date is None:
        return False

    instant_boundary = instant_period.instant_date
    if instant_period.instant_date_only:
        instant_boundary += timedelta(days=1)
    if boundary == "start":
        duration_boundary = duration_period.start_date
    elif boundary == "end":
        duration_boundary = duration_period.end_date
        if duration_boundary is not None and duration_period.end_date_only:
            duration_boundary += timedelta(days=1)
    else:
        return False
    return duration_boundary is not None and instant_boundary == duration_boundary


def _facts_have_matching_period(
    candidate: Fact,
    reference: Fact,
    instance: XbrlInstance,
) -> bool:
    """Compare the period aspect of two facts using XBRL boundary semantics."""
    candidate_context = instance.contexts.get(candidate.context_ref)
    reference_context = instance.contexts.get(reference.context_ref)
    if candidate_context is None or reference_context is None:
        return False
    return _period_aspect_key(candidate_context.period) == _period_aspect_key(
        reference_context.period
    )


def _facts_have_matching_entity_identifier(
    candidate: Fact,
    reference: Fact,
    instance: XbrlInstance,
) -> bool:
    """Compare entity identifier schemes and values without URI normalization."""
    candidate_context = instance.contexts.get(candidate.context_ref)
    reference_context = instance.contexts.get(reference.context_ref)
    if candidate_context is None or reference_context is None:
        return False
    return (
        candidate_context.entity.scheme == reference_context.entity.scheme
        and candidate_context.entity.identifier == reference_context.entity.identifier
    )


def _facts_have_matching_unit(
    candidate: Fact,
    reference: Fact,
    instance: XbrlInstance,
) -> bool:
    """Compare the U-equality signatures of two numeric facts' units."""
    if candidate.unit_ref is None or reference.unit_ref is None:
        return False
    candidate_unit = instance.units.get(candidate.unit_ref)
    reference_unit = instance.units.get(reference.unit_ref)
    if candidate_unit is None or reference_unit is None:
        return False
    return unit_structure_key(candidate_unit) == unit_structure_key(reference_unit)


def _facts_have_matching_dimension(
    candidate: Fact,
    reference: Fact,
    instance: XbrlInstance,
    dimension: QName,
    *,
    equality_tests: tuple[str, ...] = (),
    schema_element_types: dict[QName, QName] | None = None,
    schema_attribute_types: dict[tuple[QName, QName], QName] | None = None,
) -> bool:
    """Compare one explicit or typed dimension aspect between two facts."""
    candidate_context = instance.contexts.get(candidate.context_ref)
    reference_context = instance.contexts.get(reference.context_ref)
    if candidate_context is None or reference_context is None:
        return False
    return candidate_context.dimensions.get(dimension) == reference_context.dimensions.get(
        dimension
    ) and _typed_dimension_values_equal(
        candidate_context,
        reference_context,
        dimension,
        equality_tests=equality_tests,
        schema_element_types=schema_element_types,
        schema_attribute_types=schema_attribute_types,
    )


def _period_aspect_key(period: Any) -> tuple[Any, ...]:
    if period.period_type == "forever":
        return ("forever",)
    if period.period_type == "instant":
        instant = period.instant_date
        if instant is not None and period.instant_date_only:
            instant += timedelta(days=1)
        return ("instant", instant)
    end = period.end_date
    if end is not None and period.end_date_only:
        end += timedelta(days=1)
    return ("duration", period.start_date, end)


def _fact_path_qname(fact: Fact, path: tuple[int, ...]) -> QName | None:
    if path == fact.position_path:
        return fact.concept
    for index, ancestor in enumerate(fact.tuple_ancestor_concepts):
        if path == fact.tuple_path[: index + 1]:
            return ancestor
    return None


def _resolve_location_step_qname(step: str, namespaces: dict[str, str]) -> QName | None:
    if ":" in step:
        prefix, local_name = step.split(":", 1)
        namespace = namespaces.get(prefix)
        if namespace is None:
            return None
        return QName(namespace=namespace, local_name=local_name)
    return QName(namespace=namespaces.get("", ""), local_name=step)


def _with_equivalent_variable_prefixes(
    variables: dict[str, Any],
    namespaces: dict[str, str],
) -> dict[str, Any]:
    """Alias lexical prefixes that identify the same expanded variable QName."""
    aliased = dict(variables)
    for name, value in variables.items():
        if ":" not in name:
            continue
        prefix, local_name = name.split(":", 1)
        namespace = namespaces.get(prefix)
        if namespace is None:
            continue
        for equivalent_prefix, equivalent_namespace in namespaces.items():
            if equivalent_prefix and equivalent_namespace == namespace:
                aliased[f"{equivalent_prefix}:{local_name}"] = value
    return aliased


def _stringify_xpath_result(result: list[Any]) -> str:
    """Render an XPath result sequence as readable message text."""
    parts: list[str] = []
    for item in result:
        value = getattr(item, "value", item)
        if isinstance(value, etree._Element):
            value = "".join(value.itertext())
        text = str(value).strip()
        if text:
            parts.append(text)
    return " ".join(parts)


def _stringify_message_value(value: Any) -> str:
    raw = getattr(value, "value", value)
    if isinstance(raw, etree._Element):
        return "".join(raw.itertext())
    return str(raw)


def _to_bool(value: Any) -> bool:
    from elementpath.exceptions import ElementPathTypeError  # type: ignore[import-untyped]

    if isinstance(value, bool):
        return value
    sequence = [value] if not isinstance(value, list) else value
    if not sequence:
        return False
    if all(hasattr(item, "tag") for item in sequence):
        return True
    if len(sequence) != 1:
        raise ElementPathTypeError("Effective boolean value is undefined", code="err:FORG0006")
    item = sequence[0]
    if isinstance(item, bool):
        return item
    if isinstance(item, (int, float, Decimal)):
        try:
            return Decimal(str(item)) != 0
        except Exception:  # noqa: BLE001
            return bool(item)
    if isinstance(item, str):
        return item != ""
    raise ElementPathTypeError("Effective boolean value is undefined", code="err:FORG0006")
