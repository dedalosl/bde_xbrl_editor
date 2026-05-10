"""Unit tests for DimensionalConstraintValidator (validation/dimensional.py)."""

from __future__ import annotations

from datetime import date, datetime
from pathlib import Path

from bde_xbrl_editor.instance.constants import BDE_DIM_NS
from bde_xbrl_editor.instance.models import (
    Fact,
    ReportingEntity,
    ReportingPeriod,
    XbrlContext,
    XbrlInstance,
)
from bde_xbrl_editor.taxonomy.models import (
    Concept,
    DimensionModel,
    DomainMember,
    FormulaAssertionSet,
    HypercubeModel,
    QName,
    TaxonomyMetadata,
    TaxonomyStructure,
)
from bde_xbrl_editor.validation.dimensional import DimensionalConstraintValidator
from bde_xbrl_editor.validation.models import ValidationSeverity

# ---------------------------------------------------------------------------
# Shared QName constants
# ---------------------------------------------------------------------------

_TAX_NS = "http://example.com/tax"
_DIM_NS = "http://example.com/dim"
_MEM_NS = "http://example.com/mem"


def _qn(local: str, ns: str = _TAX_NS) -> QName:
    return QName(namespace=ns, local_name=local)


# ---------------------------------------------------------------------------
# Builders
# ---------------------------------------------------------------------------


def _entity() -> ReportingEntity:
    return ReportingEntity(identifier="ENT001", scheme="http://www.example.com")


def _instant_period() -> ReportingPeriod:
    return ReportingPeriod(period_type="instant", instant_date=date(2024, 12, 31))


def _make_context(ctx_id: str, dims: dict[QName, QName] | None = None) -> XbrlContext:
    return XbrlContext(
        context_id=ctx_id,
        entity=_entity(),
        period=_instant_period(),
        dimensions=dims or {},
    )


def _make_instance(facts: list[Fact], contexts: dict[str, XbrlContext]) -> XbrlInstance:
    inst = XbrlInstance(
        taxonomy_entry_point=Path("tax.xsd"),
        schema_ref_href="tax.xsd",
        entity=_entity(),
        period=_instant_period(),
    )
    inst.contexts.update(contexts)
    inst.facts.extend(facts)
    return inst


def _make_taxonomy(
    hc: HypercubeModel,
    dims: dict[QName, DimensionModel] | None = None,
    extra_concepts: dict[QName, Concept] | None = None,
) -> TaxonomyStructure:
    meta = TaxonomyMetadata(
        name="Test",
        version="1.0",
        publisher="Example",
        entry_point_path=Path("tax.xsd"),
        loaded_at=datetime(2024, 1, 1),
        declared_languages=("en",),
    )

    class _FakeLabels:
        def get(self, *a, **kw):
            return None

    concepts: dict[QName, Concept] = extra_concepts or {}
    return TaxonomyStructure(
        metadata=meta,
        concepts=concepts,
        labels=_FakeLabels(),
        presentation={},
        calculation={},
        definition={},
        hypercubes=[hc],
        dimensions=dims or {},
        tables=[],
        formula_assertion_set=FormulaAssertionSet(),
    )


def _make_taxonomy_with_hcs(
    hcs: list[HypercubeModel],
    dims: dict[QName, DimensionModel] | None = None,
    extra_concepts: dict[QName, Concept] | None = None,
) -> TaxonomyStructure:
    meta = TaxonomyMetadata(
        name="Test",
        version="1.0",
        publisher="Example",
        entry_point_path=Path("tax.xsd"),
        loaded_at=datetime(2024, 1, 1),
        declared_languages=("en",),
    )

    class _FakeLabels:
        def get(self, *a, **kw):
            return None

    concepts: dict[QName, Concept] = extra_concepts or {}
    return TaxonomyStructure(
        metadata=meta,
        concepts=concepts,
        labels=_FakeLabels(),
        presentation={},
        calculation={},
        definition={},
        hypercubes=hcs,
        dimensions=dims or {},
        tables=[],
        formula_assertion_set=FormulaAssertionSet(),
    )


# ---------------------------------------------------------------------------
# Canonical dimension / hypercube fixtures
# ---------------------------------------------------------------------------

