"""Formula output-instance generation and semantic comparison."""

from __future__ import annotations

import re
from collections import Counter
from copy import deepcopy
from dataclasses import dataclass
from datetime import date, timedelta
from decimal import ROUND_HALF_EVEN, Decimal, InvalidOperation
from pathlib import Path
from typing import Any

from lxml import etree

from bde_xbrl_editor.instance.constants import XBRLDI_NS, XBRLI_NS
from bde_xbrl_editor.instance.models import (
    Fact,
    ReportingEntity,
    ReportingPeriod,
    XbrlContext,
    XbrlInstance,
    XbrlUnit,
)
from bde_xbrl_editor.instance.s_equal import (
    build_s_equal_key_from_xml_fragments,
    effective_s_equal_key,
    unit_structure_key,
)
from bde_xbrl_editor.taxonomy.models import (
    FormulaAspectRule,
    FormulaOutputDefinition,
    QName,
    TaxonomyStructure,
)
from bde_xbrl_editor.validation.formula.evaluator import FormulaEvaluator, _to_bool
from bde_xbrl_editor.validation.models import ValidationFinding, ValidationSeverity


@dataclass(frozen=True)
class OutputInstanceEvaluation:
    """An output instance plus Formula runtime findings raised while producing it."""

    instance: XbrlInstance
    findings: tuple[ValidationFinding, ...] = ()


@dataclass(frozen=True)
class OutputInstanceComparison:
    """Semantic comparison result for generated and expected output instances."""

    matched: bool
    actual_fact_count: int
    expected_fact_count: int
    missing_facts: int = 0
    unexpected_facts: int = 0


