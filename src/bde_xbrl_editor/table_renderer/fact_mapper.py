"""FactMapper — maps CellCoordinate to instance facts."""

from __future__ import annotations

from collections import defaultdict
from typing import TYPE_CHECKING

from bde_xbrl_editor.instance.constants import BDE_DIM_NS
from bde_xbrl_editor.table_renderer.models import CellCoordinate, FactMatchResult
from bde_xbrl_editor.taxonomy.models import QName

if TYPE_CHECKING:
    from bde_xbrl_editor.instance.models import Fact, XbrlInstance
    from bde_xbrl_editor.taxonomy.models import TaxonomyStructure

# BDE Agrupacion is a report-level segment dimension set on the XBRL instance context
# to declare the consolidation scope.  It is absent from all table definition linkbases
# so it must be stripped from fact contexts before dimension matching.
_AGRUPACION_DIM = QName(namespace=BDE_DIM_NS, local_name="Agrupacion")
_DimsKey = frozenset[tuple[QName, QName]]


class FactMapper:
    """Maps a CellCoordinate to instance facts by matching concept + dimensions."""

    def __init__(self, taxonomy: TaxonomyStructure) -> None:
        self._taxonomy = taxonomy
        self._indexed_instance_id: int | None = None
        self._fact_index: dict[QName, dict[_DimsKey, list[Fact]]] = {}

    def _normalize_dimensions(self, dims: dict[QName, QName]) -> dict[QName, QName]:
        """Treat default-member dimensions as equivalent to being absent."""
        normalized: dict[QName, QName] = {}
        for dim_qname, member_qname in dims.items():
            dim_model = self._taxonomy.dimensions.get(dim_qname)
            if dim_model is not None and dim_model.default_member == member_qname:
                continue
            normalized[dim_qname] = member_qname
        return normalized

    @staticmethod
    def _strip_agrupacion(dims: dict[QName, QName]) -> dict[QName, QName]:
        """Return dimensions without the report-level Agrupacion axis."""
        return {dim: mem for dim, mem in dims.items() if dim != _AGRUPACION_DIM}

    def _dims_key(self, dims: dict[QName, QName]) -> _DimsKey:
        """Build a hashable key for exact-dimension matching."""
        return frozenset(self._normalize_dimensions(dims).items())

    def _ensure_index(self, instance: XbrlInstance) -> None:
        """Build a concept+dimension index once per instance for fast cell lookups."""
        current_instance_id = id(instance)
        if self._indexed_instance_id == current_instance_id:
            return

        index: dict[QName, dict[_DimsKey, list[Fact]]] = defaultdict(lambda: defaultdict(list))
        for fact in instance.facts:
            context = instance.contexts.get(fact.context_ref)
            if context is None:
                continue
            raw_dims = context.dimensions if hasattr(context, "dimensions") else {}
            dims_key = self._dims_key(self._strip_agrupacion(raw_dims or {}))
            index[fact.concept][dims_key].append(fact)

        self._fact_index = {
            concept: {dims_key: list(facts) for dims_key, facts in by_dims.items()}
            for concept, by_dims in index.items()
        }
        self._indexed_instance_id = current_instance_id

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

        self._ensure_index(instance)
        coord_key = self._dims_key(coordinate.explicit_dimensions or {})
        matching = self._fact_index.get(coordinate.concept, {}).get(coord_key, [])

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