DIM_QN = _qn("CountryDim", _DIM_NS)
MEM_QN_ES = _qn("ES", _MEM_NS)
MEM_QN_PT = _qn("PT", _MEM_NS)
CONCEPT_QN = _qn("PrimaryItem")
HC_QN = _qn("HC1")


def _dim_model_with_members() -> DimensionModel:
    return DimensionModel(
        qname=DIM_QN,
        dimension_type="explicit",
        default_member=None,
        members=(
            DomainMember(qname=MEM_QN_ES, parent=None, order=1.0),
            DomainMember(qname=MEM_QN_PT, parent=None, order=2.0),
        ),
    )


def _all_closed_hc() -> HypercubeModel:
    return HypercubeModel(
        qname=HC_QN,
        arcrole="all",
        closed=True,
        context_element="scenario",
        primary_items=(CONCEPT_QN,),
        dimensions=(DIM_QN,),
        extended_link_role="http://example.com/elr",
    )


def _all_open_hc() -> HypercubeModel:
    return HypercubeModel(
        qname=HC_QN,
        arcrole="all",
        closed=False,
        context_element="scenario",
        primary_items=(CONCEPT_QN,),
        dimensions=(DIM_QN,),
        extended_link_role="http://example.com/elr",
    )


def _not_all_hc() -> HypercubeModel:
    return HypercubeModel(
        qname=HC_QN,
        arcrole="notAll",
        closed=False,
        context_element="scenario",
        primary_items=(CONCEPT_QN,),
        dimensions=(DIM_QN,),
        extended_link_role="http://example.com/elr",
        direct_primary_items=(CONCEPT_QN,),
    )


def _inherited_not_all_hc() -> HypercubeModel:
    return HypercubeModel(
        qname=HC_QN,
        arcrole="notAll",
        closed=False,
        context_element="scenario",
        primary_items=(CONCEPT_QN,),
        dimensions=(DIM_QN,),
        extended_link_role="http://example.com/elr",
        direct_primary_items=(),
    )


def _all_empty_hc() -> HypercubeModel:
    return HypercubeModel(
        qname=_qn("PositiveHC"),
        arcrole="all",
        closed=False,
        context_element="scenario",
        primary_items=(CONCEPT_QN,),
        dimensions=(),
        extended_link_role="http://example.com/elr",
    )


def _not_all_closed_hc() -> HypercubeModel:
    return HypercubeModel(
        qname=HC_QN,
        arcrole="notAll",
        closed=True,
        context_element="scenario",
        primary_items=(CONCEPT_QN,),
        dimensions=(DIM_QN,),
        extended_link_role="http://example.com/elr",
    )


# ---------------------------------------------------------------------------
# 1. UNDECLARED_DIMENSION
# ---------------------------------------------------------------------------


