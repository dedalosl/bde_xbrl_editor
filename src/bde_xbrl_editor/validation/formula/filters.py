"""Fact filter predicates for formula assertion variable binding."""

from __future__ import annotations

import re
from collections.abc import Mapping
from datetime import date, datetime, time, timedelta
from decimal import Decimal, InvalidOperation
from functools import lru_cache
from typing import Any

from lxml import etree

from bde_xbrl_editor.instance.constants import XBRLI_NS
from bde_xbrl_editor.instance.models import Fact, XbrlInstance
from bde_xbrl_editor.taxonomy.models import (
    BooleanFilterDefinition,
    CustomFunctionDefinition,
    DimensionFilter,
    FactVariableDefinition,
    FormulaFilterResource,
    TypedDimensionFilter,
    XPathFilterDefinition,
)

_PERIOD_FILTER_NS = "http://xbrl.org/2008/filter/period"
_ENTITY_FILTER_NS = "http://xbrl.org/2008/filter/entity"


def apply_filters(
    facts: list[Fact],
    variable_def: FactVariableDefinition,
    instance: XbrlInstance,
    custom_functions: tuple[CustomFunctionDefinition, ...] = (),
    facts_by_concept: dict[object, list[Fact]] | None = None,
    xpath_token_cache: dict[tuple[tuple[tuple[str, str], ...], str], Any] | None = None,
    xpath_variables: dict[str, Any] | None = None,
    dimension_defaults: Mapping[Any, Any] | None = None,
    concepts: Mapping[Any, Any] | None = None,
) -> list[Fact]:
    """Return the subset of facts that satisfy all filters in variable_def.

    Returns an empty list when no facts match. Never raises.
    """
    concept_name_resources = tuple(
        resource
        for resource in variable_def.filter_resources
        if resource.local_name == "conceptName"
    )
    if concept_name_resources:
        result = _apply_concept_name_resources(
            facts,
            concept_name_resources,
            custom_functions=custom_functions,
            xpath_token_cache=xpath_token_cache,
            xpath_variables=xpath_variables,
        )
    elif variable_def.concept_filter is not None:
        cf = variable_def.concept_filter
        if facts_by_concept is not None:
            result = list(facts_by_concept.get(cf, ()))
        else:
            result = [f for f in facts if f.concept == cf]
    else:
        result = list(facts)
    if not variable_def.nils:
        result = [fact for fact in result if not fact.is_nil]

    result = _apply_concept_property_resources(
        result,
        variable_def.filter_resources,
        concepts or {},
        xpath_variables=xpath_variables,
    )

    result = _apply_value_filter_resources(result, variable_def.filter_resources)

    result = _apply_period_filter_resources(
        result,
        variable_def.filter_resources,
        instance,
        xpath_variables=xpath_variables,
    )

    result = _apply_entity_filter_resources(
        result,
        variable_def.filter_resources,
        instance,
        xpath_variables=xpath_variables,
    )

    result = _apply_tuple_location_resources(result, variable_def.filter_resources)

    # Period type filter (simple instant/duration)
    if variable_def.period_filter is not None:
        wanted_period = variable_def.period_filter
        filtered: list[Fact] = []
        for fact in result:
            ctx = instance.contexts.get(fact.context_ref)
            if ctx is None:
                continue
            if ctx.period.period_type == wanted_period:
                filtered.append(fact)
        result = filtered

    # Unit filter
    if variable_def.unit_filter is not None:
        uf = variable_def.unit_filter
        filtered = []
        for fact in result:
            unit = instance.units.get(fact.unit_ref or "")
            if unit is None:
                if variable_def.unit_filter_exclude:
                    filtered.append(fact)
                continue
            matches = (
                unit.unit_form == "simple"
                and unit.simple_measure_count == 1
                and (
                    unit.measure_qname == uf
                    or (unit.measure_qname is None and uf.local_name in unit.measure_uri)
                )
            )
            if matches != variable_def.unit_filter_exclude:
                filtered.append(fact)
        result = filtered

    result = _apply_unit_filter_resources(
        result,
        variable_def.filter_resources,
        instance,
        custom_functions=custom_functions,
        xpath_token_cache=xpath_token_cache,
        xpath_variables=xpath_variables,
    )

    # Dimension filters
    for dim_filter in variable_def.dimension_filters:
        result = [
            fact
            for fact in result
            if _passes_dim_filter(fact, dim_filter, instance, dimension_defaults)
        ]

    # Typed dimension filters
    for typed_filter in variable_def.typed_dimension_filters:
        filtered = []
        for fact in result:
            if _passes_typed_dimension_filter(fact, typed_filter, instance):
                filtered.append(fact)
        result = filtered

    # Boolean filters (bf:andFilter / bf:orFilter)
    for bf in variable_def.boolean_filters:
        result = [
            f
            for f in result
            if _passes_boolean_filter(
                f,
                bf,
                instance,
                custom_functions,
                xpath_token_cache=xpath_token_cache,
                xpath_variables=xpath_variables,
                dimension_defaults=dimension_defaults,
                concepts=concepts,
            )
        ]

    # XPath filters (gf:general test=, pf:period test=)
    xpath_filters = tuple(
        xpath_filter
        for xpath_filter in variable_def.xpath_filters
        if not (concept_name_resources and xpath_filter.filter_type == "concept")
    )
    if xpath_filters:
        result = _apply_xpath_filters(
            result,
            xpath_filters,
            instance,
            custom_functions=custom_functions,
            xpath_token_cache=xpath_token_cache,
            xpath_variables=xpath_variables,
            concepts=concepts or {},
        )

    return result