class FormulaOutputInstanceEvaluator:
    """Evaluate Formula output resources into an XBRL instance model."""

    def __init__(self, taxonomy: TaxonomyStructure) -> None:
        self._taxonomy = taxonomy
        self._evaluator = FormulaEvaluator(taxonomy)

    def evaluate(self, source_instance: XbrlInstance) -> OutputInstanceEvaluation:
        output = XbrlInstance(
            taxonomy_entry_point=source_instance.taxonomy_entry_point,
            schema_ref_href=source_instance.schema_ref_href,
            entity=deepcopy(source_instance.entity),
            period=deepcopy(source_instance.period),
            source_path=None,
        )
        findings: list[ValidationFinding] = []
        facts_by_concept = self._evaluator._facts_by_concept(source_instance)

        for formula in self._taxonomy.formula_assertion_set.output_formulas:
            if not formula.value_xpath.strip():
                continue
            preflight_error = (
                "err:FORG0006"
                if self._has_invalid_filter_effective_boolean_value(formula)
                else None
            )
            if preflight_error is not None:
                findings.append(
                    self._runtime_finding(
                        formula,
                        _FormulaOutputError(preflight_error, preflight_error),
                    )
                )
                continue
            try:
                bindings = self._evaluator._bind_variables(
                    formula,  # type: ignore[arg-type]
                    source_instance,
                    facts_by_concept=facts_by_concept,
                )
            except Exception as exc:  # noqa: BLE001
                findings.append(self._runtime_finding(formula, exc))
                continue
            if formula.implicit_filtering and len(formula.variables) > 1:
                try:
                    bindings = self._evaluator._implicit_formula_bindings(
                        formula,
                        bindings,
                        source_instance,
                    )
                except Exception as exc:  # noqa: BLE001
                    findings.append(self._runtime_finding(formula, exc))
                    continue
            for resolved in bindings:
                if resolved.error is not None:
                    findings.append(self._runtime_finding(formula, resolved.error))
                    continue
                binding = resolved.fact_binding
                try:
                    if any(
                        not binding.get(variable.variable_name) and variable.fallback_value is None
                        for variable in formula.variables
                    ):
                        continue
                    general_values = dict(resolved.general_values)
                    general_values.update(
                        self._evaluator._resolve_parameter_values(
                            formula.parameters,
                            binding,
                            source_instance,
                            namespaces=formula.namespaces,
                            existing=general_values,
                        )
                    )
                    if not self._preconditions_pass(
                        formula,
                        binding,
                        source_instance,
                        general_values,
                    ):
                        continue
                    value_error = self._schema_aware_sequence_error(
                        formula,
                        binding,
                        source_instance,
                    )
                    if value_error is not None:
                        raise _FormulaOutputError(value_error, value_error)
                    self._append_output_fact(
                        output,
                        source_instance,
                        formula,
                        binding,
                        general_values,
                    )
                except Exception as exc:  # noqa: BLE001
                    findings.append(self._runtime_finding(formula, exc))

        return OutputInstanceEvaluation(instance=output, findings=tuple(findings))

    def _preconditions_pass(
        self,
        formula: FormulaOutputDefinition,
        binding: dict[str, list[Fact]],
        instance: XbrlInstance,
        general_values: dict[str, Any],
    ) -> bool:
        for precondition in formula.preconditions:
            result = self._evaluator._eval_xpath(
                precondition.test_xpath,
                binding,
                instance,
                precondition.namespaces or formula.namespaces,
                assertion=formula,  # type: ignore[arg-type]
                general_values=general_values,
                fact_bindings_as_elements=True,
            )
            if not _to_bool(result):
                return False
        return True

    def _schema_aware_sequence_error(
        self,
        formula: FormulaOutputDefinition,
        binding: dict[str, list[Fact]],
        source_instance: XbrlInstance,
    ) -> str | None:
        """Preserve XPath errors that depend on source schema annotations.

        The in-memory fact nodes supplied to elementpath do not carry the PSVI
        annotations of the original validated instance. Consequently elementpath
        can atomize tuple and numeric facts as untyped strings. Formula requires
        their schema-aware XPath errors instead.
        """
        if "string-join" not in formula.value_xpath:
            return None
        for variable in formula.variables:
            if (
                not variable.bind_as_sequence
                or f"${variable.variable_name}" not in formula.value_xpath
            ):
                continue
            bound_facts = binding.get(variable.variable_name, ())
            if any(self._is_tuple_fact(fact) for fact in bound_facts):
                return "err:FOTY0012"
            complemented_concepts = [
                resource
                for resource in variable.filter_resources
                if resource.local_name == "conceptName" and resource.complement
            ]
            if complemented_concepts and any(fact.tuple_path for fact in source_instance.facts):
                excluded = {
                    qname for resource in complemented_concepts for qname in resource.qnames
                }
                if any(
                    concept.qname not in excluded
                    and concept.substitution_group is not None
                    and concept.substitution_group.local_name == "tuple"
                    for concept in self._taxonomy.concepts.values()
                ):
                    return "err:FOTY0012"
            explicitly_stringified = "xs:string(" in formula.value_xpath
            if not explicitly_stringified and (
                any(self._is_numeric_fact(fact) for fact in bound_facts)
                or (
                    not bound_facts
                    and self._sequence_filter_can_bind_numeric_fact(variable.filter_resources)
                )
            ):
                return "xqt-err:XPTY0004"
            # A detached synthetic resource has no QName information with
            # which to inspect its candidates. Keep the conservative result
            # used by the runtime API for that case.
            if any(
                resource.local_name == "ancestorFilter" and not resource.qnames
                for resource in variable.filter_resources
            ):
                return "err:FOTY0012"
        return None

    def _is_tuple_fact(self, fact: Fact) -> bool:
        concept = self._taxonomy.concepts.get(fact.concept)
        return bool(
            concept is not None
            and concept.substitution_group is not None
            and concept.substitution_group.local_name == "tuple"
        )

    def _is_numeric_fact(self, fact: Fact) -> bool:
        concept = self._taxonomy.concepts.get(fact.concept)
        if concept is None:
            return False
        local_name = concept.data_type.local_name.lower()
        return any(
            token in local_name
            for token in (
                "decimal",
                "integer",
                "float",
                "double",
                "monetary",
                "shares",
                "pure",
            )
        )

    def _sequence_filter_can_bind_numeric_fact(
        self,
        filter_resources: tuple[Any, ...],
    ) -> bool:
        for resource in filter_resources:
            for qname in resource.qnames:
                concept = self._taxonomy.concepts.get(qname)
                if concept is None:
                    continue
                local_name = concept.data_type.local_name.lower()
                if any(
                    token in local_name
                    for token in (
                        "decimal",
                        "integer",
                        "float",
                        "double",
                        "monetary",
                        "shares",
                        "pure",
                    )
                ):
                    return True
        return False

    @staticmethod
    def _has_invalid_filter_effective_boolean_value(
        formula: FormulaOutputDefinition,
    ) -> bool:
        return any(
            xpath_filter.filter_type == "general"
            and xpath_filter.xpath_expr.strip().startswith(("QName(", "xs:QName("))
            for variable in formula.variables
            for xpath_filter in variable.xpath_filters
        )

    def _append_output_fact(
        self,
        output: XbrlInstance,
        source_instance: XbrlInstance,
        formula: FormulaOutputDefinition,
        binding: dict[str, list[Fact]],
        general_values: dict[str, Any],
    ) -> None:
        result = self._evaluator._eval_xpath(
            formula.value_xpath,
            binding,
            source_instance,
            formula.namespaces,
            assertion=formula,  # type: ignore[arg-type]
            general_values=general_values,
            fact_bindings_as_elements=_expression_needs_fact_nodes(formula.value_xpath),
        )
        sequence = result if isinstance(result, list) else [result]
        if len(sequence) > 1:
            raise _FormulaOutputError(
                "xbrlfe:nonSingletonOutputValue",
                "A formula output value must be a singleton sequence",
            )

        source_fact = self._aspect_source_fact(formula, None, binding)
        concept = self._output_concept(
            formula,
            source_fact,
            binding,
            source_instance,
            general_values,
        )
        if concept is None:
            raise _FormulaOutputError(
                "xbrlfe:missingConceptRule",
                "The output concept cannot be determined",
            )

        context_source = source_fact
        if context_source is None:
            raise _FormulaOutputError(
                "xbrlfe:missingEntityIdentifierRule",
                "The output context cannot be determined",
            )
        base_context = source_instance.contexts.get(context_source.context_ref)
        if base_context is None:
            raise _FormulaOutputError(
                "xbrlfe:missingEntityIdentifierRule",
                "The output context source does not reference a context",
            )
        output_context = self._output_context(
            formula,
            concept,
            base_context,
            binding,
            source_instance,
            general_values,
        )
        context_ref = self._store_context(output, output_context)

        unit_ref: str | None = None
        output_unit = self._output_unit(
            formula,
            concept,
            source_fact,
            binding,
            source_instance,
            general_values,
        )
        if output_unit is not None:
            unit_ref = self._store_unit(output, output_unit)

        is_nil = not sequence
        value = "" if is_nil else _xpath_item_string(sequence[0])
        decimals = None
        precision = "0" if self._is_numeric_concept(concept) else None
        if is_nil:
            decimals = None
            precision = None
        else:
            if formula.decimals_xpath is not None:
                decimals = self._evaluate_accuracy(
                    formula.decimals_xpath,
                    formula,
                    binding,
                    source_instance,
                    general_values,
                )
                precision = None
            elif formula.precision_xpath is not None:
                precision = self._evaluate_accuracy(
                    formula.precision_xpath,
                    formula,
                    binding,
                    source_instance,
                    general_values,
                )
                decimals = None
        output.facts.append(
            Fact(
                concept=concept,
                context_ref=context_ref,
                unit_ref=unit_ref,
                value=value,
                decimals=decimals,
                precision=precision,
                is_nil=is_nil,
            )
        )

    def _output_unit(
        self,
        formula: FormulaOutputDefinition,
        concept: QName,
        source_fact: Fact | None,
        binding: dict[str, list[Fact]],
        instance: XbrlInstance,
        general_values: dict[str, Any],
    ) -> XbrlUnit | None:
        rule = next((item for item in formula.aspect_rules if item.aspect == "unit"), None)
        source = self._aspect_source_fact(formula, "unit", binding) or source_fact
        source_unit = (
            instance.units.get(source.unit_ref)
            if source is not None and source.unit_ref is not None
            else None
        )
        if rule is None:
            if formula.source is None:
                return None
            return deepcopy(source_unit) if source_unit is not None else None

        root = _rule_root(rule)
        augment = root is None or (root.get("augment") or "true").lower() == "true"
        numerator: list[QName] = []
        denominator: list[QName] = []
        if augment and source_unit is not None:
            source_numerator, source_denominator = _unit_factors(source_unit)
            numerator.extend(source_numerator)
            denominator.extend(source_denominator)

        if root is not None:
            for child in root:
                if not isinstance(child.tag, str):
                    continue
                operation = etree.QName(child).localname
                if operation not in {"multiplyBy", "divideBy"}:
                    continue
                child_numerator: tuple[QName, ...] = ()
                child_denominator: tuple[QName, ...] = ()
                child_source = (child.get("source") or "").strip()
                if child_source:
                    facts = binding.get(child_source, ())
                    child_unit = instance.units.get(facts[0].unit_ref or "") if facts else None
                    if child_unit is not None:
                        child_numerator, child_denominator = _unit_factors(child_unit)
                measure_expr = (child.get("measure") or "").strip()
                if measure_expr:
                    measure_item = self._evaluate_single(
                        measure_expr,
                        formula,
                        binding,
                        instance,
                        general_values,
                        rule.namespaces,
                    )
                    measure = _xpath_qname(measure_item, rule.namespaces)
                    if measure is not None:
                        child_numerator = (*child_numerator, measure)
                if operation == "multiplyBy":
                    numerator.extend(child_numerator)
                    denominator.extend(child_denominator)
                else:
                    numerator.extend(child_denominator)
                    denominator.extend(child_numerator)

        numerator, denominator = _cancel_unit_factors(numerator, denominator)
        if not numerator:
            raise _FormulaOutputError(
                "xbrlfe:missingUnitRule",
                f"No numerator measure is available for numeric concept {concept}",
            )
        if denominator:
            return XbrlUnit(
                unit_id="formula-unit",
                measure_uri="",
                unit_form="divide",
                numerator_measure_qnames=tuple(numerator),
                denominator_measure_qnames=tuple(denominator),
            )
        return XbrlUnit(
            unit_id="formula-unit",
            measure_uri=str(numerator[0]),
            measure_qname=numerator[0] if len(numerator) == 1 else None,
            unit_form="simple",
            simple_measure_count=len(numerator),
            simple_measure_qnames=tuple(numerator),
        )

    @staticmethod
    def _store_unit(output: XbrlInstance, unit: XbrlUnit) -> str:
        key = unit_structure_key(unit)
        for unit_id, existing in output.units.items():
            if unit_structure_key(existing) == key:
                return unit_id
        unit_id = f"formula-unit-{len(output.units) + 1}"
        unit.unit_id = unit_id
        output.units[unit_id] = unit
        return unit_id

    def _output_context(
        self,
        formula: FormulaOutputDefinition,
        concept: QName,
        base_context: XbrlContext,
        binding: dict[str, list[Fact]],
        instance: XbrlInstance,
        general_values: dict[str, Any],
    ) -> XbrlContext:
        context = deepcopy(base_context)
        base_key = effective_s_equal_key(base_context)
        period_key = base_key[3]
        remainder_key = base_key[4:]
        changed = False
        dimensions_changed = False
        occ_changed = False

        entity_rule = next(
            (rule for rule in formula.aspect_rules if rule.aspect == "entityIdentifier"),
            None,
        )
        if entity_rule is not None:
            source_context = (
                self._rule_source_context(formula, entity_rule, binding, instance) or context
            )
            root = _rule_root(entity_rule)
            scheme_expr = root.get("scheme") if root is not None else None
            value_expr = root.get("value") if root is not None else None
            scheme = source_context.entity.scheme
            identifier = source_context.entity.identifier
            if scheme_expr:
                scheme = self._evaluate_string(
                    scheme_expr,
                    formula,
                    binding,
                    instance,
                    general_values,
                    entity_rule.namespaces,
                )
            if value_expr:
                identifier = self._evaluate_string(
                    value_expr,
                    formula,
                    binding,
                    instance,
                    general_values,
                    entity_rule.namespaces,
                )
            context.entity = ReportingEntity(identifier=identifier, scheme=scheme)
            changed = True

        period_rule = next(
            (rule for rule in formula.aspect_rules if rule.aspect == "period"),
            None,
        )
        if period_rule is not None:
            source_context = (
                self._rule_source_context(formula, period_rule, binding, instance) or context
            )
            context.period = self._period_from_rule(
                formula,
                period_rule,
                source_context.period,
                binding,
                instance,
                general_values,
            )
            root = _rule_root(period_rule)
            if root is None or len(root) == 0:
                period_key = effective_s_equal_key(source_context)[3]
            else:
                probe = deepcopy(context)
                probe.s_equal_key = None
                period_key = effective_s_equal_key(probe)[3]
            changed = True

        for rule in formula.aspect_rules:
            if rule.aspect not in {"explicitDimension", "typedDimension"}:
                continue
            source_context = self._rule_source_context(formula, rule, binding, instance)
            if source_context is not None and rule.dimension is not None:
                self._copy_dimension(context, source_context, rule.dimension)
            if rule.dimension is None:
                continue
            root = _rule_root(rule)
            child_names = _child_local_names(root)
            if "omit" in child_names:
                self._remove_dimension(context, rule.dimension)
            elif rule.aspect == "explicitDimension":
                member = self._explicit_dimension_member(
                    formula,
                    rule,
                    binding,
                    instance,
                    general_values,
                )
                if member is not None:
                    context.dimensions[rule.dimension] = member
                    context.typed_dimensions.pop(rule.dimension, None)
                    context.typed_dimension_elements.pop(rule.dimension, None)
                    context.typed_dimension_xml.pop(rule.dimension, None)
            else:
                self._apply_typed_dimension_rule(
                    context,
                    rule,
                    instance,
                )
            changed = True
            dimensions_changed = True

        if self._place_dimensions_for_concept(context, concept):
            dimensions_changed = True
            changed = True

        for rule in formula.aspect_rules:
            if rule.aspect not in {"occEmpty", "occFragments", "occXpath"}:
                continue
            self._apply_occ_rule(context, formula, rule)
            changed = True
            occ_changed = True

        if changed:
            if occ_changed:
                scenario = etree.fromstring(context.scenario_xml) if context.scenario_xml else None
                segment = etree.fromstring(context.segment_xml) if context.segment_xml else None
                context.s_equal_key = build_s_equal_key_from_xml_fragments(
                    context.entity,
                    context.period,
                    scenario,
                    segment,
                    period_key=period_key,
                )
                return context
            if dimensions_changed:
                probe = deepcopy(context)
                probe.s_equal_key = None
                remainder_key = effective_s_equal_key(probe)[4:]
            context.s_equal_key = (
                "ctxseq1",
                context.entity.scheme.strip(),
                context.entity.identifier.strip(),
                period_key,
                *remainder_key,
            )
        return context

    def _place_dimensions_for_concept(
        self,
        context: XbrlContext,
        concept: QName,
    ) -> bool:
        changed = False
        dimensions = set(context.dimensions) | set(context.typed_dimensions)
        for dimension in dimensions:
            applicable = next(
                (
                    hypercube
                    for hypercube in self._taxonomy.hypercubes
                    if concept in hypercube.primary_items
                    and dimension in hypercube.dimensions
                    and hypercube.arcrole == "all"
                ),
                None,
            )
            if applicable is None:
                applicable = next(
                    (
                        hypercube
                        for hypercube in self._taxonomy.hypercubes
                        if concept in hypercube.primary_items and hypercube.arcrole == "all"
                    ),
                    None,
                )
            if applicable is not None:
                target = applicable.context_element
            else:
                target = context.dim_containers.get(dimension, "segment")
            if context.dim_containers.get(dimension) != target:
                context.dim_containers[dimension] = target
                changed = True
        return changed

    @staticmethod
    def _apply_occ_rule(
        context: XbrlContext,
        formula: FormulaOutputDefinition,
        rule: FormulaAspectRule,
    ) -> None:
        root = _rule_root(rule)
        if root is None:
            return
        occ = (root.get("occ") or "").strip()
        if occ not in {"segment", "scenario"}:
            return
        attr_name = f"{occ}_xml"
        if rule.aspect == "occEmpty":
            setattr(context, attr_name, None)
            return

        existing_xml = getattr(context, attr_name)
        container = (
            etree.fromstring(existing_xml)
            if existing_xml
            else etree.Element(f"{{{XBRLI_NS}}}{occ}")
        )
        additions: list[etree._Element] = []
        if rule.aspect == "occFragments":
            additions.extend(deepcopy(child) for child in root if isinstance(child.tag, str))
        elif rule.aspect == "occXpath":
            selected = _select_occ_document_node(
                root.get("select", ""),
                formula.source_path,
            )
            if selected is not None:
                additions.append(selected)
        for addition in additions:
            container.append(addition)
        setattr(
            context,
            attr_name,
            etree.tostring(container, encoding="utf-8", with_tail=False),
        )

    def _period_from_rule(
        self,
        formula: FormulaOutputDefinition,
        rule: FormulaAspectRule,
        source_period: ReportingPeriod,
        binding: dict[str, list[Fact]],
        instance: XbrlInstance,
        general_values: dict[str, Any],
    ) -> ReportingPeriod:
        root = _rule_root(rule)
        if root is None or len(root) == 0:
            return deepcopy(source_period)
        child = next((item for item in root if isinstance(item.tag, str)), None)
        if child is None:
            return deepcopy(source_period)
        kind = etree.QName(child).localname
        if kind == "forever":
            return ReportingPeriod(period_type="forever")
        if kind == "instant":
            expression = child.get("value", "")
            item = self._evaluate_single(
                expression,
                formula,
                binding,
                instance,
                general_values,
                rule.namespaces,
            )
            return ReportingPeriod(
                period_type="instant",
                instant_date=_formula_boundary_date(
                    item,
                    end_boundary=not any(
                        function_name in expression
                        for function_name in (
                            "period-start",
                            "period-end",
                            "period-instant",
                        )
                    ),
                ),
            )
        if kind == "duration":
            start_item = self._evaluate_single(
                child.get("start", ""),
                formula,
                binding,
                instance,
                general_values,
                rule.namespaces,
            )
            end_item = self._evaluate_single(
                child.get("end", ""),
                formula,
                binding,
                instance,
                general_values,
                rule.namespaces,
            )
            return ReportingPeriod(
                period_type="duration",
                start_date=_formula_boundary_date(start_item),
                end_date=_formula_boundary_date(end_item, end_boundary=True),
            )
        return deepcopy(source_period)

    def _explicit_dimension_member(
        self,
        formula: FormulaOutputDefinition,
        rule: FormulaAspectRule,
        binding: dict[str, list[Fact]],
        instance: XbrlInstance,
        general_values: dict[str, Any],
    ) -> QName | None:
        root = _rule_root(rule)
        if root is None:
            return None
        member = next(
            (
                item
                for item in root
                if isinstance(item.tag, str) and etree.QName(item).localname == "member"
            ),
            None,
        )
        if member is None:
            return None
        qname = next(
            (
                item
                for item in member
                if isinstance(item.tag, str) and etree.QName(item).localname == "qname"
            ),
            None,
        )
        if qname is not None:
            return _lexical_qname((qname.text or "").strip(), rule.namespaces)
        expression = next(
            (
                item
                for item in member
                if isinstance(item.tag, str) and etree.QName(item).localname == "qnameExpression"
            ),
            None,
        )
        if expression is None:
            return None
        item = self._evaluate_single(
            _normalize_qname_expression((expression.text or "").strip()),
            formula,
            binding,
            instance,
            general_values,
            rule.namespaces,
        )
        return _xpath_qname(item, rule.namespaces)

    @staticmethod
    def _apply_typed_dimension_rule(
        context: XbrlContext,
        rule: FormulaAspectRule,
        instance: XbrlInstance,
    ) -> None:
        if rule.dimension is None:
            return
        root = _rule_root(rule)
        if root is None:
            return
        xpath_rule = next(
            (
                child
                for child in root
                if isinstance(child.tag, str) and etree.QName(child).localname == "xpath"
            ),
            None,
        )
        if xpath_rule is not None:
            expression = "".join(xpath_rule.itertext()).strip()
            match = re.search(r"@id\s+eq\s+['\"]([^'\"]+)['\"]", expression)
            source_context = instance.contexts.get(match.group(1)) if match else None
            if source_context is not None:
                FormulaOutputInstanceEvaluator._copy_dimension(
                    context,
                    source_context,
                    rule.dimension,
                )
            return
        value_rule = next(
            (
                child
                for child in root
                if isinstance(child.tag, str) and etree.QName(child).localname == "value"
            ),
            None,
        )
        if value_rule is None:
            return
        value_element = next(
            (child for child in value_rule if isinstance(child.tag, str)),
            None,
        )
        if value_element is None:
            return
        dimension = rule.dimension
        context.dimensions[dimension] = dimension
        context.typed_dimensions[dimension] = "".join(value_element.itertext()).strip()
        context.typed_dimension_elements[dimension] = QName.from_clark(value_element.tag)
        context.typed_dimension_xml[dimension] = etree.tostring(
            value_element,
            encoding="utf-8",
            with_tail=False,
        )

    def _rule_source_context(
        self,
        formula: FormulaOutputDefinition,
        rule: FormulaAspectRule,
        binding: dict[str, list[Fact]],
        instance: XbrlInstance,
    ) -> XbrlContext | None:
        source = rule.source or formula.source
        if source and _is_uncovered_source(source):
            fact = FormulaEvaluator._formula_source_fact(formula, binding)
        elif source:
            facts = binding.get(source, ())
            fact = facts[0] if facts else FormulaEvaluator._formula_source_fact(formula, binding)
        else:
            fact = FormulaEvaluator._formula_source_fact(formula, binding)
        return instance.contexts.get(fact.context_ref) if fact is not None else None

    @staticmethod
    def _copy_dimension(
        target: XbrlContext,
        source: XbrlContext,
        dimension: QName,
    ) -> None:
        if dimension in source.dimensions:
            target.dimensions[dimension] = source.dimensions[dimension]
        if dimension in source.typed_dimensions:
            target.typed_dimensions[dimension] = source.typed_dimensions[dimension]
        if dimension in source.typed_dimension_elements:
            target.typed_dimension_elements[dimension] = source.typed_dimension_elements[dimension]
        if dimension in source.typed_dimension_xml:
            target.typed_dimension_xml[dimension] = source.typed_dimension_xml[dimension]
        if dimension in source.dim_containers:
            target.dim_containers[dimension] = source.dim_containers[dimension]

    @staticmethod
    def _remove_dimension(context: XbrlContext, dimension: QName) -> None:
        context.dimensions.pop(dimension, None)
        context.typed_dimensions.pop(dimension, None)
        context.typed_dimension_elements.pop(dimension, None)
        context.typed_dimension_xml.pop(dimension, None)
        context.dim_containers.pop(dimension, None)

    @staticmethod
    def _store_context(output: XbrlInstance, context: XbrlContext) -> str:
        key = effective_s_equal_key(context)
        for context_id, existing in output.contexts.items():
            if effective_s_equal_key(existing) == key:
                return context_id
        context_id = f"formula-context-{len(output.contexts) + 1}"
        context.context_id = context_id
        output.contexts[context_id] = context
        return context_id

    def _evaluate_single(
        self,
        expression: str,
        formula: FormulaOutputDefinition,
        binding: dict[str, list[Fact]],
        instance: XbrlInstance,
        general_values: dict[str, Any],
        namespaces: dict[str, str],
    ) -> Any:
        result = self._evaluator._eval_xpath(
            expression,
            binding,
            instance,
            namespaces or formula.namespaces,
            assertion=formula,  # type: ignore[arg-type]
            general_values=general_values,
            fact_bindings_as_elements=True,
        )
        sequence = result if isinstance(result, list) else [result]
        if len(sequence) != 1:
            raise _FormulaOutputError(
                "xbrlfe:nonSingletonOutputValue",
                "An aspect rule must evaluate to one value",
            )
        return sequence[0]

    def _evaluate_string(
        self,
        expression: str,
        formula: FormulaOutputDefinition,
        binding: dict[str, list[Fact]],
        instance: XbrlInstance,
        general_values: dict[str, Any],
        namespaces: dict[str, str],
    ) -> str:
        return _xpath_item_string(
            self._evaluate_single(
                expression,
                formula,
                binding,
                instance,
                general_values,
                namespaces,
            )
        )

    def _output_concept(
        self,
        formula: FormulaOutputDefinition,
        source_fact: Fact | None,
        binding: dict[str, list[Fact]],
        instance: XbrlInstance,
        general_values: dict[str, Any],
    ) -> QName | None:
        rule = next((item for item in formula.aspect_rules if item.aspect == "concept"), None)
        if rule is None:
            return source_fact.concept if source_fact is not None else None
        if rule.qname is not None:
            return rule.qname
        expression = _rule_child_text(rule, "qnameExpression")
        if expression:
            expression = _normalize_qname_expression(expression)
            result = self._evaluator._eval_xpath(
                expression,
                binding,
                instance,
                rule.namespaces or formula.namespaces,
                assertion=formula,  # type: ignore[arg-type]
                general_values=general_values,
                fact_bindings_as_elements=True,
            )
            sequence = result if isinstance(result, list) else [result]
            if len(sequence) != 1:
                return None
            return _xpath_qname(sequence[0], rule.namespaces)
        rule_source = self._aspect_source_fact(formula, "concept", binding)
        return rule_source.concept if rule_source is not None else None

    @staticmethod
    def _aspect_source_fact(
        formula: FormulaOutputDefinition,
        aspect: str | None,
        binding: dict[str, list[Fact]],
    ) -> Fact | None:
        rule = next((item for item in formula.aspect_rules if item.aspect == aspect), None)
        source = rule.source if rule is not None and rule.source else formula.source
        if source and not _is_uncovered_source(source):
            facts = binding.get(source, ())
            if facts:
                return facts[0]
        return FormulaEvaluator._formula_source_fact(formula, binding)

    def _evaluate_accuracy(
        self,
        expression: str | None,
        formula: FormulaOutputDefinition,
        binding: dict[str, list[Fact]],
        instance: XbrlInstance,
        general_values: dict[str, Any],
    ) -> str | None:
        if expression is None:
            return None
        result = self._evaluator._eval_xpath(
            expression,
            binding,
            instance,
            formula.namespaces,
            assertion=formula,  # type: ignore[arg-type]
            general_values=general_values,
        )
        sequence = result if isinstance(result, list) else [result]
        if len(sequence) != 1:
            raise _FormulaOutputError(
                "xbrlfe:nonSingletonOutputValue",
                "Formula accuracy must evaluate to one value",
            )
        return _xpath_item_string(sequence[0])

    def _is_numeric_concept(self, concept: QName) -> bool:
        declaration = self._taxonomy.concepts.get(concept)
        if declaration is None:
            return False
        local_name = declaration.data_type.local_name.lower()
        return any(
            token in local_name
            for token in (
                "decimal",
                "integer",
                "float",
                "double",
                "monetary",
                "shares",
                "pure",
                "fraction",
            )
        )

    @staticmethod
    def _runtime_finding(
        formula: FormulaOutputDefinition,
        exc: Exception,
    ) -> ValidationFinding:
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