class TestUndeclaredDimension:
    def test_context_uses_undeclared_dimension(self) -> None:
        """A dimension present in the context but absent from a CLOSED hypercube is flagged."""
        unknown_dim = _qn("UnknownDim", _DIM_NS)
        ctx = _make_context("ctx1", dims={unknown_dim: MEM_QN_ES})
        fact = Fact(concept=CONCEPT_QN, context_ref="ctx1", unit_ref=None, value="1")
        inst = _make_instance([fact], {"ctx1": ctx})
        # Closed hypercube: undeclared dimensions are not allowed
        taxonomy = _make_taxonomy(_all_closed_hc(), dims={})
        findings = DimensionalConstraintValidator(taxonomy).validate(inst)
        assert any(f.constraint_type == "UNDECLARED_DIMENSION" for f in findings)

    def test_open_hypercube_allows_undeclared_dimension(self) -> None:
        """An open hypercube allows extra (undeclared) dimensions in the context."""
        unknown_dim = _qn("UnknownDim", _DIM_NS)
        ctx = _make_context("ctx1", dims={unknown_dim: MEM_QN_ES})
        fact = Fact(concept=CONCEPT_QN, context_ref="ctx1", unit_ref=None, value="1")
        inst = _make_instance([fact], {"ctx1": ctx})
        # Open hypercube: undeclared dimensions are fine
        taxonomy = _make_taxonomy(_all_open_hc(), dims={})
        findings = DimensionalConstraintValidator(taxonomy).validate(inst)
        assert not any(f.constraint_type == "UNDECLARED_DIMENSION" for f in findings)

    def test_declared_dimension_no_undeclared_finding(self) -> None:
        """A dimension that is declared in the hypercube does not trigger UNDECLARED_DIMENSION."""
        ctx = _make_context("ctx1", dims={DIM_QN: MEM_QN_ES})
        fact = Fact(concept=CONCEPT_QN, context_ref="ctx1", unit_ref=None, value="1")
        inst = _make_instance([fact], {"ctx1": ctx})
        taxonomy = _make_taxonomy(_all_closed_hc(), dims={DIM_QN: _dim_model_with_members()})
        findings = DimensionalConstraintValidator(taxonomy).validate(inst)
        assert not any(f.constraint_type == "UNDECLARED_DIMENSION" for f in findings)

    def test_undeclared_dimension_finding_metadata(self) -> None:
        """UNDECLARED_DIMENSION findings carry concept_qname, context_ref and dimension_qname."""
        unknown_dim = _qn("UnknownDim", _DIM_NS)
        ctx = _make_context("ctx1", dims={unknown_dim: MEM_QN_ES})
        fact = Fact(concept=CONCEPT_QN, context_ref="ctx1", unit_ref=None, value="1")
        inst = _make_instance([fact], {"ctx1": ctx})
        taxonomy = _make_taxonomy(_all_closed_hc(), dims={})
        findings = DimensionalConstraintValidator(taxonomy).validate(inst)
        match = next((f for f in findings if f.constraint_type == "UNDECLARED_DIMENSION"), None)
        assert match is not None
        assert match.concept_qname == CONCEPT_QN
        assert match.context_ref == "ctx1"
        assert match.dimension_qname == unknown_dim

    def test_reused_hypercube_qname_in_other_elr_does_not_override_dimensions(self) -> None:
        """Dimension caches must distinguish reused hypercube QNames across ELRs."""
        dim_other = _qn("OtherDim", _DIM_NS)
        shared_hc_qn = QName(
            namespace="http://www.eurofiling.info/xbrl/ext/model",
            local_name="hyp",
        )
        hc_first = HypercubeModel(
            qname=shared_hc_qn,
            arcrole="all",
            closed=True,
            context_element="scenario",
            primary_items=(CONCEPT_QN,),
            dimensions=(dim_other,),
            extended_link_role="http://example.com/elr/one",
        )
        hc_second = HypercubeModel(
            qname=shared_hc_qn,
            arcrole="all",
            closed=True,
            context_element="scenario",
            primary_items=(CONCEPT_QN,),
            dimensions=(DIM_QN,),
            extended_link_role="http://example.com/elr/two",
        )
        ctx = _make_context("ctx1", dims={DIM_QN: MEM_QN_ES})
        fact = Fact(concept=CONCEPT_QN, context_ref="ctx1", unit_ref=None, value="1")
        inst = _make_instance([fact], {"ctx1": ctx})
        taxonomy = _make_taxonomy_with_hcs(
            [hc_first, hc_second],
            dims={
                DIM_QN: _dim_model_with_members(),
                dim_other: DimensionModel(
                    qname=dim_other,
                    dimension_type="explicit",
                    default_member=None,
                    members=(DomainMember(qname=MEM_QN_ES, parent=None, order=1.0),),
                ),
            },
        )

        findings = DimensionalConstraintValidator(taxonomy).validate(inst)

        assert not any(f.constraint_type == "UNDECLARED_DIMENSION" for f in findings)

    def test_positive_hypercubes_in_same_elr_are_alternative_covering_candidates(self) -> None:
        """A fact accepted by one covering hypercube is not failed by a sibling."""
        dim_other = _qn("OtherDim", _DIM_NS)
        hc_first = HypercubeModel(
            qname=_qn("HC1"),
            arcrole="all",
            closed=True,
            context_element="scenario",
            primary_items=(CONCEPT_QN,),
            dimensions=(DIM_QN,),
            extended_link_role="http://example.com/elr",
        )
        hc_second = HypercubeModel(
            qname=HC_QN,
            arcrole="all",
            closed=True,
            context_element="scenario",
            primary_items=(CONCEPT_QN,),
            dimensions=(DIM_QN, dim_other),
            extended_link_role="http://example.com/elr",
        )
        ctx = _make_context("ctx1", dims={DIM_QN: MEM_QN_ES})
        fact = Fact(concept=CONCEPT_QN, context_ref="ctx1", unit_ref=None, value="1")
        inst = _make_instance([fact], {"ctx1": ctx})
        taxonomy = _make_taxonomy_with_hcs(
            [hc_first, hc_second],
            dims={
                DIM_QN: _dim_model_with_members(),
                dim_other: DimensionModel(
                    qname=dim_other,
                    dimension_type="explicit",
                    default_member=None,
                    members=(DomainMember(qname=MEM_QN_PT, parent=None, order=1.0),),
                ),
            },
        )

        findings = DimensionalConstraintValidator(taxonomy).validate(inst)

        assert not any(f.constraint_type == "CLOSED_MISSING_DIMENSION" for f in findings)

    def test_closed_hypercube_sibling_dimension_does_not_poison_valid_candidate(self) -> None:
        """Closed sibling cubes do not reject dimensions owned by another match."""
        dim_other = _qn("OtherDim", _DIM_NS)
        hc_first = HypercubeModel(
            qname=_qn("HC1"),
            arcrole="all",
            closed=True,
            context_element="scenario",
            primary_items=(CONCEPT_QN,),
            dimensions=(DIM_QN,),
            extended_link_role="http://example.com/elr",
        )
        hc_second = HypercubeModel(
            qname=HC_QN,
            arcrole="all",
            closed=True,
            context_element="scenario",
            primary_items=(CONCEPT_QN,),
            dimensions=(DIM_QN, dim_other),
            extended_link_role="http://example.com/elr",
        )
        ctx = _make_context("ctx1", dims={DIM_QN: MEM_QN_ES, dim_other: MEM_QN_PT})
        fact = Fact(concept=CONCEPT_QN, context_ref="ctx1", unit_ref=None, value="1")
        inst = _make_instance([fact], {"ctx1": ctx})
        taxonomy = _make_taxonomy_with_hcs(
            [hc_first, hc_second],
            dims={
                DIM_QN: _dim_model_with_members(),
                dim_other: DimensionModel(
                    qname=dim_other,
                    dimension_type="explicit",
                    default_member=None,
                    members=(DomainMember(qname=MEM_QN_PT, parent=None, order=1.0),),
                ),
            },
        )

        findings = DimensionalConstraintValidator(taxonomy).validate(inst)

        assert not any(f.constraint_type == "UNDECLARED_DIMENSION" for f in findings)

    def test_reused_closed_hypercube_qname_dimension_is_not_reported(self) -> None:
        """A reused closed hypercube QName does not report dimensions from another signature."""
        dim_other = _qn("OtherDim", _DIM_NS)
        reused_hc_qname = _qn("ReusedHyp")
        hc_first = HypercubeModel(
            qname=reused_hc_qname,
            arcrole="all",
            closed=True,
            context_element="scenario",
            primary_items=(CONCEPT_QN,),
            dimensions=(DIM_QN,),
            extended_link_role="http://example.com/elr/one",
        )
        hc_second = HypercubeModel(
            qname=reused_hc_qname,
            arcrole="all",
            closed=True,
            context_element="scenario",
            primary_items=(CONCEPT_QN,),
            dimensions=(DIM_QN, dim_other),
            extended_link_role="http://example.com/elr/two",
        )
        ctx = _make_context("ctx1", dims={DIM_QN: MEM_QN_ES, dim_other: MEM_QN_PT})
        fact = Fact(concept=CONCEPT_QN, context_ref="ctx1", unit_ref=None, value="1")
        inst = _make_instance([fact], {"ctx1": ctx})
        taxonomy = _make_taxonomy_with_hcs(
            [hc_first, hc_second],
            dims={
                DIM_QN: _dim_model_with_members(),
                dim_other: DimensionModel(
                    qname=dim_other,
                    dimension_type="explicit",
                    default_member=None,
                    members=(DomainMember(qname=MEM_QN_PT, parent=None, order=1.0),),
                ),
            },
        )

        findings = DimensionalConstraintValidator(taxonomy).validate(inst)

        assert not any(
            f.constraint_type == "UNDECLARED_DIMENSION" and f.dimension_qname == dim_other
            for f in findings
        )

    def test_bde_agrupacion_is_ignored_for_hypercube_undeclared_checks(self) -> None:
        """BDE Agrupacion is a report-level dimension and must not fail closed HC checks."""
        agrupacion_dim = QName(namespace=BDE_DIM_NS, local_name="Agrupacion")
        agrupacion_member = QName(namespace=BDE_DIM_NS, local_name="AgrupacionIndividual")
        ctx = _make_context("ctx1", dims={agrupacion_dim: agrupacion_member})
        fact = Fact(concept=CONCEPT_QN, context_ref="ctx1", unit_ref=None, value="1")
        inst = _make_instance([fact], {"ctx1": ctx})
        taxonomy = _make_taxonomy(_all_closed_hc(), dims={})

        findings = DimensionalConstraintValidator(taxonomy).validate(inst)

        assert not any(f.constraint_type == "UNDECLARED_DIMENSION" for f in findings)

    def test_closed_hypercube_rejects_non_dimensional_scenario_content(self) -> None:
        """Closed hypercubes reject non-xbrldi content in their context container."""
        ctx = _make_context("ctx1", dims={DIM_QN: MEM_QN_ES})
        ctx.scenario_xml = (
            b'<xbrli:scenario xmlns:xbrli="http://www.xbrl.org/2003/instance" '
            b'xmlns:xbrldi="http://xbrl.org/2006/xbrldi" '
            b'xmlns:foo="http://example.com/foo">'
            b'<xbrldi:explicitMember dimension="dim:CountryDim" '
            b'xmlns:dim="http://example.com/dim">mem:ES</xbrldi:explicitMember>'
            b"<foo:bar/>"
            b"</xbrli:scenario>"
        )
        fact = Fact(concept=CONCEPT_QN, context_ref="ctx1", unit_ref=None, value="1")
        inst = _make_instance([fact], {"ctx1": ctx})
        taxonomy = _make_taxonomy(_all_closed_hc(), dims={DIM_QN: _dim_model_with_members()})

        findings = DimensionalConstraintValidator(taxonomy).validate(inst)

        assert any(f.constraint_type == "UNEXPECTED_DIMENSIONAL_CONTENT" for f in findings)