def _apply_concept_property_resources(
    facts: list[Fact],
    resources: tuple[Any, ...],
    concepts: Mapping[Any, Any],
    *,
    xpath_variables: dict[str, Any] | None,
) -> list[Fact]:
    """Filter facts using concept metadata already loaded from the DTS."""
    filtered = list(facts)
    for resource in resources:
        if resource.local_name == "conceptPeriodType":
            expected = resource.attributes.get("periodType", "")

            def matches_period(fact: Fact, wanted: str = expected) -> bool:
                concept = concepts.get(fact.concept)
                return concept is not None and concept.period_type == wanted

            filtered = [
                fact for fact in filtered if matches_period(fact) != bool(resource.complement)
            ]
        elif resource.local_name == "conceptBalance":
            expected = resource.attributes.get("balance", "")

            def matches_balance(fact: Fact, wanted: str = expected) -> bool:
                concept = concepts.get(fact.concept)
                if concept is None:
                    return False
                return concept.balance is None if wanted == "none" else concept.balance == wanted

            filtered = [
                fact for fact in filtered if matches_balance(fact) != bool(resource.complement)
            ]
        elif resource.local_name == "conceptSubstitutionGroup":
            targets: list[Any] = list(resource.qnames)
            for expression in resource.qname_expressions:
                value = _evaluate_filter_atomic(
                    expression,
                    resource.namespaces,
                    xpath_variables,
                )
                if value is not None:
                    targets.append(value)
            strict = resource.attributes.get("strict", "false").lower() == "true"
            filtered = [
                fact
                for fact in filtered
                if _concept_substitution_group_matches(
                    fact,
                    targets,
                    strict=strict,
                    concepts=concepts,
                )
                != bool(resource.complement)
            ]
        elif resource.local_name == "conceptDataType":
            targets: list[Any] = list(resource.qnames)
            for expression in resource.qname_expressions:
                value = _evaluate_filter_atomic(
                    expression,
                    resource.namespaces,
                    xpath_variables,
                )
                if value is not None:
                    targets.append(value)
            strict = resource.attributes.get("strict", "false").lower() == "true"
            filtered = [
                fact
                for fact in filtered
                if _concept_data_type_matches(
                    fact,
                    targets,
                    strict=strict,
                    concepts=concepts,
                )
                != bool(resource.complement)
            ]
        elif resource.local_name == "conceptCustomAttribute":
            targets: list[Any] = list(resource.qnames)
            for expression in resource.qname_expressions:
                value = _evaluate_filter_atomic(
                    expression,
                    resource.namespaces,
                    xpath_variables,
                )
                if value is not None:
                    targets.append(value)
            has_expected_value = "value" in resource.attributes
            expected_value = _evaluate_filter_atomic(
                resource.attributes.get("value"),
                resource.namespaces,
                xpath_variables,
            )
            filtered = [
                fact
                for fact in filtered
                if _concept_custom_attribute_matches(
                    fact,
                    targets,
                    has_expected_value=has_expected_value,
                    expected_value=expected_value,
                    concepts=concepts,
                )
                != bool(resource.complement)
            ]
    return filtered


def _concept_custom_attribute_matches(
    fact: Fact,
    targets: list[Any],
    *,
    has_expected_value: bool,
    expected_value: Any | None,
    concepts: Mapping[Any, Any],
) -> bool:
    declaration = concepts.get(fact.concept)
    if declaration is None:
        return False
    values = [
        lexical
        for qname, lexical in declaration.custom_attributes
        if any(_qname_matches(target, qname) for target in targets)
    ]
    if not values:
        return False
    if not has_expected_value:
        return True
    return any(_custom_attribute_value_matches(lexical, expected_value) for lexical in values)