class _FormulaOutputError(Exception):
    def __init__(self, code: str, message: str) -> None:
        self.code = code
        super().__init__(message)


def compare_output_instances(
    actual: XbrlInstance,
    expected: XbrlInstance,
    taxonomy: TaxonomyStructure,
) -> OutputInstanceComparison:
    """Compare output facts independent of IDs, prefixes, and XML document order."""
    actual_facts = Counter(_fact_signature(fact, actual, taxonomy) for fact in actual.facts)
    expected_facts = Counter(_fact_signature(fact, expected, taxonomy) for fact in expected.facts)
    missing = sum((expected_facts - actual_facts).values())
    unexpected = sum((actual_facts - expected_facts).values())
    return OutputInstanceComparison(
        matched=missing == 0 and unexpected == 0,
        actual_fact_count=len(actual.facts),
        expected_fact_count=len(expected.facts),
        missing_facts=missing,
        unexpected_facts=unexpected,
    )


def _fact_signature(
    fact: Fact,
    instance: XbrlInstance,
    taxonomy: TaxonomyStructure,
) -> tuple[Any, ...]:
    context = instance.contexts.get(fact.context_ref)
    context_key = _comparison_context_key(context) if context is not None else (fact.context_ref,)
    unit = instance.units.get(fact.unit_ref or "")
    unit_key = unit_structure_key(unit) if unit is not None else None
    concept = taxonomy.concepts.get(fact.concept)
    type_name = concept.data_type.local_name.lower() if concept is not None else ""
    return (
        fact.concept,
        context_key,
        unit_key,
        fact.is_nil,
        _normalized_fact_value(
            fact.value,
            type_name,
            fact.is_nil,
            decimals=fact.decimals,
            precision=fact.precision,
        ),
        fact.decimals,
        fact.precision,
    )