# ---------------------------------------------------------------------------
# 2. INVALID_MEMBER
# ---------------------------------------------------------------------------


class TestInvalidMember:
    def test_invalid_member_flagged(self) -> None:
        """A member not in the dimension's declared member list triggers INVALID_MEMBER."""
        bad_member = _qn("XX", _MEM_NS)
        ctx = _make_context("ctx1", dims={DIM_QN: bad_member})
        fact = Fact(concept=CONCEPT_QN, context_ref="ctx1", unit_ref=None, value="1")
        inst = _make_instance([fact], {"ctx1": ctx})
        taxonomy = _make_taxonomy(_all_open_hc(), dims={DIM_QN: _dim_model_with_members()})
        findings = DimensionalConstraintValidator(taxonomy).validate(inst)
        assert any(f.constraint_type == "INVALID_MEMBER" for f in findings)

    def test_valid_member_no_finding(self) -> None:
        """A member that belongs to the dimension's declared list passes validation."""
        ctx = _make_context("ctx1", dims={DIM_QN: MEM_QN_ES})
        fact = Fact(concept=CONCEPT_QN, context_ref="ctx1", unit_ref=None, value="1")
        inst = _make_instance([fact], {"ctx1": ctx})
        taxonomy = _make_taxonomy(_all_open_hc(), dims={DIM_QN: _dim_model_with_members()})
        findings = DimensionalConstraintValidator(taxonomy).validate(inst)
        assert not any(f.constraint_type == "INVALID_MEMBER" for f in findings)

    def test_typed_dimension_no_members_skips_member_check(self) -> None:
        """A typed dimension with no declared members skips the INVALID_MEMBER check."""
        typed_dim = DimensionModel(
            qname=DIM_QN,
            dimension_type="typed",
            default_member=None,
            members=(),
        )
        ctx = _make_context("ctx1", dims={DIM_QN: MEM_QN_ES})
        fact = Fact(concept=CONCEPT_QN, context_ref="ctx1", unit_ref=None, value="1")
        inst = _make_instance([fact], {"ctx1": ctx})
        taxonomy = _make_taxonomy(_all_open_hc(), dims={DIM_QN: typed_dim})
        findings = DimensionalConstraintValidator(taxonomy).validate(inst)
        assert not any(f.constraint_type == "INVALID_MEMBER" for f in findings)

    def test_invalid_member_finding_includes_dimension_qname(self) -> None:
        """INVALID_MEMBER finding carries the dimension_qname."""
        bad_member = _qn("WRONG", _MEM_NS)
        ctx = _make_context("ctx1", dims={DIM_QN: bad_member})
        fact = Fact(concept=CONCEPT_QN, context_ref="ctx1", unit_ref=None, value="1")
        inst = _make_instance([fact], {"ctx1": ctx})
        taxonomy = _make_taxonomy(_all_open_hc(), dims={DIM_QN: _dim_model_with_members()})
        findings = DimensionalConstraintValidator(taxonomy).validate(inst)
        match = next((f for f in findings if f.constraint_type == "INVALID_MEMBER"), None)
        assert match is not None
        assert match.dimension_qname == DIM_QN

    def test_open_empty_hypercube_ignores_rogue_context_dimensions(self) -> None:
        """Dimensions outside an open empty hypercube are not validated."""
        rogue_dim = _qn("RogueDim", _DIM_NS)
        rogue_member = _qn("NotAConcept", _DIM_NS)
        ctx = _make_context("ctx1", dims={rogue_dim: rogue_member})
        fact = Fact(concept=CONCEPT_QN, context_ref="ctx1", unit_ref=None, value="1")
        inst = _make_instance([fact], {"ctx1": ctx})
        taxonomy = _make_taxonomy_with_hcs(
            [_all_empty_hc()],
            dims={},
            extra_concepts={
                rogue_dim: Concept(
                    qname=rogue_dim,
                    data_type=_qn("stringItemType"),
                    period_type="duration",
                )
            },
        )

        findings = DimensionalConstraintValidator(taxonomy).validate(inst)

        assert not any(f.constraint_type == "EXPLICIT_MEMBER_UNDEFINED_QNAME" for f in findings)