def _custom_attribute_value_matches(lexical: str, expected: Any | None) -> bool:
    if isinstance(expected, bool):
        if lexical.strip() in {"true", "1"}:
            return expected is True
        if lexical.strip() in {"false", "0"}:
            return expected is False
        return False
    if isinstance(expected, Decimal):
        try:
            return Decimal(lexical.strip()) == expected
        except InvalidOperation:
            return False
    return expected is not None and lexical == str(expected)


def _concept_data_type_matches(
    fact: Fact,
    targets: list[Any],
    *,
    strict: bool,
    concepts: Mapping[Any, Any],
) -> bool:
    declaration = concepts.get(fact.concept)
    if declaration is None:
        return False
    candidates = (declaration.data_type,)
    if not strict:
        candidates += declaration.data_type_ancestry
    return any(_qname_matches(target, candidate) for target in targets for candidate in candidates)


def _concept_substitution_group_matches(
    fact: Fact,
    targets: list[Any],
    *,
    strict: bool,
    concepts: Mapping[Any, Any],
) -> bool:
    declaration = concepts.get(fact.concept)
    current = declaration.substitution_group if declaration is not None else None
    visited: set[Any] = set()
    while current is not None and current not in visited:
        if any(_qname_matches(target, current) for target in targets):
            return True
        if strict:
            return False
        visited.add(current)
        parent = concepts.get(current)
        current = parent.substitution_group if parent is not None else None
    return False


def _apply_entity_filter_resources(
    facts: list[Fact],
    resources: tuple[Any, ...],
    instance: XbrlInstance,
    *,
    xpath_variables: dict[str, Any] | None,
) -> list[Fact]:
    """Apply entity filters whose tests do not depend on another fact variable."""
    filtered = list(facts)
    for resource in resources:
        if resource.namespace != _ENTITY_FILTER_NS:
            continue
        if resource.local_name not in {
            "specificScheme",
            "regexpScheme",
            "specificIdentifier",
            "regexpIdentifier",
        }:
            continue
        expressions = tuple(resource.attributes.get(name, "") for name in ("scheme", "value"))
        if any("$" in expression for expression in expressions):
            continue

        expected_scheme = _evaluate_filter_atomic(
            resource.attributes.get("scheme"),
            resource.namespaces,
            xpath_variables,
        )
        expected_value = _evaluate_filter_atomic(
            resource.attributes.get("value"),
            resource.namespaces,
            xpath_variables,
        )
        pattern = resource.attributes.get("pattern", "")

        filtered = [
            fact
            for fact in filtered
            if _entity_filter_matches(
                fact,
                resource.local_name,
                expected_scheme,
                expected_value,
                pattern,
                instance,
            )
            != bool(resource.complement)
        ]
    return filtered


def _entity_filter_matches(
    fact: Fact,
    filter_name: str,
    expected_scheme: Any | None,
    expected_value: Any | None,
    pattern: str,
    instance: XbrlInstance,
) -> bool:
    context = instance.contexts.get(fact.context_ref)
    if context is None:
        return False
    entity = context.entity
    if filter_name == "specificScheme":
        return expected_scheme is not None and entity.scheme == str(expected_scheme)
    if filter_name == "specificIdentifier":
        return (
            expected_scheme is not None
            and expected_value is not None
            and entity.scheme == str(expected_scheme)
            and entity.identifier == str(expected_value)
        )
    if not pattern:
        return False
    compared = entity.scheme if filter_name == "regexpScheme" else entity.identifier
    return re.search(pattern, compared) is not None


def _apply_period_filter_resources(
    facts: list[Fact],
    resources: tuple[Any, ...],
    instance: XbrlInstance,
    *,
    xpath_variables: dict[str, Any] | None,
) -> list[Fact]:
    """Apply the specialized Formula period filters retained by the parser."""
    filtered = list(facts)
    period_resources = (
        resource
        for resource in resources
        if resource.namespace == _PERIOD_FILTER_NS
        and resource.local_name in {"periodStart", "periodEnd", "periodInstant", "forever"}
    )
    for resource in period_resources:
        target_date = _evaluate_period_filter_date(
            resource.attributes.get("date"),
            resource.namespaces,
            xpath_variables,
        )
        target_time = _evaluate_period_filter_time(
            resource.attributes.get("time"),
            resource.namespaces,
            xpath_variables,
        )

        filtered = [
            fact
            for fact in filtered
            if _period_filter_matches(
                fact,
                resource.local_name,
                target_date,
                target_time,
                instance,
            )
            != bool(resource.complement)
        ]
    return filtered