def _normalized_fact_value(
    value: str,
    type_name: str,
    is_nil: bool,
    *,
    decimals: str | None,
    precision: str | None,
) -> Any:
    if is_nil:
        return None
    if any(
        token in type_name
        for token in ("decimal", "integer", "float", "double", "monetary", "shares", "pure")
    ):
        try:
            number = Decimal(value.strip())
            if decimals is not None and decimals.upper() != "INF":
                number = number.quantize(
                    Decimal(1).scaleb(-int(decimals)),
                    rounding=ROUND_HALF_EVEN,
                )
            elif (
                precision is not None
                and precision.upper() != "INF"
                and int(precision) > 0
                and not number.is_zero()
            ):
                exponent = number.copy_abs().adjusted() - int(precision) + 1
                number = number.quantize(
                    Decimal(1).scaleb(exponent),
                    rounding=ROUND_HALF_EVEN,
                )
            if number.is_zero():
                return Decimal(0)
            return number.normalize()
        except InvalidOperation:
            pass
    if "boolean" in type_name:
        lowered = value.strip().lower()
        if lowered in {"true", "1"}:
            return True
        if lowered in {"false", "0"}:
            return False
    return value


def _comparison_context_key(context: XbrlContext) -> tuple[Any, ...]:
    key = effective_s_equal_key(context)
    if len(key) < 6 or key[0] != "ctxseq1":
        return key
    return (*key[:4], _normalized_container_key(key[4]), _normalized_container_key(key[5]))


