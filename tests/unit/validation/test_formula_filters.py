"""Unit tests for formula fact-filter predicates (validation/formula/filters.py)."""
from __future__ import annotations

from datetime import date
from pathlib import Path

from bde_xbrl_editor.instance.models import (
    Fact,
    ReportingEntity,
    ReportingPeriod,
    XbrlContext,
    XbrlInstance,
    XbrlUnit,
)
from bde_xbrl_editor.taxonomy.models import (
    BooleanFilterDefinition,
    DimensionFilter,
    FactVariableDefinition,
    QName,
    TypedDimensionFilter,
)
from bde_xbrl_editor.validation.formula.filters import apply_filters

# ---------------------------------------------------------------------------
# QName helpers
# ---------------------------------------------------------------------------

_TAX_NS = "http://example.com/tax"
_DIM_NS = "http://example.com/dim"
_MEM_NS = "http://example.com/mem"


def _qn(local: str, ns: str = _TAX_NS) -> QName:
    return QName(namespace=ns, local_name=local)


# ---------------------------------------------------------------------------
# Instance / context / fact builders
# ---------------------------------------------------------------------------

CONCEPT_A = _qn("ConceptA")
CONCEPT_B = _qn("ConceptB")
DIM_QN = _qn("CountryDim", _DIM_NS)
MEM_ES = _qn("ES", _MEM_NS)
MEM_PT = _qn("PT", _MEM_NS)


def _entity() -> ReportingEntity:
    return ReportingEntity(identifier="E001", scheme="http://www.example.com")


def _instant_period() -> ReportingPeriod:
    return ReportingPeriod(period_type="instant", instant_date=date(2024, 12, 31))


def _duration_period() -> ReportingPeriod:
    return ReportingPeriod(
        period_type="duration",
        start_date=date(2024, 1, 1),
        end_date=date(2024, 12, 31),
    )


def _ctx(ctx_id: str, period: ReportingPeriod | None = None, dims: dict | None = None) -> XbrlContext:
    return XbrlContext(
        context_id=ctx_id,
        entity=_entity(),
        period=period or _instant_period(),
        dimensions=dims or {},
    )


def _typed_ctx(ctx_id: str, typed_dims: dict[QName, str]) -> XbrlContext:
    return XbrlContext(
        context_id=ctx_id,
        entity=_entity(),
        period=_instant_period(),
        typed_dimensions=typed_dims,
    )


def _instance(
    facts: list[Fact],
    contexts: dict[str, XbrlContext],
    units: dict[str, XbrlUnit] | None = None,
) -> XbrlInstance:
    inst = XbrlInstance(
        taxonomy_entry_point=Path("tax.xsd"),
        schema_ref_href="tax.xsd",
        entity=_entity(),
        period=_instant_period(),
    )
    inst.contexts.update(contexts)
    inst.facts.extend(facts)
    if units:
        inst.units.update(units)
    return inst


def _var_def(
    variable_name: str = "v",
    concept_filter: QName | None = None,
    period_filter: str | None = None,
    dimension_filters: tuple = (),
    unit_filter: QName | None = None,
) -> FactVariableDefinition:
    return FactVariableDefinition(
        variable_name=variable_name,
        concept_filter=concept_filter,
        period_filter=period_filter,  # type: ignore[arg-type]
        dimension_filters=dimension_filters,
        unit_filter=unit_filter,
    )


# ---------------------------------------------------------------------------
# No filters — all facts pass
# ---------------------------------------------------------------------------


class TestNoFilter:
    def test_no_filter_returns_all_facts(self) -> None:
        """When no filter is set, apply_filters returns all facts unchanged."""
        ctx = _ctx("ctx1")
        facts = [
            Fact(concept=CONCEPT_A, context_ref="ctx1", unit_ref=None, value="1"),
            Fact(concept=CONCEPT_B, context_ref="ctx1", unit_ref=None, value="2"),
        ]
        inst = _instance(facts, {"ctx1": ctx})
        var = _var_def()
        result = apply_filters(facts, var, inst)
        assert len(result) == 2


# ---------------------------------------------------------------------------
# Concept filter
# ---------------------------------------------------------------------------