# ---------------------------------------------------------------------------
# 3. CLOSED_MISSING_DIMENSION
# ---------------------------------------------------------------------------


class TestClosedMissingDimension:
    def test_closed_hc_missing_required_dimension(self) -> None:
        """Fact in closed hypercube without a required dimension triggers the check."""
        ctx = _make_context("ctx1", dims={})  # dimension absent, no default member
        fact = Fact(concept=CONCEPT_QN, context_ref="ctx1", unit_ref=None, value="1")
        inst = _make_instance([fact], {"ctx1": ctx})
        taxonomy = _make_taxonomy(_all_closed_hc(), dims={DIM_QN: _dim_model_with_members()})
        findings = DimensionalConstraintValidator(taxonomy).validate(inst)
        assert any(f.constraint_type == "CLOSED_MISSING_DIMENSION" for f in findings)

    def test_closed_hc_dimension_present_no_finding(self) -> None:
        """Fact in closed hypercube with all required dimensions passes."""
        ctx = _make_context("ctx1", dims={DIM_QN: MEM_QN_ES})
        fact = Fact(concept=CONCEPT_QN, context_ref="ctx1", unit_ref=None, value="1")
        inst = _make_instance([fact], {"ctx1": ctx})
        taxonomy = _make_taxonomy(_all_closed_hc(), dims={DIM_QN: _dim_model_with_members()})
        findings = DimensionalConstraintValidator(taxonomy).validate(inst)
        assert not any(f.constraint_type == "CLOSED_MISSING_DIMENSION" for f in findings)

    def test_open_hc_missing_dimension_reports_finding(self) -> None:
        """Open hypercubes also require declared dimensions (unless a default exists)."""
        ctx = _make_context("ctx1", dims={})
        fact = Fact(concept=CONCEPT_QN, context_ref="ctx1", unit_ref=None, value="1")
        inst = _make_instance([fact], {"ctx1": ctx})
        taxonomy = _make_taxonomy(_all_open_hc(), dims={DIM_QN: _dim_model_with_members()})
        findings = DimensionalConstraintValidator(taxonomy).validate(inst)
        assert any(f.constraint_type == "CLOSED_MISSING_DIMENSION" for f in findings)

    def test_closed_hc_dimension_has_default_no_finding(self) -> None:
        """A missing dimension with a default member does not trigger the closed check."""
        dim_with_default = DimensionModel(
            qname=DIM_QN,
            dimension_type="explicit",
            default_member=MEM_QN_ES,  # has default
            members=(DomainMember(qname=MEM_QN_ES, parent=None, order=1.0),),
        )
        ctx = _make_context("ctx1", dims={})  # dimension absent but has default
        fact = Fact(concept=CONCEPT_QN, context_ref="ctx1", unit_ref=None, value="1")
        inst = _make_instance([fact], {"ctx1": ctx})
        taxonomy = _make_taxonomy(_all_closed_hc(), dims={DIM_QN: dim_with_default})
        findings = DimensionalConstraintValidator(taxonomy).validate(inst)
        assert not any(f.constraint_type == "CLOSED_MISSING_DIMENSION" for f in findings)

    def test_missing_eba_null_dimension_is_not_required(self) -> None:
        """EBA NullDimension is a placeholder and is not required in contexts."""
        null_dim = QName(
            namespace="http://www.eba.europa.eu/xbrl/ext/model",
            local_name="NullDimension",
        )
        hc = HypercubeModel(
            qname=QName(
                namespace="http://www.eurofiling.info/xbrl/ext/model",
                local_name="hyp",
            ),
            arcrole="all",
            closed=True,
            context_element="scenario",
            primary_items=(CONCEPT_QN,),
            dimensions=(null_dim,),
            extended_link_role="http://example.com/elr",
        )
        ctx = _make_context("ctx1", dims={})
        fact = Fact(concept=CONCEPT_QN, context_ref="ctx1", unit_ref=None, value="1")
        inst = _make_instance([fact], {"ctx1": ctx})
        taxonomy = _make_taxonomy(
            hc,
            dims={
                null_dim: DimensionModel(
                    qname=null_dim,
                    dimension_type="explicit",
                    default_member=None,
                    members=(),
                )
            },
        )

        findings = DimensionalConstraintValidator(taxonomy).validate(inst)

        assert not any(
            f.constraint_type == "CLOSED_MISSING_DIMENSION" and f.dimension_qname == null_dim
            for f in findings
        )

    def test_missing_dimension_with_unusable_default_is_invalid(self) -> None:
        """A default only satisfies a missing dimension when the member is usable."""
        dim_with_unusable_default = DimensionModel(
            qname=DIM_QN,
            dimension_type="explicit",
            default_member=MEM_QN_ES,
            members=(DomainMember(qname=MEM_QN_ES, parent=None, order=1.0, usable=False),),
        )
        ctx = _make_context("ctx1", dims={})
        fact = Fact(concept=CONCEPT_QN, context_ref="ctx1", unit_ref=None, value="1")
        inst = _make_instance([fact], {"ctx1": ctx})
        taxonomy = _make_taxonomy(_all_open_hc(), dims={DIM_QN: dim_with_unusable_default})

        findings = DimensionalConstraintValidator(taxonomy).validate(inst)

        assert any(
            f.rule_id == "xbrldie:PrimaryItemDimensionallyInvalidError"
            and f.constraint_type == "CLOSED_MISSING_DIMENSION"
            for f in findings
        )