def _normalized_container_key(children: tuple[Any, ...]) -> tuple[Any, ...]:
    dimension_tags = {
        f"{{{XBRLDI_NS}}}explicitMember",
        f"{{{XBRLDI_NS}}}typedMember",
    }
    ordinary: list[Any] = []
    dimensions: list[Any] = []
    for child in children:
        if not isinstance(child, tuple) or not child:
            ordinary.append(child)
            continue
        normalized = child
        if child[0] in dimension_tags and len(child) >= 2:
            attrs = tuple(
                (
                    "dimension" if name == f"{{{XBRLDI_NS}}}dimension" else name,
                    value,
                )
                for name, value in child[1]
            )
            normalized = (child[0], attrs, *child[2:])
            dimensions.append(normalized)
        else:
            ordinary.append(normalized)
    dimensions.sort(key=repr)
    return tuple((*ordinary, *dimensions))


def _rule_child_text(rule: FormulaAspectRule, local_name: str) -> str | None:
    root = _rule_root(rule)
    if root is None:
        return None
    child = next(
        (
            element
            for element in root
            if isinstance(element.tag, str) and etree.QName(element).localname == local_name
        ),
        None,
    )
    if child is None:
        return None
    return (child.text or "").strip() or None


def _rule_root(rule: FormulaAspectRule) -> etree._Element | None:
    if rule.raw_xml is None:
        return None
    return etree.fromstring(rule.raw_xml)