class TestConceptFilter:
    def test_concept_filter_match(self) -> None:
        """concept_filter keeps only facts with a matching concept."""
        ctx = _ctx("ctx1")
        facts = [
            Fact(concept=CONCEPT_A, context_ref="ctx1", unit_ref=None, value="1"),
            Fact(concept=CONCEPT_B, context_ref="ctx1", unit_ref=None, value="2"),
        ]
        inst = _instance(facts, {"ctx1": ctx})
        var = _var_def(concept_filter=CONCEPT_A)
        result = apply_filters(facts, var, inst)
        assert len(result) == 1
        assert result[0].concept == CONCEPT_A

    def test_concept_filter_no_match(self) -> None:
        """concept_filter returns empty list when no facts match the concept."""
        ctx = _ctx("ctx1")
        facts = [Fact(concept=CONCEPT_B, context_ref="ctx1", unit_ref=None, value="2")]
        inst = _instance(facts, {"ctx1": ctx})
        var = _var_def(concept_filter=CONCEPT_A)
        result = apply_filters(facts, var, inst)
        assert result == []

    def test_concept_filter_multiple_facts_same_concept(self) -> None:
        """concept_filter returns all facts that match, not just the first."""
        ctx = _ctx("ctx1")
        facts = [
            Fact(concept=CONCEPT_A, context_ref="ctx1", unit_ref=None, value="10"),
            Fact(concept=CONCEPT_A, context_ref="ctx1", unit_ref=None, value="20"),
        ]
        inst = _instance(facts, {"ctx1": ctx})
        var = _var_def(concept_filter=CONCEPT_A)
        result = apply_filters(facts, var, inst)
        assert len(result) == 2


# ---------------------------------------------------------------------------
# Period filter
# ---------------------------------------------------------------------------


class TestPeriodFilter:
    def test_period_filter_instant_keeps_instant_facts(self) -> None:
        """period_filter='instant' retains only facts in instant contexts."""
        ctx_instant = _ctx("ctx_i", period=_instant_period())
        ctx_duration = _ctx("ctx_d", period=_duration_period())
        facts = [
            Fact(concept=CONCEPT_A, context_ref="ctx_i", unit_ref=None, value="1"),
            Fact(concept=CONCEPT_A, context_ref="ctx_d", unit_ref=None, value="2"),
        ]
        inst = _instance(facts, {"ctx_i": ctx_instant, "ctx_d": ctx_duration})
        var = _var_def(period_filter="instant")
        result = apply_filters(facts, var, inst)
        assert len(result) == 1
        assert result[0].context_ref == "ctx_i"

    def test_period_filter_duration_keeps_duration_facts(self) -> None:
        """period_filter='duration' retains only facts in duration contexts."""
        ctx_instant = _ctx("ctx_i", period=_instant_period())
        ctx_duration = _ctx("ctx_d", period=_duration_period())
        facts = [
            Fact(concept=CONCEPT_A, context_ref="ctx_i", unit_ref=None, value="1"),
            Fact(concept=CONCEPT_A, context_ref="ctx_d", unit_ref=None, value="2"),
        ]
        inst = _instance(facts, {"ctx_i": ctx_instant, "ctx_d": ctx_duration})
        var = _var_def(period_filter="duration")
        result = apply_filters(facts, var, inst)
        assert len(result) == 1
        assert result[0].context_ref == "ctx_d"

    def test_period_filter_no_match_returns_empty(self) -> None:
        """period_filter returns empty when all facts are in the wrong period type."""
        ctx = _ctx("ctx1", period=_instant_period())
        facts = [Fact(concept=CONCEPT_A, context_ref="ctx1", unit_ref=None, value="1")]
        inst = _instance(facts, {"ctx1": ctx})
        var = _var_def(period_filter="duration")
        result = apply_filters(facts, var, inst)
        assert result == []

    def test_period_filter_skips_fact_with_missing_context(self) -> None:
        """A fact referencing a non-existent context is dropped by the period filter."""
        facts = [Fact(concept=CONCEPT_A, context_ref="ctx_MISSING", unit_ref=None, value="1")]
        inst = _instance(facts, {})
        var = _var_def(period_filter="instant")
        result = apply_filters(facts, var, inst)
        assert result == []