# ---------------------------------------------------------------------------
# 4. PROHIBITED_COMBINATION
# ---------------------------------------------------------------------------


class TestProhibitedCombination:
    def test_not_all_all_dims_present_triggers_prohibited(self) -> None:
        """When all dimensions of a notAll hypercube are present, it is prohibited."""
        ctx = _make_context("ctx1", dims={DIM_QN: MEM_QN_ES})
        fact = Fact(concept=CONCEPT_QN, context_ref="ctx1", unit_ref=None, value="1")
        inst = _make_instance([fact], {"ctx1": ctx})
        taxonomy = _make_taxonomy_with_hcs(
            [_all_empty_hc(), _not_all_hc()],
            dims={DIM_QN: _dim_model_with_members()},
        )
        findings = DimensionalConstraintValidator(taxonomy).validate(inst)
        assert any(f.constraint_type == "PROHIBITED_COMBINATION" for f in findings)

    def test_not_all_without_positive_hypercube_is_not_a_drs(self) -> None:
        """An inherited negative hypercube only applies within positive ELR coverage."""
        ctx = _make_context("ctx1", dims={DIM_QN: MEM_QN_ES})
        fact = Fact(concept=CONCEPT_QN, context_ref="ctx1", unit_ref=None, value="1")
        inst = _make_instance([fact], {"ctx1": ctx})
        taxonomy = _make_taxonomy(_inherited_not_all_hc(), dims={DIM_QN: _dim_model_with_members()})

        findings = DimensionalConstraintValidator(taxonomy).validate(inst)

        assert not any(f.constraint_type == "PROHIBITED_COMBINATION" for f in findings)

    def test_not_all_dim_absent_no_finding(self) -> None:
        """When a notAll dimension is absent, the combination is not prohibited."""
        ctx = _make_context("ctx1", dims={})  # no dimensions present
        fact = Fact(concept=CONCEPT_QN, context_ref="ctx1", unit_ref=None, value="1")
        inst = _make_instance([fact], {"ctx1": ctx})
        taxonomy = _make_taxonomy_with_hcs(
            [_all_empty_hc(), _not_all_hc()],
            dims={DIM_QN: _dim_model_with_members()},
        )
        findings = DimensionalConstraintValidator(taxonomy).validate(inst)
        assert not any(f.constraint_type == "PROHIBITED_COMBINATION" for f in findings)

    def test_closed_not_all_with_extra_dimension_does_not_trigger(self) -> None:
        """A closed notAll cube only prohibits contexts valid for that cube."""
        extra_dim = _qn("ExtraDim", _DIM_NS)
        ctx = _make_context("ctx1", dims={DIM_QN: MEM_QN_ES, extra_dim: MEM_QN_PT})
        fact = Fact(concept=CONCEPT_QN, context_ref="ctx1", unit_ref=None, value="1")
        inst = _make_instance([fact], {"ctx1": ctx})
        taxonomy = _make_taxonomy_with_hcs(
            [_all_empty_hc(), _not_all_closed_hc()],
            dims={
                DIM_QN: _dim_model_with_members(),
                extra_dim: _dim_model_with_members(),
            },
        )

        findings = DimensionalConstraintValidator(taxonomy).validate(inst)

        assert not any(f.constraint_type == "PROHIBITED_COMBINATION" for f in findings)

    def test_prohibited_combination_source_is_dimensional(self) -> None:
        """PROHIBITED_COMBINATION findings have source='dimensional'."""
        ctx = _make_context("ctx1", dims={DIM_QN: MEM_QN_ES})
        fact = Fact(concept=CONCEPT_QN, context_ref="ctx1", unit_ref=None, value="1")
        inst = _make_instance([fact], {"ctx1": ctx})
        taxonomy = _make_taxonomy_with_hcs(
            [_all_empty_hc(), _not_all_hc()],
            dims={DIM_QN: _dim_model_with_members()},
        )
        findings = DimensionalConstraintValidator(taxonomy).validate(inst)
        for f in findings:
            if f.constraint_type == "PROHIBITED_COMBINATION":
                assert f.source == "dimensional"
                assert f.severity == ValidationSeverity.ERROR


# ---------------------------------------------------------------------------
# Concept not in any hypercube — skipped
# ---------------------------------------------------------------------------


class TestConceptNotInHypercube:
    def test_concept_not_in_any_hypercube_skipped(self) -> None:
        """A fact whose concept is not a primary item in any hypercube is not validated."""
        other_concept = _qn("OtherConcept")
        ctx = _make_context("ctx1", dims={DIM_QN: MEM_QN_ES})
        fact = Fact(concept=other_concept, context_ref="ctx1", unit_ref=None, value="1")
        inst = _make_instance([fact], {"ctx1": ctx})
        taxonomy = _make_taxonomy(_all_closed_hc(), dims={DIM_QN: _dim_model_with_members()})
        findings = DimensionalConstraintValidator(taxonomy).validate(inst)
        assert findings == []
