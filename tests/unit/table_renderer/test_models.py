"""Unit tests for CellCoordinate merging and table_renderer models."""

from __future__ import annotations

from bde_xbrl_editor.table_renderer.models import (
    BodyCell,
    CellCoordinate,
    FactMatchResult,
)
from bde_xbrl_editor.taxonomy.models import QName


def _qn(local: str) -> QName:
    return QName(namespace="http://example.com", local_name=local)


class TestCellCoordinate:
    def test_default_empty_dimensions(self):
        coord = CellCoordinate()
        assert coord.concept is None
        assert coord.explicit_dimensions == {}

    def test_explicit_dimensions_stored(self):
        dim = _qn("Dim")
        mem = _qn("Mem")
        coord = CellCoordinate(concept=_qn("Assets"), explicit_dimensions={dim: mem})
        assert coord.explicit_dimensions[dim] == mem

    def test_two_coordinates_equal_same_content(self):
        d = _qn("D")
        m = _qn("M")
        c1 = CellCoordinate(concept=_qn("A"), explicit_dimensions={d: m})
        c2 = CellCoordinate(concept=_qn("A"), explicit_dimensions={d: m})
        assert c1 == c2

    def test_two_coordinates_differ_on_dim(self):
        d = _qn("D")
        m1 = _qn("M1")
        m2 = _qn("M2")
        c1 = CellCoordinate(concept=_qn("A"), explicit_dimensions={d: m1})
        c2 = CellCoordinate(concept=_qn("A"), explicit_dimensions={d: m2})
        assert c1 != c2


class TestBodyCell:
    def test_defaults(self):
        coord = CellCoordinate()
        cell = BodyCell(row_index=0, col_index=0, coordinate=coord)
        assert cell.fact_value is None
        assert not cell.is_duplicate
        assert cell.is_applicable

    def test_with_fact(self):
        coord = CellCoordinate(concept=_qn("Assets"))
        cell = BodyCell(row_index=1, col_index=2, coordinate=coord, fact_value="100")
        assert cell.fact_value == "100"


class TestFactMatchResult:
    def test_no_match(self):
        r = FactMatchResult(matched=False)
        assert not r.matched
        assert r.duplicate_count == 0
        assert r.fact_value is None

    def test_match(self):
        r = FactMatchResult(matched=True, fact_value="42", duplicate_count=1)
        assert r.matched
        assert r.fact_value == "42"

    def test_duplicate(self):
        r = FactMatchResult(matched=True, fact_value="42", duplicate_count=3)
        assert r.duplicate_count == 3