# ---------------------------------------------------------------------------
# Dimension filters — include
# ---------------------------------------------------------------------------


class TestDimensionFilterInclude:
    def test_dim_filter_include_specific_member(self) -> None:
        """Include filter with specific members retains only facts with matching members."""
        ctx_es = _ctx("ctx_es", dims={DIM_QN: MEM_ES})
        ctx_pt = _ctx("ctx_pt", dims={DIM_QN: MEM_PT})
        facts = [
            Fact(concept=CONCEPT_A, context_ref="ctx_es", unit_ref=None, value="1"),
            Fact(concept=CONCEPT_A, context_ref="ctx_pt", unit_ref=None, value="2"),
        ]
        inst = _instance(facts, {"ctx_es": ctx_es, "ctx_pt": ctx_pt})
        dim_filter = DimensionFilter(dimension_qname=DIM_QN, member_qnames=(MEM_ES,), exclude=False)
        var = _var_def(dimension_filters=(dim_filter,))
        result = apply_filters(facts, var, inst)
        assert len(result) == 1
        assert result[0].context_ref == "ctx_es"

    def test_dim_filter_include_any_member(self) -> None:
        """Include filter with empty member list retains any fact that has the dimension."""
        ctx_es = _ctx("ctx_es", dims={DIM_QN: MEM_ES})
        ctx_no_dim = _ctx("ctx_no_dim", dims={})
        facts = [
            Fact(concept=CONCEPT_A, context_ref="ctx_es", unit_ref=None, value="1"),
            Fact(concept=CONCEPT_A, context_ref="ctx_no_dim", unit_ref=None, value="2"),
        ]
        inst = _instance(facts, {"ctx_es": ctx_es, "ctx_no_dim": ctx_no_dim})
        dim_filter = DimensionFilter(dimension_qname=DIM_QN, member_qnames=(), exclude=False)
        var = _var_def(dimension_filters=(dim_filter,))
        result = apply_filters(facts, var, inst)
        assert len(result) == 1
        assert result[0].context_ref == "ctx_es"

    def test_dim_filter_include_no_match_returns_empty(self) -> None:
        """Include filter returns empty when no fact has the required member."""
        ctx = _ctx("ctx1", dims={DIM_QN: MEM_PT})
        facts = [Fact(concept=CONCEPT_A, context_ref="ctx1", unit_ref=None, value="1")]
        inst = _instance(facts, {"ctx1": ctx})
        dim_filter = DimensionFilter(dimension_qname=DIM_QN, member_qnames=(MEM_ES,), exclude=False)
        var = _var_def(dimension_filters=(dim_filter,))
        result = apply_filters(facts, var, inst)
        assert result == []


class TestTypedDimensionFilter:
    def test_typed_dimension_filter_keeps_facts_with_typed_dimension(self) -> None:
        typed_dim = _qn("OpenRowDim", _DIM_NS)
        ctx_open = _typed_ctx("ctx_open", {typed_dim: "row-1"})
        ctx_closed = _ctx("ctx_closed")
        facts = [
            Fact(concept=CONCEPT_A, context_ref="ctx_open", unit_ref=None, value="1"),
            Fact(concept=CONCEPT_A, context_ref="ctx_closed", unit_ref=None, value="2"),
        ]
        inst = _instance(facts, {"ctx_open": ctx_open, "ctx_closed": ctx_closed})
        var = FactVariableDefinition(
            variable_name="a",
            concept_filter=CONCEPT_A,
            typed_dimension_filters=(TypedDimensionFilter(typed_dim),),
        )

        result = apply_filters(facts, var, inst)

        assert len(result) == 1
        assert result[0].context_ref == "ctx_open"


# ---------------------------------------------------------------------------
# Dimension filters — exclude
# ---------------------------------------------------------------------------


