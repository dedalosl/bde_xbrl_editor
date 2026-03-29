"""Fact filter predicates for formula assertion variable binding."""

from __future__ import annotations

from bde_xbrl_editor.instance.models import Fact, XbrlInstance
from bde_xbrl_editor.taxonomy.models import FactVariableDefinition, QName


def apply_filters(
    facts: list[Fact],
    variable_def: FactVariableDefinition,
    instance: XbrlInstance,
) -> list[Fact]:
    """Return the subset of facts that satisfy all filters in variable_def.

    Returns an empty list when no facts match. Never raises.
    """
    result = list(facts)

    # Concept filter
    if variable_def.concept_filter is not None:
        cf = variable_def.concept_filter
        result = [f for f in result if f.concept == cf]

    # Period type filter
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
            member = ctx_dims.get(dim_filter.dimension_qname)

            if dim_filter.exclude:
                # Excluded: must NOT have any of the listed members
                if dim_filter.member_qnames:
                    if member in dim_filter.member_qnames:
                        continue  # excluded member found — skip fact
                filtered.append(fact)
            else:
                # Include: must have one of the listed members (or any member if list is empty)
                if dim_filter.member_qnames:
                    if member in dim_filter.member_qnames:
                        filtered.append(fact)
                else:
                    # Any member of this dimension
                    if member is not None:
                        filtered.append(fact)
        result = filtered

    return result