def _period_filter_matches(
    fact: Fact,
    filter_name: str,
    target_date: date | None,
    target_time: time | None,
    instance: XbrlInstance,
) -> bool:
    context = instance.contexts.get(fact.context_ref)
    if context is None:
        return False
    period = context.period
    if filter_name == "forever":
        return period.period_type == "forever"
    if target_date is None:
        return False
    if filter_name == "periodStart":
        boundary = period.start_date if period.period_type == "duration" else None
    elif filter_name == "periodEnd":
        boundary = period.end_date if period.period_type == "duration" else None
        if boundary is not None and target_time is not None and period.end_date_only:
            boundary += timedelta(days=1)
    else:
        boundary = period.instant_date if period.period_type == "instant" else None
        if boundary is not None and target_time is not None and period.instant_date_only:
            boundary += timedelta(days=1)
    if boundary is None:
        return False
    if target_time is None:
        return boundary == target_date
    return datetime.combine(boundary, time.min) == datetime.combine(target_date, target_time)


def _evaluate_period_filter_date(
    expression: str | None,
    namespaces: dict[str, str],
    xpath_variables: dict[str, Any] | None,
) -> date | None:
    value = _evaluate_filter_atomic(expression, namespaces, xpath_variables)
    if value is None:
        return None
    try:
        return date.fromisoformat(str(value).split("T", 1)[0])
    except ValueError:
        return None


def _evaluate_period_filter_time(
    expression: str | None,
    namespaces: dict[str, str],
    xpath_variables: dict[str, Any] | None,
) -> time | None:
    value = _evaluate_filter_atomic(expression, namespaces, xpath_variables)
    if value is None:
        return None
    lexical = str(value).removesuffix("Z").split("+", 1)[0]
    try:
        return time.fromisoformat(lexical).replace(tzinfo=None)
    except ValueError:
        return None


def _evaluate_filter_atomic(
    expression: str | None,
    namespaces: dict[str, str],
    xpath_variables: dict[str, Any] | None,
) -> Any | None:
    if not expression:
        return None
    import elementpath  # type: ignore[import-untyped]

    from bde_xbrl_editor.validation.formula.xfi_functions import build_formula_parser

    try:
        token = build_formula_parser(namespaces).parse(expression)
        values = list(
            token.select(elementpath.XPathContext(item="", variables=xpath_variables or {}))
        )
        return values[0] if len(values) == 1 else None
    except Exception:  # noqa: BLE001
        return None


def _apply_value_filter_resources(
    facts: list[Fact],
    resources: tuple[Any, ...],
) -> list[Fact]:
    """Apply value filters that operate on attributes already parsed on facts."""
    filtered = list(facts)
    for resource in resources:
        if resource.local_name == "nil":
            filtered = [fact for fact in filtered if fact.is_nil != bool(resource.complement)]
        elif resource.local_name == "precision":
            try:
                minimum = int(resource.attributes.get("minimum", ""))
            except (TypeError, ValueError):
                filtered = [] if not resource.complement else filtered
                continue

            def matches(fact: Fact, threshold: int = minimum) -> bool:
                if fact.unit_ref is None or fact.precision is None:
                    return False
                if fact.precision.upper() == "INF":
                    return True
                try:
                    return int(fact.precision) >= threshold
                except ValueError:
                    return False

            filtered = [fact for fact in filtered if matches(fact) != bool(resource.complement)]
    return filtered


