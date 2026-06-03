"""FactMapper — maps CellCoordinate to instance facts."""

from __future__ import annotations

from collections.abc import Sequence
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


class FactMapper:
    """Maps a CellCoordinate to instance facts by matching concept + dimensions."""

    def __init__(self, taxonomy: TaxonomyStructure) -> None:
        self._taxonomy = taxonomy
        self._indexed_instance_id: int | None = None
        # Per concept: facts with precomputed normalised explicit/typed dims (no Agrupacion).
        self._facts_by_concept: dict[QName, list[tuple[Fact, dict[QName, QName], dict[QName, str]]]] = {}

    def _hypercubes_for_taxonomy(self) -> tuple[object, ...]:
        """Return hypercube definitions; empty when absent or not a real sequence (e.g. MagicMock)."""
        raw = getattr(self._taxonomy, "hypercubes", ())
        if raw is None:
            return ()
        if isinstance(raw, (str, bytes)) or not isinstance(raw, Sequence):
            return ()
        return tuple(raw)

    def _concept_in_closed_all_hypercube_for_table(self, concept: QName, table_elr: str) -> bool:
        """True when XBRL Dimensions closed ``all`` applies like ``_is_cell_excluded`` ELR filtering."""
        hcs = self._hypercubes_for_taxonomy()
        elr_prefix = (table_elr + "/") if table_elr else ""
        return any(
            getattr(hc, "arcrole", None) == "all"
            and getattr(hc, "closed", False)
            and concept in getattr(hc, "primary_items", ())
            and (not elr_prefix or str(getattr(hc, "extended_link_role", "")).startswith(elr_prefix))
            for hc in hcs
        )

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

    @staticmethod
    def _normalise_typed_dims(typed_dims: dict[QName, str] | None) -> dict[QName, str]:
        return {
            dim_qname: value.strip()
            for dim_qname, value in (typed_dims or {}).items()
            if value.strip()
        }

    def _fact_context_bindings(
        self,
        instance: XbrlInstance,
        fact: Fact,
    ) -> tuple[dict[QName, QName], dict[QName, str]] | None:
        context = instance.contexts.get(fact.context_ref)
        if context is None:
            return None
        raw_dims = context.dimensions if hasattr(context, "dimensions") else {}
        typed_keys = set((getattr(context, "typed_dimensions", {}) or {}).keys())
        explicit_dims = {
            dim: member
            for dim, member in (raw_dims or {}).items()
            if dim not in typed_keys
        }
        explicit = self._normalize_dimensions(self._strip_agrupacion(explicit_dims))
        typed = self._normalise_typed_dims(getattr(context, "typed_dimensions", {}) or {})
        return explicit, typed

    @staticmethod
    def _coordinate_satisfied_by_fact(
        coord_explicit: dict[QName, QName],
        coord_typed: dict[QName, str],
        fact_explicit: dict[QName, QName],
        fact_typed: dict[QName, str],
    ) -> bool:
        """True when the fact context agrees with every explicit/typed binding on the cell."""
        return all(fact_explicit.get(dim) == member for dim, member in coord_explicit.items()) and all(
            fact_typed.get(dim) == value for dim, value in coord_typed.items()
        )

    @staticmethod
    def _disambiguate_subset_matches(
        coord_explicit: dict[QName, QName],
        coord_typed: dict[QName, str],
        candidates: list[tuple[Fact, dict[QName, QName], dict[QName, str]]],
    ) -> list[Fact]:
        """Choose among FINREP supersets matching a partial cell coordinate.

        Many instance contexts repeat the same axis members (for example ``qCAA``) while
        also binding further breakdown dimensions. Subset matching would accept all.
        Prefer a fact whose explicit/typed **keys exactly match those on the coordinate**;
        if none, prefer the **sparsest** context (fewest dimensional bindings — totals /
        rollup lines expressed with only axis members).
        """
        if not candidates:
            return []
        ce_k = set(coord_explicit.keys())
        ct_k = set(coord_typed.keys())
        exact_bounds = [
            fact
            for fact, fact_ex, fact_ty in candidates
            if set(fact_ex.keys()) == ce_k and set(fact_ty.keys()) == ct_k
        ]
        if exact_bounds:
            return exact_bounds
        narrowest = min(len(fact_ex) + len(fact_ty) for _fact, fact_ex, fact_ty in candidates)
        return [
            fact
            for fact, fact_ex, fact_ty in candidates
            if len(fact_ex) + len(fact_ty) == narrowest
        ]

    def resolve_matching_facts(
        self,
        coordinate: CellCoordinate,
        instance: XbrlInstance,
        *,
        table_elr: str = "",
    ) -> list[Fact]:
        """Return instance facts matching ``coordinate`` after dimensional disambiguation."""
        if coordinate.concept is None:
            return []

        self._ensure_index(instance)
        coord_explicit = self._normalize_dimensions(
            self._strip_agrupacion(coordinate.explicit_dimensions or {})
        )
        coord_typed = self._normalise_typed_dims(coordinate.typed_dimensions or {})
        rows = self._facts_by_concept.get(coordinate.concept, [])

        if coord_explicit or coord_typed:
            closed_exact = self._concept_in_closed_all_hypercube_for_table(coordinate.concept, table_elr)
            candidates = [
                (fact, fact_ex, fact_ty)
                for fact, fact_ex, fact_ty in rows
                if self._coordinate_satisfied_by_fact(coord_explicit, coord_typed, fact_ex, fact_ty)
            ]
            if closed_exact:
                ce_k = set(coord_explicit.keys())
                ct_k = set(coord_typed.keys())
                candidates = [
                    (fact, fact_ex, fact_ty)
                    for fact, fact_ex, fact_ty in candidates
                    if set(fact_ex.keys()) == ce_k and set(fact_ty.keys()) == ct_k
                ]
                return [fact for fact, _ex, _ty in candidates]
            return self._disambiguate_subset_matches(coord_explicit, coord_typed, candidates)

        return [fact for fact, fact_ex, fact_ty in rows if not fact_ex and not fact_ty]

    def _ensure_index(self, instance: XbrlInstance) -> None:
        """Group facts by concept with normalised dimensional bindings."""
        current_instance_id = id(instance)
        if self._indexed_instance_id == current_instance_id:
            return

        by_concept: dict[QName, list[tuple[Fact, dict[QName, QName], dict[QName, str]]]] = {}
        for fact in instance.facts:
            bindings = self._fact_context_bindings(instance, fact)
            if bindings is None:
                continue
            explicit, typed = bindings
            by_concept.setdefault(fact.concept, []).append((fact, explicit, typed))

        self._facts_by_concept = by_concept
        self._indexed_instance_id = current_instance_id

    def match(
        self,
        coordinate: CellCoordinate,
        instance: XbrlInstance,
        *,
        table_elr: str = "",
    ) -> FactMatchResult:
        """Match coordinate against instance facts.

        Matching rules:
        - concept must match (if coordinate.concept is None, no match)
        - every explicit/typed binding on the coordinate must match the fact's
          context; the fact may carry additional dimensions (FINREP-style rich
          contexts vs table-axis-only cell coordinates), **unless** this concept is
          in scope of an ``all``, **closed** hypercube for ``table_elr`` — then the
          fact's explicit + typed dimensional keys must **exactly** match the
          coordinate's keys (after normalisation and Agrupacion stripping).
        - the fact context's Agrupacion dimension is stripped before comparison —
          it is a BDE instance-level segment dimension not declared in any table
          definition linkbase and must never influence cell matching
        - period_override and entity_override are used if set
        """
        if coordinate.concept is None:
            return FactMatchResult(matched=False, duplicate_count=0)

        matching = self.resolve_matching_facts(coordinate, instance, table_elr=table_elr)

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
