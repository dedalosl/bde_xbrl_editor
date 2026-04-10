"""Unit tests for FactMapper — coordinate matching, duplicate detection."""

from __future__ import annotations

from unittest.mock import MagicMock

from bde_xbrl_editor.table_renderer.fact_mapper import FactMapper
from bde_xbrl_editor.table_renderer.models import CellCoordinate
from bde_xbrl_editor.taxonomy.models import QName

_NS = "http://example.com"


def _qn(local: str) -> QName:
    return QName(namespace=_NS, local_name=local)


def _make_fact(concept: QName, value: str = "100", decimals: str | None = None, context_ref: str = "ctx1") -> MagicMock:
    fact = MagicMock()
    fact.concept = concept
    fact.value = value
    fact.decimals = decimals
    fact.context_ref = context_ref
    return fact


def _make_context(dims: dict | None = None) -> MagicMock:
    ctx = MagicMock()
    ctx.dimensions = dims or {}
    return ctx


def _make_instance(facts: list, contexts: dict | None = None) -> MagicMock:
    inst = MagicMock()
    inst.facts = facts
    inst.contexts = contexts or {}
    return inst


class TestFactMapper:
    def test_no_concept_no_match(self):
        taxonomy = MagicMock()
        mapper = FactMapper(taxonomy)
        coord = CellCoordinate(concept=None)
        result = mapper.match(coord, _make_instance([]))
        assert not result.matched
        assert result.duplicate_count == 0

    def test_concept_match(self):
        concept = _qn("Assets")
        fact = _make_fact(concept, value="500")
        instance = _make_instance([fact], {"ctx1": _make_context()})
        taxonomy = MagicMock()
        mapper = FactMapper(taxonomy)
        coord = CellCoordinate(concept=concept)
        result = mapper.match(coord, instance)
        assert result.matched
        assert result.fact_value == "500"
        assert result.duplicate_count == 1

    def test_concept_no_match_different_concept(self):
        concept = _qn("Assets")
        other = _qn("Liabilities")
        fact = _make_fact(other, value="500")
        instance = _make_instance([fact], {"ctx1": _make_context()})
        taxonomy = MagicMock()
        mapper = FactMapper(taxonomy)
        coord = CellCoordinate(concept=concept)
        result = mapper.match(coord, instance)
        assert not result.matched

    def test_duplicate_detection(self):
        concept = _qn("Assets")
        fact1 = _make_fact(concept, value="100", context_ref="ctx1")
        fact2 = _make_fact(concept, value="200", context_ref="ctx1")
        instance = _make_instance([fact1, fact2], {"ctx1": _make_context()})
        taxonomy = MagicMock()
        mapper = FactMapper(taxonomy)
        coord = CellCoordinate(concept=concept)
        result = mapper.match(coord, instance)
        assert result.matched
        assert result.duplicate_count == 2

    def test_dimension_match(self):
        concept = _qn("Assets")
        dim = _qn("Dim1")
        mem = _qn("Mem1")
        fact = _make_fact(concept, context_ref="ctx1")
        ctx = _make_context({dim: mem})
        instance = _make_instance([fact], {"ctx1": ctx})
        taxonomy = MagicMock()
        mapper = FactMapper(taxonomy)
        coord = CellCoordinate(concept=concept, explicit_dimensions={dim: mem})
        result = mapper.match(coord, instance)
        assert result.matched

    def test_dimension_no_match_wrong_member(self):
        concept = _qn("Assets")
        dim = _qn("Dim1")
        mem = _qn("Mem1")
        wrong_mem = _qn("Mem2")
        fact = _make_fact(concept, context_ref="ctx1")
        ctx = _make_context({dim: wrong_mem})
        instance = _make_instance([fact], {"ctx1": ctx})
        taxonomy = MagicMock()
        mapper = FactMapper(taxonomy)
        coord = CellCoordinate(concept=concept, explicit_dimensions={dim: mem})
        result = mapper.match(coord, instance)
        assert not result.matched

    def test_empty_instance(self):
        concept = _qn("Assets")
        instance = _make_instance([])
        taxonomy = MagicMock()
        mapper = FactMapper(taxonomy)
        coord = CellCoordinate(concept=concept)
        result = mapper.match(coord, instance)
        assert not result.matched
        assert result.duplicate_count == 0

    def test_agrupacion_dimension_stripped_from_fact_context(self):
        """Agrupacion in the fact's context must not affect matching or duplicate detection."""
        from bde_xbrl_editor.instance.constants import BDE_DIM_NS
        concept = _qn("Assets")
        table_dim = _qn("Industry")
        table_mem = _qn("Banks")
        agrupacion_dim = QName(namespace=BDE_DIM_NS, local_name="Agrupacion")
        agrupacion_mem_a = QName(namespace=BDE_DIM_NS, local_name="AgrupacionIndividual")
        agrupacion_mem_b = QName(namespace=BDE_DIM_NS, local_name="AgrupacionGrupoConsolidado")

        # Two facts that differ ONLY in Agrupacion — same table cell
        fact1 = _make_fact(concept, value="100", context_ref="ctx_a")
        fact2 = _make_fact(concept, value="100", context_ref="ctx_b")
        ctx_a = _make_context({table_dim: table_mem, agrupacion_dim: agrupacion_mem_a})
        ctx_b = _make_context({table_dim: table_mem, agrupacion_dim: agrupacion_mem_b})
        instance = _make_instance([fact1, fact2], {"ctx_a": ctx_a, "ctx_b": ctx_b})

        taxonomy = MagicMock()
        mapper = FactMapper(taxonomy)
        coord = CellCoordinate(concept=concept, explicit_dimensions={table_dim: table_mem})
        result = mapper.match(coord, instance)

        # Both facts match the coord; they differ only in Agrupacion → duplicate_count=2
        # (Agrupacion is stripped so it doesn't prevent matching, but facts are still counted)
        assert result.matched
        assert result.duplicate_count == 2

    def test_agrupacion_only_context_matches_coord_without_agrupacion(self):
        """Fact with only Agrupacion in context matches a coord with no explicit dims."""
        from bde_xbrl_editor.instance.constants import BDE_DIM_NS
        concept = _qn("Assets")
        agrupacion_dim = QName(namespace=BDE_DIM_NS, local_name="Agrupacion")
        agrupacion_mem = QName(namespace=BDE_DIM_NS, local_name="AgrupacionIndividual")

        fact = _make_fact(concept, value="999", context_ref="ctx1")
        ctx = _make_context({agrupacion_dim: agrupacion_mem})
        instance = _make_instance([fact], {"ctx1": ctx})

        taxonomy = MagicMock()
        mapper = FactMapper(taxonomy)
        # Coordinate has no explicit dims — Agrupacion must not block the match
        coord = CellCoordinate(concept=concept, explicit_dimensions={})
        result = mapper.match(coord, instance)
        assert result.matched
        assert result.fact_value == "999"
        assert result.duplicate_count == 1