def _apply_unit_filter_resources(
    facts: list[Fact],
    resources: tuple[Any, ...],
    instance: XbrlInstance,
    *,
    custom_functions: tuple[CustomFunctionDefinition, ...],
    xpath_token_cache: dict[tuple[tuple[tuple[str, str], ...], str], Any] | None,
    xpath_variables: dict[str, Any] | None,
) -> list[Fact]:
    """Apply executable unit-filter resources retained by the Formula parser."""
    import elementpath  # type: ignore[import-untyped]

    filtered = list(facts)
    for resource in resources:
        if resource.local_name == "generalMeasures":
            filtered = _apply_general_measures_resource(
                filtered,
                resource,
                instance,
                custom_functions=custom_functions,
                xpath_variables=xpath_variables,
            )
            continue
        if resource.local_name != "singleMeasure":
            continue
        qname_values: list[Any] = list(resource.qnames)
        for expression in resource.qname_expressions:
            xpath_filter = XPathFilterDefinition(
                xpath_expr=expression,
                namespaces=resource.namespaces,
                filter_type="unit",
            )
            try:
                token = _get_xpath_filter_token(
                    xpath_filter,
                    custom_functions=custom_functions,
                    xpath_token_cache=xpath_token_cache,
                )
                context = elementpath.XPathContext(
                    root=None,
                    item=True,
                    variables=xpath_variables or {},
                )
                qname_values.extend(token.select(context))
            except Exception:  # noqa: BLE001
                continue

        def matches(fact: Fact, values: tuple[Any, ...] = tuple(qname_values)) -> bool:
            unit = instance.units.get(fact.unit_ref or "")
            if unit is None or unit.unit_form != "simple" or unit.simple_measure_count != 1:
                return False
            return any(_qname_matches(value, unit.measure_qname) for value in values)

        filtered = [fact for fact in filtered if matches(fact) != bool(resource.complement)]
    return filtered


def _apply_general_measures_resource(
    facts: list[Fact],
    resource: Any,
    instance: XbrlInstance,
    *,
    custom_functions: tuple[CustomFunctionDefinition, ...],
    xpath_variables: dict[str, Any] | None,
) -> list[Fact]:
    """Evaluate ``uf:generalMeasures/@test`` with the unit as context item."""
    import elementpath  # type: ignore[import-untyped]

    if not resource.test_xpath:
        return [] if not resource.complement else list(facts)
    from bde_xbrl_editor.validation.formula.xfi_functions import build_formula_parser

    try:
        schema = _unit_schema_proxy()
        parser = build_formula_parser(
            resource.namespaces,
            custom_functions,
            (resource.test_xpath,),
            schema=schema,
        )
        token = parser.parse(resource.test_xpath)
    except Exception:  # noqa: BLE001
        return [] if not resource.complement else list(facts)

    passed: list[Fact] = []
    for fact in facts:
        unit = instance.units.get(fact.unit_ref or "")
        if unit is None:
            matches = False
        else:
            try:
                unit_element = _unit_xpath_element(unit, resource.namespaces)
                context = elementpath.XPathContext(
                    root=unit_element,
                    item=unit_element,
                    schema=schema,
                    variables=xpath_variables or {},
                )
                matches = _to_bool(list(token.select(context)))
            except Exception:  # noqa: BLE001
                matches = False
        if matches != bool(resource.complement):
            passed.append(fact)
    return passed


@lru_cache(maxsize=1)
def _unit_schema_proxy() -> Any:
    """Return a minimal schema proxy that preserves xbrli:measure as xs:QName."""
    import xmlschema  # type: ignore[import-untyped]
    from xmlschema.xpath import XMLSchemaProxy  # type: ignore[import-untyped]

    schema_text = f"""<xs:schema xmlns:xs="http://www.w3.org/2001/XMLSchema"
        xmlns:xbrli="{XBRLI_NS}" targetNamespace="{XBRLI_NS}"
        elementFormDefault="qualified">
      <xs:complexType name="measuresType"><xs:sequence>
        <xs:element name="measure" type="xs:QName" maxOccurs="unbounded"/>
      </xs:sequence></xs:complexType>
      <xs:element name="unit"><xs:complexType><xs:choice>
        <xs:element name="measure" type="xs:QName" maxOccurs="unbounded"/>
        <xs:element name="divide"><xs:complexType><xs:sequence>
          <xs:element name="unitNumerator" type="xbrli:measuresType"/>
          <xs:element name="unitDenominator" type="xbrli:measuresType"/>
        </xs:sequence></xs:complexType></xs:element>
      </xs:choice></xs:complexType></xs:element>
    </xs:schema>"""
    return XMLSchemaProxy(xmlschema.XMLSchema(schema_text))


