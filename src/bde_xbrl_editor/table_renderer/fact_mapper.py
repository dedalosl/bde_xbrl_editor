"""FactMapper — maps CellCoordinate to instance facts."""

from __future__ import annotations

from typing import TYPE_CHECKING

from bde_xbrl_editor.instance.constants import BDE_DIM_NS
from bde_xbrl_editor.table_renderer.models import CellCoordinate, FactMatchResult
from bde_xbrl_editor.taxonomy.models import QName

if TYPE_CHECKING:
    from bde_xbrl_editor.instance.models import XbrlInstance
    from bde_xbrl_editor.taxonomy.models import TaxonomyStructure

# BDE Agrupacion is a report-level segment dimension set on the XBRL instance context
# to declare the consolidation scope.  It is absent from all table definition linkbases
# so it must be stripped from fact contexts before dimension matching.
_AGRUPACION_DIM = QName(namespace=BDE_DIM_NS, local_name="Agrupacion")


class FactMapper:
    """Maps a CellCoordinate to instance facts by matching concept + dimensions."""

    def __init__(self, taxonomy: TaxonomyStructure) -> None:
        self._taxonomy = taxonomy

    def _normalize_dimensions(self, dims: dict[QName, QName]) -> dict[QName, QName]:
        """Treat default-member dimensions as equivalent to being absent."""
        normalized: dict[QName, QName] = {}
        for dim_qname, member_qname in dims.items():
            dim_model = self._taxonomy.dimensions.get(dim_qname)
            if dim_model is not None and dim_model.default_member == member_qname:
                continue
            normalized[dim_qname] = member_qname
        return normalized

    def match(self, coordinate: CellCoordinate, instance: XbrlInstance) -> FactMatchResult:
        """Match coordinate against instance facts.

        Matching rules:
        - concept must match (if coordinate.concept is None, no match)
        - all explicit_dimensions in the coordinate must be present in the fact's
          context with the same member values
        - the fact context's Agrupacion dimension is stripped before comparison —
          it is a BDE instance-level segment dimension not declared in any table
          definition linkbase and must never influence cell matching
        - period_override and entity_override are used if set
        """
        if coordinate.concept is None:
            return FactMatchResult(matched=False, duplicate_count=0)

        matching = []
        for fact in instance.facts:
            if fact.concept != coordinate.concept:
                continue
            context = instance.contexts.get(fact.context_ref)
            if context is None:
                continue
            # Strip Agrupacion before matching — it is not a table axis
            fact_dims = {
                dim: mem
                for dim, mem in (context.dimensions if hasattr(context, "dimensions") else {}).items()
                if dim != _AGRUPACION_DIM
            }
            fact_dims = self._normalize_dimensions(fact_dims)
            coord_dims = self._normalize_dimensions(coordinate.explicit_dimensions or {})
            # Exact match: fact dimensions (after stripping Agrupacion) must equal
            # coordinate dimensions exactly — not just a subset. A fact with extra
            # dimensions would belong to a different (more specific) table cell.
            if set(fact_dims.keys()) != set(coord_dims.keys()):
                continue
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
        # Multiple matches — true table-level duplicate
        fact = matching[0]
        return FactMatchResult(
            matched=True,
            fact_value=fact.value,
            fact_decimals=fact.decimals,
            duplicate_count=count,
        )