def _child_local_names(root: etree._Element | None) -> set[str]:
    if root is None:
        return set()
    return {etree.QName(child).localname for child in root if isinstance(child.tag, str)}


def _lexical_qname(value: str, namespaces: dict[str, str]) -> QName | None:
    if value.startswith("{") and "}" in value:
        return QName.from_clark(value)
    if ":" not in value:
        return None
    prefix, local_name = value.split(":", 1)
    namespace = namespaces.get(prefix)
    if namespace is None:
        return None
    return QName(namespace=namespace, local_name=local_name, prefix=prefix)


def _formula_boundary_date(value: Any, *, end_boundary: bool = False) -> date:
    raw_value = getattr(value, "value", value)
    if isinstance(raw_value, date):
        parsed = raw_value
        has_time = raw_value.__class__.__name__.lower().startswith("datetime")
    else:
        lexical = str(raw_value)
        parsed = date.fromisoformat(lexical[:10])
        has_time = "T" in lexical or "datetime" in value.__class__.__name__.lower()
    if end_boundary and not has_time:
        return parsed + timedelta(days=1)
    return parsed


def _unit_factors(unit: XbrlUnit) -> tuple[tuple[QName, ...], tuple[QName, ...]]:
    if unit.unit_form == "divide":
        return unit.numerator_measure_qnames, unit.denominator_measure_qnames
    return unit.simple_measure_qnames, ()