def _unit_xpath_element(unit: Any, namespaces: dict[str, str]) -> etree._Element:
    measures = (
        unit.simple_measure_qnames
        if unit.unit_form == "simple"
        else unit.numerator_measure_qnames + unit.denominator_measure_qnames
    )
    nsmap = {prefix: namespace for prefix, namespace in namespaces.items() if prefix}
    nsmap.setdefault("xbrli", XBRLI_NS)
    prefixes_by_namespace = {namespace: prefix for prefix, namespace in nsmap.items()}
    for index, measure in enumerate(measures):
        if measure.namespace and measure.namespace not in prefixes_by_namespace:
            prefix = f"measure{index}"
            nsmap[prefix] = measure.namespace
            prefixes_by_namespace[measure.namespace] = prefix

    root = etree.Element(f"{{{XBRLI_NS}}}unit", nsmap=nsmap)

    def append_measure(parent: etree._Element, measure: Any) -> None:
        element = etree.SubElement(parent, f"{{{XBRLI_NS}}}measure")
        prefix = prefixes_by_namespace.get(measure.namespace)
        element.text = f"{prefix}:{measure.local_name}" if prefix else measure.local_name

    if unit.unit_form == "simple":
        for measure in unit.simple_measure_qnames:
            append_measure(root, measure)
        return root

    divide = etree.SubElement(root, f"{{{XBRLI_NS}}}divide")
    numerator = etree.SubElement(divide, f"{{{XBRLI_NS}}}unitNumerator")
    denominator = etree.SubElement(divide, f"{{{XBRLI_NS}}}unitDenominator")
    for measure in unit.numerator_measure_qnames:
        append_measure(numerator, measure)
    for measure in unit.denominator_measure_qnames:
        append_measure(denominator, measure)
    return root


def _apply_tuple_location_resources(
    facts: list[Fact],
    resources: tuple[Any, ...],
) -> list[Fact]:
    """Apply tuple ancestor/parent filters using parser-preserved ancestry."""
    filtered = list(facts)
    document_root = (XBRLI_NS, "xbrl")
    for resource in resources:
        if resource.local_name not in {"ancestorFilter", "parentFilter"}:
            continue
        wanted = {(qname.namespace, qname.local_name) for qname in resource.qnames}
        if not wanted:
            continue

        def matches(
            fact: Fact,
            *,
            filter_name: str = resource.local_name,
            wanted_qnames: set[tuple[str, str]] = wanted,
        ) -> bool:
            ancestors = fact.tuple_ancestor_concepts
            if filter_name == "parentFilter":
                actual = (
                    (ancestors[-1].namespace, ancestors[-1].local_name)
                    if ancestors
                    else document_root
                )
                return actual in wanted_qnames
            return document_root in wanted_qnames or any(
                (ancestor.namespace, ancestor.local_name) in wanted_qnames for ancestor in ancestors
            )

        filtered = [fact for fact in filtered if matches(fact) != bool(resource.complement)]
    return filtered


def _apply_concept_name_resources(
    facts: list[Fact],
    resources: tuple[Any, ...],
    *,
    custom_functions: tuple[CustomFunctionDefinition, ...],
    xpath_token_cache: dict[tuple[tuple[tuple[str, str], ...], str], Any] | None,
    xpath_variables: dict[str, Any] | None,
) -> list[Fact]:
    """Apply each concept-name filter, unioning its internal alternatives."""
    import elementpath  # type: ignore[import-untyped]

    filtered = list(facts)
    for resource in resources:
        qname_values: list[Any] = list(resource.qnames)
        for expression in resource.qname_expressions:
            xpath_filter = XPathFilterDefinition(
                xpath_expr=expression,
                namespaces=resource.namespaces,
                filter_type="concept",
            )
            try:
                token = _get_xpath_filter_token(
                    xpath_filter,
                    custom_functions=custom_functions,
                    xpath_token_cache=xpath_token_cache,
                )
                context = elementpath.XPathContext(
                    root=None,
                    item=True,
                    variables=xpath_variables or {},
                )
                qname_values.extend(token.select(context))
            except Exception:  # noqa: BLE001
                continue
        filtered = [
            fact
            for fact in filtered
            if any(_qname_matches_fact(value, fact) for value in qname_values)
            != bool(resource.complement)
        ]
    return filtered


def _passes_dim_filter(
    fact: Fact,
    dim_filter: DimensionFilter,
    instance: XbrlInstance,
    dimension_defaults: Mapping[Any, Any] | None = None,
) -> bool:
    """Return True if *fact* satisfies a single DimensionFilter."""
    ctx = instance.contexts.get(fact.context_ref)
    if ctx is None:
        return False
    member = ctx.dimensions.get(
        dim_filter.dimension_qname,
        (dimension_defaults or {}).get(dim_filter.dimension_qname),
    )
    if dim_filter.exclude:
        if dim_filter.member_qnames:
            return member not in dim_filter.member_qnames
        return member is None
    else:
        if dim_filter.member_qnames:
            return member in dim_filter.member_qnames
        return member is not None


