"""FactMapper — maps CellCoordinate to instance facts."""

from __future__ import annotations

from typing import TYPE_CHECKING

from bde_xbrl_editor.table_renderer.models import CellCoordinate, FactMatchResult

if TYPE_CHECKING:
    from bde_xbrl_editor.instance.models import XbrlInstance
    from bde_xbrl_editor.taxonomy.models import TaxonomyStructure


class FactMapper:
    """Maps a CellCoordinate to instance facts by matching concept + dimensions."""

    def __init__(self, taxonomy: TaxonomyStructure) -> None:
        self._taxonomy = taxonomy

    def match(self, coordinate: CellCoordinate, instance: XbrlInstance) -> FactMatchResult:
        """Match coordinate against instance facts.

        Matching rules:
        - concept must match (if coordinate.concept is None, no match)
        - all explicit_dimensions must match
        - period_override and entity_override are used if set
        """
        if coordinate.concept is None:
            return FactMatchResult(matched=False, duplicate_count=0)

        matching = []
        for fact in instance.facts:
            if fact.concept != coordinate.concept:
                continue
            # Check explicit dimensions — fact's context must match exactly:
            # all coordinate dims must be present with correct values AND
            # the fact's context must not carry extra dimensions absent from coordinate.
            context = instance.contexts.get(fact.context_ref)
            if context is None:
                continue
            fact_dims = context.dimensions if hasattr(context, "dimensions") else {}
            coord_dims = coordinate.explicit_dimensions or {}
            # All coordinate dims must be satisfied by the fact's context.
            # Extra dimensions in the fact context (e.g. report-level meta-dimensions
            # like Agrupacion, or period selectors like MCY that are not axes of this
            # particular table) are intentionally ignored — the table only constrains
            # the dimensions it declares as axes.
            match = True
            for dim, expected_mem in coord_dims.items():
                if fact_dims.get(dim) != expected_mem:
                    match = False
                    break
            if not match:
                continue
            matching.append(fact)

        count = len(matching)
        if count == 0:
            return FactMatchResult(matched=False, duplicate_count=0)
        if count == 1:
            fact = matching[0]
            return FactMatchResult(
                matched=True,
                fact_value=fact.value,
                fact_decimals=fact.decimals,
                duplicate_count=1,
            )
        # Multiple matches — duplicate
        fact = matching[0]
        return FactMatchResult(
            matched=True,
            fact_value=fact.value,
            fact_decimals=fact.decimals,
            duplicate_count=count,
        )