class TestDimensionFilterExclude:
    def test_dim_filter_exclude_specific_member(self) -> None:
        """Exclude filter drops facts that have the excluded member."""
        ctx_es = _ctx("ctx_es", dims={DIM_QN: MEM_ES})
        ctx_pt = _ctx("ctx_pt", dims={DIM_QN: MEM_PT})
        facts = [
            Fact(concept=CONCEPT_A, context_ref="ctx_es", unit_ref=None, value="1"),
            Fact(concept=CONCEPT_A, context_ref="ctx_pt", unit_ref=None, value="2"),
        ]
        inst = _instance(facts, {"ctx_es": ctx_es, "ctx_pt": ctx_pt})
        dim_filter = DimensionFilter(dimension_qname=DIM_QN, member_qnames=(MEM_ES,), exclude=True)
        var = _var_def(dimension_filters=(dim_filter,))
        result = apply_filters(facts, var, inst)
        assert len(result) == 1
        assert result[0].context_ref == "ctx_pt"

    def test_dim_filter_exclude_keeps_fact_without_dimension(self) -> None:
        """Exclude filter retains facts that have no value for the dimension at all."""
        ctx_no_dim = _ctx("ctx_no_dim", dims={})
        facts = [Fact(concept=CONCEPT_A, context_ref="ctx_no_dim", unit_ref=None, value="1")]
        inst = _instance(facts, {"ctx_no_dim": ctx_no_dim})
        dim_filter = DimensionFilter(dimension_qname=DIM_QN, member_qnames=(MEM_ES,), exclude=True)
        var = _var_def(dimension_filters=(dim_filter,))
        result = apply_filters(facts, var, inst)
        assert len(result) == 1


# ---------------------------------------------------------------------------
# Boolean filters — bf:andFilter / bf:orFilter
# ---------------------------------------------------------------------------

DIM_A = _qn("DimA", _DIM_NS)
DIM_B = _qn("DimB", _DIM_NS)
MEM_1 = _qn("m1", _MEM_NS)
MEM_2 = _qn("m2", _MEM_NS)
MEM_3 = _qn("m3", _MEM_NS)


def _bool_var(bf: BooleanFilterDefinition, concept: QName | None = None) -> FactVariableDefinition:
    return FactVariableDefinition(
        variable_name="v",
        concept_filter=concept,
        boolean_filters=(bf,),
    )


class TestAndFilter:
    """bf:andFilter — fact must satisfy ALL child dimension conditions."""

    def test_and_passes_when_all_dims_match(self) -> None:
        ctx = _ctx("c1", dims={DIM_A: MEM_1, DIM_B: MEM_2})
        fact = Fact(concept=CONCEPT_A, context_ref="c1", unit_ref=None, value="10")
        inst = _instance([fact], {"c1": ctx})
        bf = BooleanFilterDefinition(
            filter_type="and",
            children=(
                DimensionFilter(dimension_qname=DIM_A, member_qnames=(MEM_1,)),
                DimensionFilter(dimension_qname=DIM_B, member_qnames=(MEM_2,)),
            ),
        )
        result = apply_filters([fact], _bool_var(bf), inst)
        assert result == [fact]

    def test_and_fails_when_one_dim_mismatches(self) -> None:
        ctx = _ctx("c1", dims={DIM_A: MEM_1, DIM_B: MEM_3})  # DIM_B = MEM_3, not MEM_2
        fact = Fact(concept=CONCEPT_A, context_ref="c1", unit_ref=None, value="10")
        inst = _instance([fact], {"c1": ctx})
        bf = BooleanFilterDefinition(
            filter_type="and",
            children=(
                DimensionFilter(dimension_qname=DIM_A, member_qnames=(MEM_1,)),
                DimensionFilter(dimension_qname=DIM_B, member_qnames=(MEM_2,)),
            ),
        )
        result = apply_filters([fact], _bool_var(bf), inst)
        assert result == []

    def test_and_with_no_children_passes_all(self) -> None:
        ctx = _ctx("c1", dims={})
        fact = Fact(concept=CONCEPT_A, context_ref="c1", unit_ref=None, value="5")
        inst = _instance([fact], {"c1": ctx})
        bf = BooleanFilterDefinition(filter_type="and", children=())
        result = apply_filters([fact], _bool_var(bf), inst)
        assert result == [fact]

    def test_and_complement_inverts_result(self) -> None:
        """complement=True on andFilter inverts the whole result."""
        ctx = _ctx("c1", dims={DIM_A: MEM_1})
        fact = Fact(concept=CONCEPT_A, context_ref="c1", unit_ref=None, value="10")
        inst = _instance([fact], {"c1": ctx})
        bf = BooleanFilterDefinition(
            filter_type="and",
            children=(DimensionFilter(dimension_qname=DIM_A, member_qnames=(MEM_1,)),),
            complement=True,
        )
        # Without complement this would pass; with complement it must fail
        result = apply_filters([fact], _bool_var(bf), inst)
        assert result == []


