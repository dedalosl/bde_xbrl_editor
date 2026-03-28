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
