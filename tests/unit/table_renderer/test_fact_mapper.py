"""Unit tests for FactMapper — coordinate matching, duplicate detection."""

from __future__ import annotations

from unittest.mock import MagicMock

from bde_xbrl_editor.table_renderer.fact_mapper import FactMapper
from bde_xbrl_editor.table_renderer.models import CellCoordinate
from bde_xbrl_editor.taxonomy.models import HypercubeModel, QName

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

    def test_subset_coordinate_matches_finrep_style_context(self):
        """Table cell axes are a subset of instance context dimensions (e.g. FINREP)."""
        concept = _qn("Assets")
        d1 = _qn("Dim1")
        d2 = _qn("Dim2")
        d3 = _qn("Dim3")
        m1 = _qn("Mem1")
        m2 = _qn("Mem2")
        m3 = _qn("Mem3")
        fact = _make_fact(concept, value="42", context_ref="ctx1")
        ctx = _make_context({d1: m1, d2: m2, d3: m3})
        instance = _make_instance([fact], {"ctx1": ctx})
        taxonomy = MagicMock()
        mapper = FactMapper(taxonomy)
        coord = CellCoordinate(concept=concept, explicit_dimensions={d1: m1, d2: m2})
        result = mapper.match(coord, instance)
        assert result.matched
        assert result.fact_value == "42"
        assert result.duplicate_count == 1

    def test_ambiguous_same_axis_prefers_fact_with_exact_dimension_keyset(self):
        """FINREP totals often use only the column axis while lines add further dimensions."""
        concept = _qn("Metric")
        d_axis = _qn("AxisDim")
        m_axis = _qn("AxisMember")
        d_break = _qn("BreakDim")
        m_break = _qn("BreakMember")
        fact_wide = _make_fact(concept, value="wrong", context_ref="wide")
        fact_narrow = _make_fact(concept, value="right", context_ref="narrow")
        ctx_wide = _make_context({d_axis: m_axis, d_break: m_break})
        ctx_narrow = _make_context({d_axis: m_axis})
        instance = _make_instance([fact_wide, fact_narrow], {"wide": ctx_wide, "narrow": ctx_narrow})

        taxonomy = MagicMock(dimensions={})
        mapper = FactMapper(taxonomy)
        coord = CellCoordinate(concept=concept, explicit_dimensions={d_axis: m_axis})
        result = mapper.match(coord, instance)
        assert result.matched
        assert result.fact_value == "right"
        assert result.duplicate_count == 1

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

    def test_default_member_dimension_is_treated_as_absent(self):
        concept = _qn("Assets")
        dim = _qn("Dim1")
        default_mem = _qn("Default")

        taxonomy = MagicMock()
        dim_model = MagicMock()
        dim_model.default_member = default_mem
        taxonomy.dimensions = {dim: dim_model}

        fact = _make_fact(concept, value="321", context_ref="ctx1")
        ctx = _make_context({})
        instance = _make_instance([fact], {"ctx1": ctx})

        mapper = FactMapper(taxonomy)
        coord = CellCoordinate(concept=concept, explicit_dimensions={dim: default_mem})
        result = mapper.match(coord, instance)

        assert result.matched
        assert result.fact_value == "321"
        assert result.duplicate_count == 1

    def test_rebuilds_index_when_instance_object_changes(self):
        concept = _qn("Assets")
        coord = CellCoordinate(concept=concept)

        taxonomy = MagicMock()
        mapper = FactMapper(taxonomy)

        instance_a = _make_instance([_make_fact(concept, value="100")], {"ctx1": _make_context()})
        instance_b = _make_instance([_make_fact(concept, value="200")], {"ctx1": _make_context()})

        result_a = mapper.match(coord, instance_a)
        result_b = mapper.match(coord, instance_b)

        assert result_a.matched and result_a.fact_value == "100"
        assert result_b.matched and result_b.fact_value == "200"

    def test_closed_hypercube_rejects_superset_context(self) -> None:
        """Under closed ``all`` for this table ELR, facts with extra dimensions do not match."""
        concept = _qn("Assets")
        d1 = _qn("Dim1")
        d2 = _qn("Dim2")
        m1 = _qn("Mem1")
        m2_other = _qn("Mem2")
        fact_wide = _make_fact(concept, value="wide", context_ref="w")
        fact_narrow = _make_fact(concept, value="narrow", context_ref="n")
        ctx_wide = _make_context({d1: m1, d2: m2_other})
        ctx_narrow = _make_context({d1: m1})
        instance = _make_instance([fact_wide, fact_narrow], {"w": ctx_wide, "n": ctx_narrow})

        table_elr = "http://example.com/role/table1"
        taxonomy = MagicMock(dimensions={})
        taxonomy.hypercubes = (
            HypercubeModel(
                qname=_qn("Cube1"),
                arcrole="all",
                closed=True,
                context_element="scenario",
                primary_items=(concept,),
                dimensions=(d1, d2),
                extended_link_role=f"{table_elr}/hc",
            ),
        )
        mapper = FactMapper(taxonomy)
        coord = CellCoordinate(concept=concept, explicit_dimensions={d1: m1})
        result = mapper.match(coord, instance, table_elr=table_elr)
        assert result.matched
        assert result.fact_value == "narrow"

        only_wide = _make_instance([fact_wide], {"w": ctx_wide})
        no_match = mapper.match(coord, only_wide, table_elr=table_elr)
        assert not no_match.matched

    def test_closed_hypercube_not_applied_without_matching_elr(self) -> None:
        """Subset + disambiguation when no closed hypercube is scoped to ``table_elr``."""
        concept = _qn("Metric")
        d_axis = _qn("AxisDim")
        m_axis = _qn("AxisMember")
        d_break = _qn("BreakDim")
        m_break = _qn("BreakMember")
        fact_wide = _make_fact(concept, value="wrong", context_ref="wide")
        fact_narrow = _make_fact(concept, value="right", context_ref="narrow")
        ctx_wide = _make_context({d_axis: m_axis, d_break: m_break})
        ctx_narrow = _make_context({d_axis: m_axis})
        instance = _make_instance([fact_wide, fact_narrow], {"wide": ctx_wide, "narrow": ctx_narrow})

        table_elr = "http://example.com/role/otherTable"
        taxonomy = MagicMock(dimensions={})
        taxonomy.hypercubes = (
            HypercubeModel(
                qname=_qn("Cube1"),
                arcrole="all",
                closed=True,
                context_element="scenario",
                primary_items=(concept,),
                dimensions=(d_axis, d_break),
                extended_link_role="http://example.com/role/thisTable/hc",
            ),
        )
        mapper = FactMapper(taxonomy)
        coord = CellCoordinate(concept=concept, explicit_dimensions={d_axis: m_axis})
        result = mapper.match(coord, instance, table_elr=table_elr)
        assert result.matched
        assert result.fact_value == "right"