class TestOrFilter:
    """bf:orFilter — fact must satisfy AT LEAST ONE child dimension condition."""

    def test_or_passes_when_first_branch_matches(self) -> None:
        ctx = _ctx("c1", dims={DIM_A: MEM_1})
        fact = Fact(concept=CONCEPT_A, context_ref="c1", unit_ref=None, value="10")
        inst = _instance([fact], {"c1": ctx})
        bf = BooleanFilterDefinition(
            filter_type="or",
            children=(
                DimensionFilter(dimension_qname=DIM_A, member_qnames=(MEM_1,)),
                DimensionFilter(dimension_qname=DIM_B, member_qnames=(MEM_2,)),
            ),
        )
        result = apply_filters([fact], _bool_var(bf), inst)
        assert result == [fact]

    def test_or_passes_when_second_branch_matches(self) -> None:
        ctx = _ctx("c1", dims={DIM_B: MEM_2})
        fact = Fact(concept=CONCEPT_A, context_ref="c1", unit_ref=None, value="10")
        inst = _instance([fact], {"c1": ctx})
        bf = BooleanFilterDefinition(
            filter_type="or",
            children=(
                DimensionFilter(dimension_qname=DIM_A, member_qnames=(MEM_1,)),
                DimensionFilter(dimension_qname=DIM_B, member_qnames=(MEM_2,)),
            ),
        )
        result = apply_filters([fact], _bool_var(bf), inst)
        assert result == [fact]

    def test_or_fails_when_no_branch_matches(self) -> None:
        ctx = _ctx("c1", dims={DIM_A: MEM_3, DIM_B: MEM_3})
        fact = Fact(concept=CONCEPT_A, context_ref="c1", unit_ref=None, value="10")
        inst = _instance([fact], {"c1": ctx})
        bf = BooleanFilterDefinition(
            filter_type="or",
            children=(
                DimensionFilter(dimension_qname=DIM_A, member_qnames=(MEM_1,)),
                DimensionFilter(dimension_qname=DIM_B, member_qnames=(MEM_2,)),
            ),
        )
        result = apply_filters([fact], _bool_var(bf), inst)
        assert result == []

    def test_or_with_no_children_passes_all(self) -> None:
        ctx = _ctx("c1", dims={})
        fact = Fact(concept=CONCEPT_A, context_ref="c1", unit_ref=None, value="5")
        inst = _instance([fact], {"c1": ctx})
        bf = BooleanFilterDefinition(filter_type="or", children=())
        result = apply_filters([fact], _bool_var(bf), inst)
        assert result == [fact]


