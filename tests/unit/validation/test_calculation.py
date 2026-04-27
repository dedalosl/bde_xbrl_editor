"""Unit tests for CalculationConsistencyValidator (validation/calculation.py)."""
from __future__ import annotations

from datetime import date, datetime
from pathlib import Path

from bde_xbrl_editor.instance.models import (
    Fact,
    ReportingEntity,
    ReportingPeriod,
    XbrlContext,
    XbrlInstance,
    XbrlUnit,
)
from bde_xbrl_editor.instance.s_equal import build_s_equal_key_from_xml_fragments
from bde_xbrl_editor.taxonomy.constants import NS_XBRLI
from bde_xbrl_editor.taxonomy.models import (
    CalculationArc,
    Concept,
    FormulaAssertionSet,
    QName,
    TaxonomyMetadata,
    TaxonomyStructure,
)
from bde_xbrl_editor.validation.calculation import CalculationConsistencyValidator
from bde_xbrl_editor.validation.models import ValidationSeverity

_NS = "http://example.com/calc-test"
_ELR = "http://www.xbrl.org/2003/role/link"


def _q(local: str) -> QName:
    return QName(namespace=_NS, local_name=local)


def _entity() -> ReportingEntity:
    return ReportingEntity(identifier="E1", scheme="http://www.example.com")


def _instant_ctx(ctx_id: str = "ctx1") -> XbrlContext:
    return XbrlContext(
        context_id=ctx_id,
        entity=_entity(),
        period=ReportingPeriod(period_type="instant", instant_date=date(2006, 7, 28)),
    )


def _monetary_concept(name: str) -> Concept:
    qn = _q(name)
    return Concept(
        qname=qn,
        data_type=QName(namespace=NS_XBRLI, local_name="monetaryItemType"),
        period_type="instant",
        monetary_item_type=True,
    )


def _taxonomy_summation_a_equals_b() -> TaxonomyStructure:
    """Single summation-item arc: A (parent) = B (child) with weight 1."""
    qa, qb = _q("A"), _q("B")
    concepts = {qa: _monetary_concept("A"), qb: _monetary_concept("B")}
    arcs = [
        CalculationArc(parent=qa, child=qb, order=1.0, weight=1.0, extended_link_role=_ELR),
    ]
    meta = TaxonomyMetadata(
        name="CalcTest",
        version="1.0",
        publisher="Test",
        entry_point_path=Path("t.xsd"),
        loaded_at=datetime(2024, 1, 1),
        declared_languages=("en",),
    )

    class _FakeLabels:
        def get(self, *a, **kw):
            return None

    return TaxonomyStructure(
        metadata=meta,
        concepts=concepts,
        labels=_FakeLabels(),
        presentation={},
        calculation={_ELR: arcs},
        definition={},
        hypercubes=[],
        dimensions={},
        tables=[],
        formula_assertion_set=FormulaAssertionSet(),
    )


def _taxonomy_with_abc_calculation() -> TaxonomyStructure:
    qa, qb, qc = _q("A"), _q("B"), _q("C")
    concepts = {
        qa: _monetary_concept("A"),
        qb: _monetary_concept("B"),
        qc: _monetary_concept("C"),
    }
    arcs = [
        CalculationArc(parent=qa, child=qb, order=1.0, weight=1.0, extended_link_role=_ELR),
        CalculationArc(parent=qa, child=qc, order=2.0, weight=1.0, extended_link_role=_ELR),
    ]
    meta = TaxonomyMetadata(
        name="CalcTest",
        version="1.0",
        publisher="Test",
        entry_point_path=Path("t.xsd"),
        loaded_at=datetime(2024, 1, 1),
        declared_languages=("en",),
    )

    class _FakeLabels:
        def get(self, *a, **kw):
            return None

    return TaxonomyStructure(
        metadata=meta,
        concepts=concepts,
        labels=_FakeLabels(),
        presentation={},
        calculation={_ELR: arcs},
        definition={},
        hypercubes=[],
        dimensions={},
        tables=[],
        formula_assertion_set=FormulaAssertionSet(),
    )


def _instance_with_facts(facts: list[Fact]) -> XbrlInstance:
    inst = XbrlInstance(
        taxonomy_entry_point=Path("t.xsd"),
        schema_ref_href="t.xsd",
        entity=_entity(),
        period=ReportingPeriod(period_type="instant", instant_date=date(2006, 7, 28)),
    )
    inst.contexts["ctx1"] = _instant_ctx()
    inst.units["u1"] = XbrlUnit(
        unit_id="u1",
        measure_uri="iso4217:EUR",
        measure_qname=QName(
            namespace="http://www.xbrl.org/2003/iso4217",
            local_name="EUR",
        ),
    )
    for f in facts:
        inst.add_fact(f)
    return inst