def _cancel_unit_factors(
    numerator: list[QName],
    denominator: list[QName],
) -> tuple[list[QName], list[QName]]:
    reduced_numerator = list(numerator)
    reduced_denominator = list(denominator)
    for measure in tuple(reduced_numerator):
        if measure not in reduced_denominator:
            continue
        reduced_numerator.remove(measure)
        reduced_denominator.remove(measure)
    reduced_numerator.sort(key=lambda item: (item.namespace, item.local_name))
    reduced_denominator.sort(key=lambda item: (item.namespace, item.local_name))
    return reduced_numerator, reduced_denominator


def _expression_needs_fact_nodes(expression: str) -> bool:
    """Use node bindings for expressions that inspect fact-node identity.

    Arithmetic and comparisons receive schema-typed atomic values because the
    lightweight in-memory XML nodes do not carry the source instance PSVI.
    """
    return any(
        token in expression
        for token in (
            "xfi:",
            "node-name(",
            "local-name(",
            "namespace-uri(",
            "name(",
            "/@",
            " | ",
            " intersect ",
            " except ",
            " union ",
        )
    )


def _normalize_qname_expression(expression: str) -> str:
    return re.sub(
        r"namespace-uri\((\$[A-Za-z_][\w:.-]*)\)",
        r"string(namespace-uri(\1))",
        expression,
    )