def _passes_typed_dimension_filter(
    fact: Fact,
    typed_filter: TypedDimensionFilter,
    instance: XbrlInstance,
) -> bool:
    ctx = instance.contexts.get(fact.context_ref)
    if ctx is None:
        return False
    present = typed_filter.dimension_qname in (getattr(ctx, "typed_dimensions", {}) or {})
    return not present if typed_filter.exclude else present


def _passes_boolean_filter(
    fact: Fact,
    bf: BooleanFilterDefinition,
    instance: XbrlInstance,
    custom_functions: tuple[CustomFunctionDefinition, ...] = (),
    xpath_token_cache: dict[tuple[tuple[tuple[str, str], ...], str], Any] | None = None,
    xpath_variables: dict[str, Any] | None = None,
    dimension_defaults: Mapping[Any, Any] | None = None,
    concepts: Mapping[Any, Any] | None = None,
) -> bool:
    """Return True if *fact* satisfies the boolean filter tree rooted at *bf*."""
    child_results: list[bool] = []
    for child in bf.children:
        if isinstance(child, DimensionFilter):
            child_results.append(_passes_dim_filter(fact, child, instance, dimension_defaults))
        elif isinstance(child, TypedDimensionFilter):
            child_results.append(_passes_typed_dimension_filter(fact, child, instance))
        elif isinstance(child, BooleanFilterDefinition):
            child_results.append(
                _passes_boolean_filter(
                    fact,
                    child,
                    instance,
                    custom_functions,
                    xpath_token_cache=xpath_token_cache,
                    xpath_variables=xpath_variables,
                    dimension_defaults=dimension_defaults,
                    concepts=concepts,
                )
            )
        elif isinstance(child, XPathFilterDefinition):
            passed_list = _apply_xpath_filters(
                [fact],
                (child,),
                instance,
                custom_functions=custom_functions,
                xpath_token_cache=xpath_token_cache,
                xpath_variables=xpath_variables,
            )  # type: ignore[arg-type]
            child_results.append(bool(passed_list))
        elif isinstance(child, FormulaFilterResource):
            child_variable = FactVariableDefinition(
                variable_name="",
                nils=True,
                filter_resources=(child,),
            )
            child_results.append(
                bool(
                    apply_filters(
                        [fact],
                        child_variable,
                        instance,
                        custom_functions=custom_functions,
                        xpath_token_cache=xpath_token_cache,
                        xpath_variables=xpath_variables,
                        dimension_defaults=dimension_defaults,
                        concepts=concepts,
                    )
                )
            )

    if not child_results:
        passes = False
    elif bf.filter_type == "and":
        passes = all(child_results)
    else:  # "or"
        passes = any(child_results)

    return (not passes) if bf.complement else passes


def _apply_xpath_filters(
    facts: list[Fact],
    xpath_filters: tuple,
    instance: XbrlInstance,
    custom_functions: tuple[CustomFunctionDefinition, ...] = (),
    xpath_token_cache: dict[tuple[tuple[tuple[str, str], ...], str], Any] | None = None,
    xpath_variables: dict[str, Any] | None = None,
    concepts: Mapping[Any, Any] | None = None,
) -> list[Fact]:
    """Apply each XPath filter expression to every candidate fact.

    The context item for filter evaluation is the fact's numeric value as
    a Decimal (e.g. ``. le 0.1`` in gf:general filters).  For period-based
    filters (pf:period test=) xfi: functions read the period via the global
    evaluation context set here.

    A fact passes if ALL XPath filter expressions evaluate to true.
    Facts for which any filter raises an exception are excluded.
    """
    import elementpath  # type: ignore[import-untyped]

    from bde_xbrl_editor.validation.formula.xfi_functions import (
        clear_evaluation_context,
        set_evaluation_context,
    )

    passed: list[Fact] = []
    for fact in facts:
        ctx_obj = instance.contexts.get(fact.context_ref)
        unit_obj = instance.units.get(fact.unit_ref or "") if fact.unit_ref else None

        set_evaluation_context(
            {
                "_all_facts": instance.facts,
                "_current_fact": fact,
                "_context": ctx_obj,
                "_unit": unit_obj,
                "_instance": instance,
                "_custom_functions": custom_functions,
            }
        )

        try:
            fact_passes = True
            for xf in xpath_filters:
                try:
                    token = _get_xpath_filter_token(
                        xf,
                        custom_functions=custom_functions,
                        xpath_token_cache=xpath_token_cache,
                    )
                    filter_item = _general_filter_context_item(
                        fact,
                        xf.xpath_expr,
                        concepts or {},
                    )
                    filter_root = None
                    if xf.filter_type in {"segment", "scenario"}:
                        context_xml = (
                            ctx_obj.segment_xml
                            if ctx_obj is not None and xf.filter_type == "segment"
                            else ctx_obj.scenario_xml
                            if ctx_obj is not None
                            else None
                        )
                        if context_xml is None:
                            fact_passes = False
                            break
                        filter_item = etree.fromstring(context_xml)
                        filter_root = filter_item
                    elif xf.filter_type == "entity":
                        if ctx_obj is None:
                            fact_passes = False
                            break
                        filter_item = ctx_obj.entity.identifier
                    xp_ctx = elementpath.XPathContext(
                        root=filter_root,
                        item=filter_item,
                        variables=xpath_variables or {},
                    )
                    result = list(token.select(xp_ctx))
                    if xf.filter_type == "concept":
                        matches = bool(result) and _qname_matches_fact(result[0], fact)
                        if matches == xf.complement:
                            fact_passes = False
                            break
                    elif _to_bool(result) == xf.complement:
                        fact_passes = False
                        break
                except Exception:  # noqa: BLE001
                    if xf.filter_type in {"concept", "segment", "scenario"}:
                        fact_passes = False
                        break
            if fact_passes:
                passed.append(fact)
        finally:
            clear_evaluation_context()

    return passed