def test_calculation_consistent_infer_precision_like_320_00() -> None:
    """Mixed precision/decimals roll up (conformance 320-00 style)."""
    tax = _taxonomy_with_abc_calculation()
    inst = _instance_with_facts(
        [
            Fact(_q("A"), "ctx1", "u1", "1559", precision="2"),
            Fact(_q("B"), "ctx1", "u1", "984.8", precision="3"),
            Fact(_q("C"), "ctx1", "u1", "582.334973", decimals="1"),
        ]
    )
    findings = CalculationConsistencyValidator().validate(inst, tax)
    assert not findings


def test_calculation_inconsistent_like_320_17() -> None:
    """A != B + C with decimals 0 (simple roll-up)."""
    tax = _taxonomy_with_abc_calculation()
    inst = _instance_with_facts(
        [
            Fact(_q("A"), "ctx1", "u1", "1", decimals="0"),
            Fact(_q("B"), "ctx1", "u1", "1", decimals="0"),
            Fact(_q("C"), "ctx1", "u1", "1", decimals="0"),
        ]
    )
    findings = CalculationConsistencyValidator().validate(inst, tax)
    assert len(findings) == 1
    assert findings[0].rule_id == "calculation:summation-inconsistent"
    assert findings[0].severity == ValidationSeverity.ERROR
    assert findings[0].source == "calculation"


def test_calculation_inconsistent_when_bound_facts_have_zero_precision() -> None:
    """Conformance 320-07: precision=0 facts still bind and report inconsistency."""
    tax = _taxonomy_with_abc_calculation()
    inst = _instance_with_facts(
        [
            Fact(_q("A"), "ctx1", "u1", "1.25", precision="0"),
            Fact(_q("B"), "ctx1", "u1", "1", precision="0"),
            Fact(_q("C"), "ctx1", "u1", "0.25", precision="0"),
        ]
    )

    findings = CalculationConsistencyValidator().validate(inst, tax)

    assert [finding.rule_id for finding in findings] == [
        "calculation:summation-inconsistent"
    ]


def test_calculation_inconsistent_like_320_16() -> None:
    """Small contributor rounded away at decimals=0."""
    tax = _taxonomy_with_abc_calculation()
    inst = _instance_with_facts(
        [
            Fact(_q("A"), "ctx1", "u1", "4001", decimals="0"),
            Fact(_q("B"), "ctx1", "u1", "4000", decimals="0"),
            Fact(_q("C"), "ctx1", "u1", "0.01", decimals="0"),
        ]
    )
    findings = CalculationConsistencyValidator().validate(inst, tax)
    assert len(findings) == 1


def test_nil_contributor_treated_as_zero() -> None:
    """Missing numeric value on a contributor is skipped (implicit zero)."""
    tax = _taxonomy_with_abc_calculation()
    inst = _instance_with_facts(
        [
            Fact(_q("A"), "ctx1", "u1", "100", decimals="0"),
            Fact(_q("B"), "ctx1", "u1", "100", decimals="0"),
            Fact(_q("C"), "ctx1", "u1", "", decimals="0"),
        ]
    )
    findings = CalculationConsistencyValidator().validate(inst, tax)
    assert not findings


def test_duplicate_fact_key_skips_calculation_row() -> None:
    """Two facts for the same concept/context/unit block calc for that binding."""
    tax = _taxonomy_with_abc_calculation()
    inst = _instance_with_facts(
        [
            Fact(_q("A"), "ctx1", "u1", "2", decimals="0"),
            Fact(_q("B"), "ctx1", "u1", "1", decimals="0"),
            Fact(_q("B"), "ctx1", "u1", "1", decimals="0"),
            Fact(_q("C"), "ctx1", "u1", "1", decimals="0"),
        ]
    )
    findings = CalculationConsistencyValidator().validate(inst, tax)
    assert not findings


def test_summation_binds_across_s_equal_context_ids_302_11_style() -> None:
    """302.11: A and B in different context @id that are S-equal must roll up together."""
    tax = _taxonomy_summation_a_equals_b()
    e = _entity()
    p = ReportingPeriod(period_type="instant", instant_date=date(2006, 7, 28))
    sk = build_s_equal_key_from_xml_fragments(e, p, None, None)
    inst = XbrlInstance(
        taxonomy_entry_point=Path("t.xsd"),
        schema_ref_href="t.xsd",
        entity=e,
        period=p,
    )
    inst.contexts["c1"] = XbrlContext(
        context_id="c1", entity=e, period=p, s_equal_key=sk
    )
    inst.contexts["c2"] = XbrlContext(
        context_id="c2", entity=e, period=p, s_equal_key=sk
    )
    inst.units["u1"] = XbrlUnit(
        unit_id="u1",
        measure_uri="iso4217:EUR",
        measure_qname=QName(
            namespace="http://www.xbrl.org/2003/iso4217",
            local_name="EUR",
        ),
    )
    inst.add_fact(Fact(_q("A"), "c1", "u1", "1000", decimals="0"))
    inst.add_fact(Fact(_q("B"), "c2", "u1", "2000", decimals="0"))
    findings = CalculationConsistencyValidator().validate(inst, tax)
    assert len(findings) == 1
    assert findings[0].rule_id == "calculation:summation-inconsistent"