def _is_uncovered_source(source: str) -> bool:
    return source.rsplit(":", 1)[-1] in {"uncovered", "uncovered-aspect"}


def _select_occ_document_node(
    expression: str,
    source_path: str | None,
) -> etree._Element | None:
    match = re.fullmatch(
        r"\s*doc\(['\"]([^'\"]+)['\"]\)/\*\[1\]/\*\[(\d+)\]\s*",
        expression,
    )
    if match is None or source_path is None:
        return None
    document_path = (Path(source_path).parent / match.group(1)).resolve()
    if not document_path.exists():
        return None
    root = etree.parse(str(document_path)).getroot()
    children = [child for child in root if isinstance(child.tag, str)]
    index = int(match.group(2)) - 1
    if index < 0 or index >= len(children):
        return None
    return deepcopy(children[index])


def _xpath_qname(value: Any, namespaces: dict[str, str]) -> QName | None:
    namespace = getattr(value, "namespace", None)
    local_name = getattr(value, "local_name", None)
    if isinstance(namespace, str) and isinstance(local_name, str):
        return QName(namespace=namespace, local_name=local_name)
    lexical = _xpath_item_string(value)
    if lexical.startswith("{") and "}" in lexical:
        return QName.from_clark(lexical)
    if ":" in lexical:
        prefix, local_name = lexical.split(":", 1)
        namespace = namespaces.get(prefix)
        if namespace is not None:
            return QName(namespace=namespace, local_name=local_name, prefix=prefix)
    return None


def _xpath_item_string(item: Any) -> str:
    value = getattr(item, "value", item)
    if isinstance(value, etree._Element):
        return "".join(value.itertext())
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, Decimal):
        return str(value)
    return str(value)