def _general_filter_context_item(
    fact: Fact,
    xpath_expr: str,
    concepts: Mapping[Any, Any],
) -> object:
    """Return the XDM context item required by a general-filter expression."""
    if fact.source_element_xml is not None and (
        re.search(r"(?:^|[^\w])@", xpath_expr) or re.search(r"\btext\s*\(", xpath_expr)
    ):
        return etree.fromstring(fact.source_element_xml)

    concept = concepts.get(fact.concept)
    type_name = concept.data_type.local_name.lower() if concept is not None else ""
    if "qname" in type_name and ":" in fact.value:
        prefix, _local_name = fact.value.split(":", 1)
        namespace = ""
        if fact.source_element_xml is not None:
            namespace = etree.fromstring(fact.source_element_xml).nsmap.get(prefix, "")
        if namespace:
            try:
                from elementpath.datatypes import (
                    QName as XPathQName,  # type: ignore[import-untyped]
                )

                return XPathQName(namespace, fact.value)
            except (ImportError, TypeError, ValueError):
                pass
        return fact.value
    if "string" in type_name:
        return fact.value or ""
    if "boolean" in type_name:
        return fact.value.strip() in {"true", "1"}
    try:
        return Decimal(fact.value)
    except (InvalidOperation, TypeError):
        return fact.value or ""


def _qname_matches_fact(value: Any, fact: Fact) -> bool:
    return _qname_matches(value, fact.concept)


def _qname_matches(value: Any, qname: Any) -> bool:
    if qname is None:
        return False
    namespace = getattr(value, "namespace", None)
    local_name = getattr(value, "local_name", None)
    if namespace is not None and local_name is not None:
        return str(namespace) == qname.namespace and str(local_name) == qname.local_name
    text = str(value)
    clark = f"{{{qname.namespace}}}{qname.local_name}"
    return text == str(qname) or text == clark


def _get_xpath_filter_token(
    xpath_filter: XPathFilterDefinition,
    *,
    custom_functions: tuple[CustomFunctionDefinition, ...],
    xpath_token_cache: dict[tuple[tuple[tuple[str, str], ...], str], Any] | None,
) -> Any:
    from bde_xbrl_editor.validation.formula.xfi_functions import (
        build_formula_parser,
        normalize_formula_xpath_expression,
    )

    namespace_items = tuple(sorted((xpath_filter.namespaces or {}).items()))
    cache_key = (namespace_items, xpath_filter.xpath_expr)
    if xpath_token_cache is not None:
        cached = xpath_token_cache.get(cache_key)
        if cached is not None:
            return cached

    parser = build_formula_parser(
        dict(namespace_items),
        custom_functions=custom_functions,
        expression_hints=(xpath_filter.xpath_expr,),
    )
    token = parser.parse(normalize_formula_xpath_expression(xpath_filter.xpath_expr))
    if xpath_token_cache is not None:
        xpath_token_cache[cache_key] = token
    return token


def _to_bool(value: object) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, list):
        if not value:
            return False
        first = value[0]
        if isinstance(first, bool):
            return first
        return bool(first)
    if isinstance(value, str):
        return value.lower() not in ("", "false", "0")
    return bool(value)
