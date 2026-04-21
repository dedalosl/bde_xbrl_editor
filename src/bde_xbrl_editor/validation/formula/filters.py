"""Fact filter predicates for formula assertion variable binding."""

from __future__ import annotations

import contextlib
from decimal import Decimal, InvalidOperation

from bde_xbrl_editor.instance.models import Fact, XbrlInstance
from bde_xbrl_editor.taxonomy.models import (
    BooleanFilterDefinition,
    CustomFunctionDefinition,
    DimensionFilter,
    FactVariableDefinition,
    XPathFilterDefinition,
)


def apply_filters(
    facts: list[Fact],
    variable_def: FactVariableDefinition,
    instance: XbrlInstance,
    custom_functions: tuple[CustomFunctionDefinition, ...] = (),
) -> list[Fact]:
    """Return the subset of facts that satisfy all filters in variable_def.

    Returns an empty list when no facts match. Never raises.
    """
    result = list(facts)

    # Concept filter
    if variable_def.concept_filter is not None:
        cf = variable_def.concept_filter
        result = [f for f in result if f.concept == cf]

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
                continue
            # Match by measure URI containing the local_name
            if uf.local_name in unit.measure_uri:
                filtered.append(fact)
        result = filtered

    # Dimension filters
    for dim_filter in variable_def.dimension_filters:
        filtered = []
        for fact in result:
            ctx = instance.contexts.get(fact.context_ref)
            if ctx is None:
                continue
            ctx_dims = ctx.dimensions

            if dim_filter.exclude:
                if dim_filter.member_qnames and ctx_dims.get(dim_filter.dimension_qname) in dim_filter.member_qnames:
                    continue
                filtered.append(fact)
            else:
                member = ctx_dims.get(dim_filter.dimension_qname)
                if dim_filter.member_qnames:
                    if member in dim_filter.member_qnames:
                        filtered.append(fact)
                else:
                    if member is not None:
                        filtered.append(fact)
        result = filtered

    # Boolean filters (bf:andFilter / bf:orFilter)
    for bf in variable_def.boolean_filters:
        result = [
            f for f in result
            if _passes_boolean_filter(f, bf, instance, custom_functions)
        ]

    # XPath filters (gf:general test=, pf:period test=)
    if variable_def.xpath_filters:
        result = _apply_xpath_filters(
            result,
            variable_def.xpath_filters,
            instance,
            custom_functions=custom_functions,
        )

    return result


def _passes_dim_filter(fact: Fact, dim_filter: DimensionFilter, instance: XbrlInstance) -> bool:
    """Return True if *fact* satisfies a single DimensionFilter."""
    ctx = instance.contexts.get(fact.context_ref)
    if ctx is None:
        return False
    member = ctx.dimensions.get(dim_filter.dimension_qname)
    if dim_filter.exclude:
        if dim_filter.member_qnames:
            return member not in dim_filter.member_qnames
        return member is None
    else:
        if dim_filter.member_qnames:
            return member in dim_filter.member_qnames
        return member is not None


def _passes_boolean_filter(
    fact: Fact,
    bf: BooleanFilterDefinition,
    instance: XbrlInstance,
    custom_functions: tuple[CustomFunctionDefinition, ...] = (),
) -> bool:
    """Return True if *fact* satisfies the boolean filter tree rooted at *bf*."""
    child_results: list[bool] = []
    for child in bf.children:
        if isinstance(child, DimensionFilter):
            child_results.append(_passes_dim_filter(fact, child, instance))
        elif isinstance(child, BooleanFilterDefinition):
            child_results.append(_passes_boolean_filter(fact, child, instance, custom_functions))
        elif isinstance(child, XPathFilterDefinition):
            passed_list = _apply_xpath_filters(
                [fact],
                (child,),
                instance,
                custom_functions=custom_functions,
            )  # type: ignore[arg-type]
            child_results.append(bool(passed_list))

    if not child_results:
        passes = True  # vacuously true
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
) -> list[Fact]:
    """Apply each XPath filter expression to every candidate fact.

    The context item for filter evaluation is the fact's numeric value as
    a Decimal (e.g. ``. le 0.1`` in gf:general filters).  For period-based
    filters (pf:period test=) xfi: functions read the period via the global
    evaluation context set here.

    A fact passes if ALL XPath filter expressions evaluate to true.
    Facts for which any filter raises an exception are excluded.
    """
    from bde_xbrl_editor.validation.formula.xfi_functions import (
        build_formula_parser,
        clear_evaluation_context,
        set_evaluation_context,
    )
    import elementpath  # type: ignore[import-untyped]

    passed: list[Fact] = []
    for fact in facts:
        ctx_obj = instance.contexts.get(fact.context_ref)
        unit_obj = instance.units.get(fact.unit_ref or "") if fact.unit_ref else None

        # Coerce fact value to Decimal for arithmetic filters; fallback to 0
        try:
            item_value: object = Decimal(fact.value)
        except (InvalidOperation, TypeError):
            item_value = fact.value or ""

        set_evaluation_context({
            "_all_facts": instance.facts,
            "_current_fact": fact,
            "_context": ctx_obj,
            "_unit": unit_obj,
            "_instance": instance,
            "_custom_functions": custom_functions,
        })

        try:
            fact_passes = True
            for xf in xpath_filters:
                with contextlib.suppress(Exception):
                    parser = build_formula_parser(
                        xf.namespaces,
                        custom_functions=custom_functions,
                        expression_hints=(xf.xpath_expr,),
                    )
                    token = parser.parse(xf.xpath_expr)
                    xp_ctx = elementpath.XPathContext(root=None, item=item_value)
                    result = list(token.select(xp_ctx))
                    # Evaluate result as boolean
                    if not _to_bool(result):
                        fact_passes = False
                        break
            if fact_passes:
                passed.append(fact)
        finally:
            clear_evaluation_context()

    return passed


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