class TestNestedBooleanFilter:
    """orFilter containing andFilter children — mirrors the es_v9 structure."""

    def _make_es_v9_filter(self) -> BooleanFilterDefinition:
        """
        Simplified version of es_v9's boolean filter:

          orFilter:
            andFilter:  PUR=x50 AND TCP ∈ {x1, x1017}
            andFilter:  OSM=x0 AND TCP=x1017
        """
        DIM_PUR = _qn("PUR", _DIM_NS)
        DIM_TCP = _qn("TCP", _DIM_NS)
        DIM_OSM = _qn("OSM", _DIM_NS)
        MEM_X50  = _qn("x50",   _MEM_NS)
        MEM_X1   = _qn("x1",    _MEM_NS)
        MEM_X17  = _qn("x1017", _MEM_NS)
        MEM_X0   = _qn("x0",    _MEM_NS)

        branch1 = BooleanFilterDefinition(
            filter_type="and",
            children=(
                DimensionFilter(dimension_qname=DIM_PUR, member_qnames=(MEM_X50,)),
                DimensionFilter(dimension_qname=DIM_TCP, member_qnames=(MEM_X1, MEM_X17)),
            ),
        )
        branch2 = BooleanFilterDefinition(
            filter_type="and",
            children=(
                DimensionFilter(dimension_qname=DIM_OSM, member_qnames=(MEM_X0,)),
                DimensionFilter(dimension_qname=DIM_TCP, member_qnames=(MEM_X17,)),
            ),
        )
        return BooleanFilterDefinition(filter_type="or", children=(branch1, branch2))

    def test_fact_matches_first_and_branch(self) -> None:
        DIM_PUR = _qn("PUR", _DIM_NS)
        DIM_TCP = _qn("TCP", _DIM_NS)
        MEM_X50 = _qn("x50",  _MEM_NS)
        MEM_X1  = _qn("x1",   _MEM_NS)
        ctx = _ctx("c1", dims={DIM_PUR: MEM_X50, DIM_TCP: MEM_X1})
        fact = Fact(concept=CONCEPT_A, context_ref="c1", unit_ref=None, value="100")
        inst = _instance([fact], {"c1": ctx})
        result = apply_filters([fact], _bool_var(self._make_es_v9_filter()), inst)
        assert result == [fact]

    def test_fact_matches_second_and_branch(self) -> None:
        DIM_OSM = _qn("OSM",  _DIM_NS)
        DIM_TCP = _qn("TCP",  _DIM_NS)
        MEM_X0  = _qn("x0",   _MEM_NS)
        MEM_X17 = _qn("x1017", _MEM_NS)
        ctx = _ctx("c1", dims={DIM_OSM: MEM_X0, DIM_TCP: MEM_X17})
        fact = Fact(concept=CONCEPT_A, context_ref="c1", unit_ref=None, value="200")
        inst = _instance([fact], {"c1": ctx})
        result = apply_filters([fact], _bool_var(self._make_es_v9_filter()), inst)
        assert result == [fact]

    def test_fact_matches_neither_branch_is_excluded(self) -> None:
        DIM_PUR = _qn("PUR", _DIM_NS)
        DIM_TCP = _qn("TCP", _DIM_NS)
        MEM_X1  = _qn("x1",  _MEM_NS)
        MEM_X99 = _qn("x99", _MEM_NS)  # wrong PUR value
        ctx = _ctx("c1", dims={DIM_PUR: MEM_X99, DIM_TCP: MEM_X1})
        fact = Fact(concept=CONCEPT_A, context_ref="c1", unit_ref=None, value="50")
        inst = _instance([fact], {"c1": ctx})
        result = apply_filters([fact], _bool_var(self._make_es_v9_filter()), inst)
        assert result == []

    def test_multiple_facts_only_matching_ones_returned(self) -> None:
        DIM_PUR = _qn("PUR", _DIM_NS)
        DIM_TCP = _qn("TCP", _DIM_NS)
        MEM_X50 = _qn("x50", _MEM_NS)
        MEM_X1  = _qn("x1",  _MEM_NS)
        MEM_X99 = _qn("x99", _MEM_NS)

        ctx_match   = _ctx("c_ok",  dims={DIM_PUR: MEM_X50, DIM_TCP: MEM_X1})
        ctx_nomatch = _ctx("c_bad", dims={DIM_PUR: MEM_X99, DIM_TCP: MEM_X1})
        fact_ok  = Fact(concept=CONCEPT_A, context_ref="c_ok",  unit_ref=None, value="1")
        fact_bad = Fact(concept=CONCEPT_A, context_ref="c_bad", unit_ref=None, value="2")
        inst = _instance(
            [fact_ok, fact_bad],
            {"c_ok": ctx_match, "c_bad": ctx_nomatch},
        )
        result = apply_filters([fact_ok, fact_bad], _bool_var(self._make_es_v9_filter()), inst)
        assert result == [fact_ok]
