"""Unit tests for StructuralConformanceValidator (validation/structural.py)."""

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
from bde_xbrl_editor.instance.s_equal import effective_s_equal_key
from bde_xbrl_editor.taxonomy.constants import NS_XBRLI
from bde_xbrl_editor.taxonomy.models import (
    Concept,
    DefinitionArc,
    FormulaAssertionSet,
    QName,
    TaxonomyMetadata,
    TaxonomyStructure,
)
from bde_xbrl_editor.validation.models import ValidationSeverity
from bde_xbrl_editor.validation.structural import StructuralConformanceValidator

# ---------------------------------------------------------------------------
# Reusable helpers
# ---------------------------------------------------------------------------

_NS = "http://example.com/taxonomy"
_XSD_NS = "http://www.w3.org/2001/XMLSchema"


def _qname(local: str, ns: str = _NS) -> QName:
    return QName(namespace=ns, local_name=local)


def _entity() -> ReportingEntity:
    return ReportingEntity(identifier="TEST001", scheme="http://www.example.com")


def _instant_period() -> ReportingPeriod:
    return ReportingPeriod(period_type="instant", instant_date=date(2024, 12, 31))


def _duration_period() -> ReportingPeriod:
    return ReportingPeriod(
        period_type="duration",
        start_date=date(2024, 1, 1),
        end_date=date(2024, 12, 31),
    )


def _context(ctx_id: str, period: ReportingPeriod | None = None) -> XbrlContext:
    return XbrlContext(
        context_id=ctx_id,
        entity=_entity(),
        period=period or _instant_period(),
    )


def _minimal_instance(schema_ref: str = "taxonomy.xsd") -> XbrlInstance:
    """Build the simplest valid XbrlInstance."""
    inst = XbrlInstance(
        taxonomy_entry_point=Path("taxonomy.xsd"),
        schema_ref_href=schema_ref,
        entity=_entity(),
        period=_instant_period(),
    )
    ctx = _context("ctx1")
    inst.contexts["ctx1"] = ctx
    return inst


def _minimal_taxonomy(
    period_type: str = "instant",
    type_local: str = "stringItemType",
) -> TaxonomyStructure:
    """Build a minimal TaxonomyStructure with one concept."""
    meta = TaxonomyMetadata(
        name="Test",
        version="1.0",
        publisher="Example",
        entry_point_path=Path("tax.xsd"),
        loaded_at=datetime(2024, 1, 1),
        declared_languages=("en",),
    )
    concept_qn = _qname("MyConcept")
    if type_local in {
        "monetaryItemType",
        "sharesItemType",
        "pureItemType",
        "decimalItemType",
    }:
        dt = QName(namespace=NS_XBRLI, local_name=type_local)
    else:
        dt = QName(namespace=_XSD_NS, local_name=type_local)
    concept = Concept(
        qname=concept_qn,
        data_type=dt,
        period_type=period_type,  # type: ignore[arg-type]
    )

    class _FakeLabelResolver:
        def get(self, *a, **kw):
            return None

    return TaxonomyStructure(
        metadata=meta,
        concepts={concept_qn: concept},
        labels=_FakeLabelResolver(),
        presentation={},
        calculation={},
        definition={},
        hypercubes=[],
        dimensions={},
        tables=[],
        formula_assertion_set=FormulaAssertionSet(),
    )


# ---------------------------------------------------------------------------
# Check 1: missing-schemaref
# ---------------------------------------------------------------------------


class TestMissingSchemaref:
    def test_missing_schemaref_empty_string(self) -> None:
        """An instance with an empty schema_ref_href triggers missing-schemaref."""
        inst = _minimal_instance(schema_ref="")
        findings = StructuralConformanceValidator().validate(inst)
        rule_ids = [f.rule_id for f in findings]
        assert "structural:missing-schemaref" in rule_ids

    def test_missing_schemaref_whitespace_only(self) -> None:
        """A whitespace-only schema_ref_href also triggers missing-schemaref."""
        inst = _minimal_instance(schema_ref="   ")
        findings = StructuralConformanceValidator().validate(inst)
        assert any(f.rule_id == "structural:missing-schemaref" for f in findings)

    def test_valid_schemaref_no_finding(self) -> None:
        """A non-empty schema_ref_href does not produce a missing-schemaref finding."""
        inst = _minimal_instance(schema_ref="http://example.com/taxonomy.xsd")
        findings = StructuralConformanceValidator().validate(inst)
        assert not any(f.rule_id == "structural:missing-schemaref" for f in findings)

    def test_missing_schemaref_severity_is_error(self) -> None:
        """missing-schemaref findings always have ERROR severity."""
        inst = _minimal_instance(schema_ref="")
        findings = StructuralConformanceValidator().validate(inst)
        for f in findings:
            if f.rule_id == "structural:missing-schemaref":
                assert f.severity == ValidationSeverity.ERROR


def test_requires_element_arc_reports_missing_required_concept(tmp_path: Path) -> None:
    source = _qname("TupleFlag")
    target = _qname("RequiredAmount")
    instance_path = tmp_path / "instance.xbrl"
    instance_path.write_text(
        f"""<xbrli:xbrl xmlns:xbrli="{NS_XBRLI}" xmlns:t="{_NS}">
  <t:TupleFlag/>
</xbrli:xbrl>""",
        encoding="utf-8",
    )
    inst = _minimal_instance()
    inst.source_path = instance_path

    taxonomy = _minimal_taxonomy()
    taxonomy = TaxonomyStructure(
        metadata=taxonomy.metadata,
        concepts={
            source: Concept(
                qname=source,
                data_type=QName(namespace=NS_XBRLI, local_name="tuple"),
                period_type="duration",
                substitution_group=QName(namespace=NS_XBRLI, local_name="tuple"),
            ),
            target: Concept(
                qname=target,
                data_type=QName(namespace=NS_XBRLI, local_name="monetaryItemType"),
                period_type="instant",
            ),
        },
        labels=taxonomy.labels,
        presentation={},
        calculation={},
        definition={
            "http://www.xbrl.org/2003/role/link": (
                DefinitionArc(
                    arcrole="http://www.xbrl.org/2003/arcrole/requires-element",
                    source=source,
                    target=target,
                    order=1.0,
                    extended_link_role="http://www.xbrl.org/2003/role/link",
                ),
            )
        },
        hypercubes=[],
        dimensions={},
        tables=[],
    )

    findings = StructuralConformanceValidator().validate(inst, taxonomy)

    assert any(f.rule_id == "structural:requires-element" for f in findings)


# ---------------------------------------------------------------------------
# Check 2: unresolved-context-ref
# ---------------------------------------------------------------------------


class TestUnresolvedContextRef:
    def test_fact_references_missing_context(self) -> None:
        """A fact whose context_ref is not in instance.contexts is flagged."""
        inst = _minimal_instance()
        concept = _qname("Amount")
        inst.facts.append(
            Fact(concept=concept, context_ref="ctx_MISSING", unit_ref=None, value="100")
        )
        findings = StructuralConformanceValidator().validate(inst)
        assert any(f.rule_id == "structural:unresolved-context-ref" for f in findings)

    def test_fact_references_valid_context(self) -> None:
        """A fact with a valid context_ref produces no unresolved-context-ref finding."""
        inst = _minimal_instance()
        concept = _qname("Amount")
        inst.facts.append(Fact(concept=concept, context_ref="ctx1", unit_ref=None, value="100"))
        findings = StructuralConformanceValidator().validate(inst)
        assert not any(f.rule_id == "structural:unresolved-context-ref" for f in findings)

    def test_unresolved_context_ref_carries_concept_and_context(self) -> None:
        """The finding for an unresolved context ref includes concept_qname and context_ref."""
        inst = _minimal_instance()
        concept = _qname("Ratio")
        inst.facts.append(
            Fact(concept=concept, context_ref="ctx_GHOST", unit_ref=None, value="0.5")
        )
        findings = StructuralConformanceValidator().validate(inst)
        match = next(
            (f for f in findings if f.rule_id == "structural:unresolved-context-ref"), None
        )
        assert match is not None
        assert match.concept_qname == concept
        assert match.context_ref == "ctx_GHOST"


# ---------------------------------------------------------------------------
# Check 3: unresolved-unit-ref
# ---------------------------------------------------------------------------


class TestUnresolvedUnitRef:
    def test_numeric_fact_missing_unit_ref(self) -> None:
        """A numeric fact with no unit_ref triggers unresolved-unit-ref."""
        inst = _minimal_instance()
        concept_qn = _qname("MyConcept")
        inst.facts.append(Fact(concept=concept_qn, context_ref="ctx1", unit_ref=None, value="1000"))
        taxonomy = _minimal_taxonomy(type_local="monetaryItemType")
        findings = StructuralConformanceValidator().validate(inst, taxonomy)
        assert any(f.rule_id == "structural:unresolved-unit-ref" for f in findings)

    def test_numeric_fact_with_declared_unit_passes(self) -> None:
        """A numeric fact referencing a declared unit passes check 3."""
        inst = _minimal_instance()
        inst.units["EUR"] = XbrlUnit(unit_id="EUR", measure_uri="iso4217:EUR")
        concept_qn = _qname("MyConcept")
        inst.facts.append(
            Fact(concept=concept_qn, context_ref="ctx1", unit_ref="EUR", value="1000")
        )
        taxonomy = _minimal_taxonomy(type_local="monetaryItemType")
        findings = StructuralConformanceValidator().validate(inst, taxonomy)
        assert not any(f.rule_id == "structural:unresolved-unit-ref" for f in findings)

    def test_non_numeric_fact_needs_no_unit(self) -> None:
        """A string-type fact with no unit_ref should not trigger check 3."""
        inst = _minimal_instance()
        concept_qn = _qname("MyConcept")
        inst.facts.append(
            Fact(concept=concept_qn, context_ref="ctx1", unit_ref=None, value="hello")
        )
        taxonomy = _minimal_taxonomy(type_local="stringItemType")
        findings = StructuralConformanceValidator().validate(inst, taxonomy)
        assert not any(f.rule_id == "structural:unresolved-unit-ref" for f in findings)

    def test_no_taxonomy_skips_unit_check(self) -> None:
        """When taxonomy=None, check 3 is skipped entirely."""
        inst = _minimal_instance()
        concept_qn = _qname("MyConcept")
        inst.facts.append(Fact(concept=concept_qn, context_ref="ctx1", unit_ref=None, value="1000"))
        findings = StructuralConformanceValidator().validate(inst, taxonomy=None)
        assert not any(f.rule_id == "structural:unresolved-unit-ref" for f in findings)

    def test_numeric_fact_with_undeclared_unit_id(self) -> None:
        """A numeric fact referencing an undeclared unit_id triggers check 3."""
        inst = _minimal_instance()
        concept_qn = _qname("MyConcept")
        inst.facts.append(Fact(concept=concept_qn, context_ref="ctx1", unit_ref="USD", value="42"))
        taxonomy = _minimal_taxonomy(type_local="monetaryItemType")
        findings = StructuralConformanceValidator().validate(inst, taxonomy)
        assert any(f.rule_id == "structural:unresolved-unit-ref" for f in findings)


# ---------------------------------------------------------------------------
# Check 4: incomplete-context
# ---------------------------------------------------------------------------


class TestIncompleteContext:
    def test_context_missing_entity_flagged(self) -> None:
        """A context whose entity is None triggers incomplete-context."""
        inst = XbrlInstance(
            taxonomy_entry_point=Path("tax.xsd"),
            schema_ref_href="tax.xsd",
            entity=_entity(),
            period=_instant_period(),
        )
        # Manually construct a context with entity=None by bypassing the dataclass
        ctx = XbrlContext.__new__(XbrlContext)
        ctx.context_id = "ctx_bad"
        ctx.entity = None  # type: ignore[assignment]
        ctx.period = _instant_period()
        ctx.dimensions = {}
        ctx.context_element = "scenario"
        inst.contexts["ctx_bad"] = ctx
        findings = StructuralConformanceValidator().validate(inst)
        assert any(f.rule_id == "structural:incomplete-context" for f in findings)

    def test_context_missing_period_flagged(self) -> None:
        """A context whose period is None triggers incomplete-context."""
        inst = XbrlInstance(
            taxonomy_entry_point=Path("tax.xsd"),
            schema_ref_href="tax.xsd",
            entity=_entity(),
            period=_instant_period(),
        )
        ctx = XbrlContext.__new__(XbrlContext)
        ctx.context_id = "ctx_no_period"
        ctx.entity = _entity()
        ctx.period = None  # type: ignore[assignment]
        ctx.dimensions = {}
        ctx.context_element = "scenario"
        inst.contexts["ctx_no_period"] = ctx
        findings = StructuralConformanceValidator().validate(inst)
        assert any(f.rule_id == "structural:incomplete-context" for f in findings)

    def test_complete_context_no_finding(self) -> None:
        """A complete context (entity + period) does not trigger incomplete-context."""
        inst = _minimal_instance()
        findings = StructuralConformanceValidator().validate(inst)
        assert not any(f.rule_id == "structural:incomplete-context" for f in findings)


# ---------------------------------------------------------------------------
# Check 5: period-type-mismatch
# ---------------------------------------------------------------------------


class TestPeriodTypeMismatch:
    def test_instant_concept_used_with_duration_context(self) -> None:
        """A concept declared as instant used with a duration context triggers mismatch."""
        inst = _minimal_instance()
        # Replace the default instant context with a duration context
        inst.contexts["ctx1"] = _context("ctx1", period=_duration_period())

        concept_qn = _qname("MyConcept")
        inst.facts.append(Fact(concept=concept_qn, context_ref="ctx1", unit_ref=None, value="val"))
        taxonomy = _minimal_taxonomy(period_type="instant", type_local="stringItemType")
        findings = StructuralConformanceValidator().validate(inst, taxonomy)
        assert any(f.rule_id == "structural:period-type-mismatch" for f in findings)

    def test_duration_concept_used_with_instant_context(self) -> None:
        """A concept declared as duration used with an instant context triggers mismatch."""
        inst = _minimal_instance()
        concept_qn = _qname("MyConcept")
        inst.facts.append(Fact(concept=concept_qn, context_ref="ctx1", unit_ref=None, value="val"))
        taxonomy = _minimal_taxonomy(period_type="duration", type_local="stringItemType")
        findings = StructuralConformanceValidator().validate(inst, taxonomy)
        assert any(f.rule_id == "structural:period-type-mismatch" for f in findings)

    def test_matching_period_type_no_finding(self) -> None:
        """A concept and context with matching period_type produce no mismatch finding."""
        inst = _minimal_instance()
        concept_qn = _qname("MyConcept")
        inst.facts.append(Fact(concept=concept_qn, context_ref="ctx1", unit_ref=None, value="val"))
        taxonomy = _minimal_taxonomy(period_type="instant", type_local="stringItemType")
        findings = StructuralConformanceValidator().validate(inst, taxonomy)
        assert not any(f.rule_id == "structural:period-type-mismatch" for f in findings)

    def test_no_taxonomy_skips_period_check(self) -> None:
        """When taxonomy=None, check 5 is skipped."""
        inst = _minimal_instance()
        concept_qn = _qname("MyConcept")
        inst.facts.append(Fact(concept=concept_qn, context_ref="ctx1", unit_ref=None, value="val"))
        findings = StructuralConformanceValidator().validate(inst, taxonomy=None)
        assert not any(f.rule_id == "structural:period-type-mismatch" for f in findings)


# ---------------------------------------------------------------------------
# Check 6: duplicate-fact
# ---------------------------------------------------------------------------


class TestDuplicateFact:
    def test_conflicting_duplicate_values_triggers_duplicate(self) -> None:
        """Same (concept, context_ref, unit_ref) with different values is duplicate-fact."""
        inst = _minimal_instance()
        concept = _qname("Revenue")
        inst.facts.append(Fact(concept=concept, context_ref="ctx1", unit_ref="EUR", value="100"))
        inst.facts.append(Fact(concept=concept, context_ref="ctx1", unit_ref="EUR", value="200"))
        findings = StructuralConformanceValidator().validate(inst)
        assert any(f.rule_id == "structural:duplicate-fact" for f in findings)

    def test_redundant_identical_values_no_duplicate_finding(self) -> None:
        """Same signature and identical values (redundant reporting) are allowed."""
        inst = _minimal_instance()
        concept = _qname("Revenue")
        inst.facts.append(Fact(concept=concept, context_ref="ctx1", unit_ref="EUR", value="100"))
        inst.facts.append(Fact(concept=concept, context_ref="ctx1", unit_ref="EUR", value="100"))
        findings = StructuralConformanceValidator().validate(inst)
        assert not any(f.rule_id == "structural:duplicate-fact" for f in findings)

    def test_different_context_no_duplicate(self) -> None:
        """Two facts with the same concept but non-S-equal contexts are not duplicates."""
        inst = _minimal_instance()
        inst.contexts["ctx2"] = _context("ctx2", period=_duration_period())
        concept = _qname("Revenue")
        inst.facts.append(Fact(concept=concept, context_ref="ctx1", unit_ref=None, value="100"))
        inst.facts.append(Fact(concept=concept, context_ref="ctx2", unit_ref=None, value="200"))
        findings = StructuralConformanceValidator().validate(inst)
        assert not any(f.rule_id == "structural:duplicate-fact" for f in findings)

    def test_s_equal_context_ids_still_trigger_duplicate_fact(self) -> None:
        """Different context @id values that are S-equal bind like one context (XBRL 2.1)."""
        inst = _minimal_instance()
        ctx1 = inst.contexts["ctx1"]
        ctx2 = _context("ctx_other")
        seq = effective_s_equal_key(ctx1)
        ctx1.s_equal_key = seq
        ctx2.s_equal_key = seq
        inst.contexts["ctx_other"] = ctx2
        concept = _qname("Revenue")
        inst.facts.append(Fact(concept=concept, context_ref="ctx1", unit_ref=None, value="100"))
        inst.facts.append(
            Fact(concept=concept, context_ref="ctx_other", unit_ref=None, value="200")
        )
        findings = StructuralConformanceValidator().validate(inst)
        assert any(f.rule_id == "structural:duplicate-fact" for f in findings)

    def test_different_unit_ref_no_duplicate(self) -> None:
        """Two facts with the same concept/context but different unit_refs are not duplicates."""
        inst = _minimal_instance()
        concept = _qname("Revenue")
        inst.facts.append(Fact(concept=concept, context_ref="ctx1", unit_ref="EUR", value="100"))
        inst.facts.append(Fact(concept=concept, context_ref="ctx1", unit_ref="USD", value="120"))
        findings = StructuralConformanceValidator().validate(inst)
        assert not any(f.rule_id == "structural:duplicate-fact" for f in findings)

    def test_duplicate_fact_finding_has_correct_source(self) -> None:
        """duplicate-fact findings have source='structural'."""
        inst = _minimal_instance()
        concept = _qname("Revenue")
        inst.facts.append(Fact(concept=concept, context_ref="ctx1", unit_ref=None, value="1"))
        inst.facts.append(Fact(concept=concept, context_ref="ctx1", unit_ref=None, value="2"))
        findings = StructuralConformanceValidator().validate(inst)
        for f in findings:
            if f.rule_id == "structural:duplicate-fact":
                assert f.source == "structural"


# ---------------------------------------------------------------------------
# Monetary ISO 4217 unit measure (structural:monetary-unit-measure)
# ---------------------------------------------------------------------------


class TestMonetaryIsoUnitMeasure:
    def test_monetary_with_pure_measure_fails(self) -> None:
        """Monetary facts must not use xbrli:pure as the unit measure."""
        inst = _minimal_instance()
        inst.units["pure"] = XbrlUnit(
            unit_id="pure", measure_uri="http://www.xbrl.org/2003/instance:pure"
        )
        concept_qn = _qname("MyConcept")
        inst.facts.append(
            Fact(concept=concept_qn, context_ref="ctx1", unit_ref="pure", value="100")
        )
        taxonomy = _minimal_taxonomy(type_local="monetaryItemType")
        findings = StructuralConformanceValidator().validate(inst, taxonomy)
        assert any(f.rule_id == "structural:monetary-unit-measure" for f in findings)

    def test_monetary_with_divide_unit_fails(self) -> None:
        inst = _minimal_instance()
        inst.units["u1"] = XbrlUnit(
            unit_id="u1",
            measure_uri="",
            unit_form="divide",
            simple_measure_count=0,
        )
        concept_qn = _qname("MyConcept")
        inst.facts.append(Fact(concept=concept_qn, context_ref="ctx1", unit_ref="u1", value="100"))
        taxonomy = _minimal_taxonomy(type_local="monetaryItemType")
        findings = StructuralConformanceValidator().validate(inst, taxonomy)
        assert any(
            f.rule_id == "structural:monetary-unit-measure" and "divide" in f.message
            for f in findings
        )

    def test_derived_monetary_flag_valid_eur(self) -> None:
        """Concepts flagged monetary_item_type accept a standard ISO unit."""
        inst = _minimal_instance()
        inst.units["EUR"] = XbrlUnit(unit_id="EUR", measure_uri="iso4217:EUR")
        concept_qn = _qname("RestrictedAssets")
        derived = Concept(
            qname=concept_qn,
            data_type=_qname("assetsItemType"),
            period_type="instant",
            monetary_item_type=True,
        )
        meta = TaxonomyMetadata(
            name="Test",
            version="1.0",
            publisher="Example",
            entry_point_path=Path("tax.xsd"),
            loaded_at=datetime(2024, 1, 1),
            declared_languages=("en",),
        )

        class _FakeLabelResolver:
            def get(self, *a, **kw):
                return None

        taxonomy = TaxonomyStructure(
            metadata=meta,
            concepts={concept_qn: derived},
            labels=_FakeLabelResolver(),
            presentation={},
            calculation={},
            definition={},
            hypercubes=[],
            dimensions={},
            tables=[],
            formula_assertion_set=FormulaAssertionSet(),
        )
        inst.facts.append(Fact(concept=concept_qn, context_ref="ctx1", unit_ref="EUR", value="500"))
        findings = StructuralConformanceValidator().validate(inst, taxonomy)
        assert not any(f.rule_id == "structural:monetary-unit-measure" for f in findings)

    def test_invalid_currency_local_name(self) -> None:
        inst = _minimal_instance()
        bad = QName(namespace="http://www.xbrl.org/2003/iso4217", local_name="us_dollars")
        inst.units["u1"] = XbrlUnit(
            unit_id="u1",
            measure_uri="iso4217:us_dollars",
            measure_qname=bad,
            simple_measure_count=1,
        )
        concept_qn = _qname("MyConcept")
        inst.facts.append(Fact(concept=concept_qn, context_ref="ctx1", unit_ref="u1", value="1"))
        taxonomy = _minimal_taxonomy(type_local="monetaryItemType")
        findings = StructuralConformanceValidator().validate(inst, taxonomy)
        assert any(f.rule_id == "structural:monetary-unit-measure" for f in findings)


# ---------------------------------------------------------------------------
# Segment/scenario substitution checks (structural:segment-scenario-substitution)
# ---------------------------------------------------------------------------


class TestSegmentScenarioSubstitutionChecks:
    def test_scenario_with_item_substitution_is_flagged(self) -> None:
        inst = _minimal_instance()
        ctx = inst.contexts["ctx1"]
        ctx.scenario_xml = (
            b'<xbrli:scenario xmlns:xbrli="http://www.xbrl.org/2003/instance" '
            b'xmlns:ex="http://example.com/taxonomy"><ex:BadItem/></xbrli:scenario>'
        )

        bad_qn = _qname("BadItem")
        taxonomy = _minimal_taxonomy(type_local="stringItemType")
        base = taxonomy.concepts[_qname("MyConcept")]
        taxonomy = TaxonomyStructure(
            metadata=taxonomy.metadata,
            concepts={
                **taxonomy.concepts,
                bad_qn: Concept(
                    qname=bad_qn,
                    data_type=base.data_type,
                    period_type=base.period_type,
                    substitution_group=QName(namespace=NS_XBRLI, local_name="item"),
                ),
            },
            labels=taxonomy.labels,
            presentation=taxonomy.presentation,
            calculation=taxonomy.calculation,
            definition=taxonomy.definition,
            hypercubes=taxonomy.hypercubes,
            dimensions=taxonomy.dimensions,
            tables=taxonomy.tables,
            formula_assertion_set=taxonomy.formula_assertion_set,
        )

        findings = StructuralConformanceValidator().validate(inst, taxonomy)
        assert any(
            f.rule_id == "structural:segment-scenario-substitution"
            and f.context_ref == "ctx1"
            and f.concept_qname == bad_qn
            for f in findings
        )

    def test_segment_with_dimension_member_is_not_flagged(self) -> None:
        inst = _minimal_instance()
        ctx = inst.contexts["ctx1"]
        ctx.segment_xml = (
            b'<xbrli:segment xmlns:xbrli="http://www.xbrl.org/2003/instance" '
            b'xmlns:ex="http://example.com/taxonomy"><ex:SomeDomainMember/></xbrli:segment>'
        )

        member_qn = _qname("SomeDomainMember")
        taxonomy = _minimal_taxonomy(type_local="stringItemType")
        base = taxonomy.concepts[_qname("MyConcept")]
        taxonomy = TaxonomyStructure(
            metadata=taxonomy.metadata,
            concepts={
                **taxonomy.concepts,
                member_qn: Concept(
                    qname=member_qn,
                    data_type=base.data_type,
                    period_type=base.period_type,
                    substitution_group=QName(
                        namespace="http://xbrl.org/2005/xbrldt",
                        local_name="dimensionItem",
                    ),
                ),
            },
            labels=taxonomy.labels,
            presentation=taxonomy.presentation,
            calculation=taxonomy.calculation,
            definition=taxonomy.definition,
            hypercubes=taxonomy.hypercubes,
            dimensions=taxonomy.dimensions,
            tables=taxonomy.tables,
            formula_assertion_set=taxonomy.formula_assertion_set,
        )

        findings = StructuralConformanceValidator().validate(inst, taxonomy)
        assert not any(f.rule_id == "structural:segment-scenario-substitution" for f in findings)

    def test_schema_based_substitution_check_flags_element_not_in_concepts(
        self, tmp_path: Path
    ) -> None:
        inst = _minimal_instance()
        ctx = inst.contexts["ctx1"]
        ctx.segment_xml = (
            b'<xbrli:segment xmlns:xbrli="http://www.xbrl.org/2003/instance" '
            b'xmlns:ex="http://example.com/taxonomy"><ex:BadFromSchemaOnly/></xbrli:segment>'
        )

        schema_path = tmp_path / "segment-substitution.xsd"
        schema_path.write_text(
            """<?xml version="1.0"?>
<xs:schema xmlns:xs="http://www.w3.org/2001/XMLSchema"
           xmlns:xbrli="http://www.xbrl.org/2003/instance"
           targetNamespace="http://example.com/taxonomy"
           xmlns:ex="http://example.com/taxonomy"
           elementFormDefault="qualified">
  <xs:import namespace="http://www.xbrl.org/2003/instance"
             schemaLocation="http://www.xbrl.org/2003/xbrl-instance-2003-12-31.xsd"/>
  <xs:element name="BadFromSchemaOnly"
              type="xbrli:stringItemType"
              substitutionGroup="xbrli:item"
              nillable="true"
              xbrli:periodType="duration"/>
</xs:schema>
""",
            encoding="utf-8",
        )

        taxonomy = _minimal_taxonomy(type_local="stringItemType")
        taxonomy = TaxonomyStructure(
            metadata=taxonomy.metadata,
            concepts=taxonomy.concepts,
            labels=taxonomy.labels,
            presentation=taxonomy.presentation,
            calculation=taxonomy.calculation,
            definition=taxonomy.definition,
            hypercubes=taxonomy.hypercubes,
            dimensions=taxonomy.dimensions,
            tables=taxonomy.tables,
            formula_assertion_set=taxonomy.formula_assertion_set,
            schema_files=(schema_path,),
        )

        findings = StructuralConformanceValidator().validate(inst, taxonomy)
        assert any(
            f.rule_id == "structural:segment-scenario-substitution"
            and f.context_ref == "ctx1"
            and f.concept_qname == QName("http://example.com/taxonomy", "BadFromSchemaOnly")
            for f in findings
        )

    def test_schema_substitution_groups_from_taxonomy_are_reused(self, monkeypatch) -> None:
        inst = _minimal_instance()
        ctx = inst.contexts["ctx1"]
        ctx.segment_xml = (
            b'<xbrli:segment xmlns:xbrli="http://www.xbrl.org/2003/instance" '
            b'xmlns:ex="http://example.com/taxonomy"><ex:BadFromSchemaMap/></xbrli:segment>'
        )

        def _fail_parse_schema_raw(*_args, **_kwargs):
            raise AssertionError("schema XML should not be reparsed")

        monkeypatch.setattr(
            "bde_xbrl_editor.validation.structural.parse_schema_raw",
            _fail_parse_schema_raw,
        )

        bad_qn = QName("http://example.com/taxonomy", "BadFromSchemaMap")
        taxonomy = _minimal_taxonomy(type_local="stringItemType")
        taxonomy = TaxonomyStructure(
            metadata=taxonomy.metadata,
            concepts=taxonomy.concepts,
            labels=taxonomy.labels,
            presentation=taxonomy.presentation,
            calculation=taxonomy.calculation,
            definition=taxonomy.definition,
            hypercubes=taxonomy.hypercubes,
            dimensions=taxonomy.dimensions,
            tables=taxonomy.tables,
            formula_assertion_set=taxonomy.formula_assertion_set,
            schema_files=(Path("would-have-been-reparsed.xsd"),),
            schema_substitution_groups={
                bad_qn: QName(namespace=NS_XBRLI, local_name="item"),
            },
        )

        findings = StructuralConformanceValidator().validate(inst, taxonomy)
        assert any(
            f.rule_id == "structural:segment-scenario-substitution"
            and f.context_ref == "ctx1"
            and f.concept_qname == bad_qn
            for f in findings
        )


# ---------------------------------------------------------------------------
# Decimals / precision checks (structural:decimals-precision)
# ---------------------------------------------------------------------------


class TestDecimalsPrecisionChecks:
    def test_numeric_fact_without_decimals_or_precision_is_flagged(self) -> None:
        inst = _minimal_instance()
        concept_qn = _qname("MyConcept")
        inst.units["pure"] = XbrlUnit(unit_id="pure", measure_uri="xbrli:pure")
        inst.facts.append(Fact(concept=concept_qn, context_ref="ctx1", unit_ref="pure", value="5.6"))
        taxonomy = _minimal_taxonomy(type_local="decimalItemType")

        findings = StructuralConformanceValidator().validate(inst, taxonomy)

        assert any(f.rule_id == "structural:decimals-precision" for f in findings)

    def test_numeric_fact_with_both_decimals_and_precision_is_flagged(self) -> None:
        inst = _minimal_instance()
        concept_qn = _qname("MyConcept")
        inst.units["pure"] = XbrlUnit(unit_id="pure", measure_uri="xbrli:pure")
        inst.facts.append(
            Fact(
                concept=concept_qn,
                context_ref="ctx1",
                unit_ref="pure",
                value="5.6",
                decimals="3",
                precision="4",
            )
        )
        taxonomy = _minimal_taxonomy(type_local="decimalItemType")

        findings = StructuralConformanceValidator().validate(inst, taxonomy)

        assert any(
            f.rule_id == "structural:decimals-precision"
            and "both decimals and precision" in f.message
            for f in findings
        )

    def test_nil_fact_with_decimals_or_precision_is_flagged(self) -> None:
        inst = _minimal_instance()
        concept_qn = _qname("MyConcept")
        inst.units["pure"] = XbrlUnit(unit_id="pure", measure_uri="xbrli:pure")
        inst.facts.append(
            Fact(
                concept=concept_qn,
                context_ref="ctx1",
                unit_ref="pure",
                value="",
                decimals="3",
                is_nil=True,
            )
        )
        taxonomy = _minimal_taxonomy(type_local="decimalItemType")

        findings = StructuralConformanceValidator().validate(inst, taxonomy)

        assert any(
            f.rule_id == "structural:decimals-precision" and "Nil fact" in f.message
            for f in findings
        )

    def test_numeric_fact_with_only_decimals_has_no_decimals_precision_finding(self) -> None:
        inst = _minimal_instance()
        concept_qn = _qname("MyConcept")
        inst.units["pure"] = XbrlUnit(unit_id="pure", measure_uri="xbrli:pure")
        inst.facts.append(
            Fact(
                concept=concept_qn,
                context_ref="ctx1",
                unit_ref="pure",
                value="5.6",
                decimals="4",
            )
        )
        taxonomy = _minimal_taxonomy(type_local="decimalItemType")

        findings = StructuralConformanceValidator().validate(inst, taxonomy)

        assert not any(f.rule_id == "structural:decimals-precision" for f in findings)


# ---------------------------------------------------------------------------
# Unit consistency checks (structural:unit-consistency)
# ---------------------------------------------------------------------------


class TestUnitConsistencyChecks:
    def test_invalid_xbrli_measure_local_name_is_flagged(self) -> None:
        inst = _minimal_instance()
        concept_qn = _qname("MyConcept")
        inst.units["u1"] = XbrlUnit(
            unit_id="u1",
            measure_uri="xbrli:impure",
            measure_qname=QName(namespace=NS_XBRLI, local_name="impure"),
            simple_measure_count=1,
            simple_measure_qnames=(QName(namespace=NS_XBRLI, local_name="impure"),),
        )
        inst.facts.append(
            Fact(
                concept=concept_qn,
                context_ref="ctx1",
                unit_ref="u1",
                value="5.6",
                precision="4",
            )
        )
        taxonomy = _minimal_taxonomy(type_local="pureItemType")

        findings = StructuralConformanceValidator().validate(inst, taxonomy)

        assert any(
            f.rule_id == "structural:unit-consistency" and "xbrli measure 'impure'" in f.message
            for f in findings
        )

    def test_shares_item_requires_single_xbrli_shares_measure(self) -> None:
        inst = _minimal_instance()
        concept_qn = _qname("MyConcept")
        pure = QName(namespace=NS_XBRLI, local_name="pure")
        inst.units["u1"] = XbrlUnit(
            unit_id="u1",
            measure_uri="xbrli:pure xbrli:pure",
            simple_measure_count=2,
            simple_measure_qnames=(pure, pure),
        )
        inst.facts.append(
            Fact(
                concept=concept_qn,
                context_ref="ctx1",
                unit_ref="u1",
                value="1000",
                precision="4",
            )
        )
        taxonomy = _minimal_taxonomy(type_local="sharesItemType")

        findings = StructuralConformanceValidator().validate(inst, taxonomy)

        assert any(
            f.rule_id == "structural:unit-consistency"
            and "exactly one xbrli:shares" in f.message
            for f in findings
        )

    def test_shares_item_rejects_unqualified_shares_measure(self) -> None:
        inst = _minimal_instance()
        concept_qn = _qname("MyConcept")
        inst.units["u1"] = XbrlUnit(
            unit_id="u1",
            measure_uri="shares",
            measure_qname=QName(namespace="", local_name="shares"),
            simple_measure_count=1,
            simple_measure_qnames=(QName(namespace="", local_name="shares"),),
        )
        inst.facts.append(
            Fact(
                concept=concept_qn,
                context_ref="ctx1",
                unit_ref="u1",
                value="1000",
                precision="4",
            )
        )
        taxonomy = _minimal_taxonomy(type_local="sharesItemType")

        findings = StructuralConformanceValidator().validate(inst, taxonomy)

        assert any(f.rule_id == "structural:unit-consistency" for f in findings)

    def test_divide_unit_with_cancelled_measures_is_flagged(self) -> None:
        inst = _minimal_instance()
        concept_qn = _qname("MyConcept")
        feet = _qname("feet")
        inst.units["u1"] = XbrlUnit(
            unit_id="u1",
            measure_uri="",
            unit_form="divide",
            numerator_measure_qnames=(_qname("pure"), feet),
            denominator_measure_qnames=(feet,),
        )
        inst.facts.append(
            Fact(
                concept=concept_qn,
                context_ref="ctx1",
                unit_ref="u1",
                value="5.6",
                precision="4",
            )
        )
        taxonomy = _minimal_taxonomy(type_local="decimalItemType")

        findings = StructuralConformanceValidator().validate(inst, taxonomy)

        assert any(
            f.rule_id == "structural:unit-consistency" and "simplest form" in f.message
            for f in findings
        )

    def test_valid_shares_unit_has_no_unit_consistency_finding(self) -> None:
        inst = _minimal_instance()
        concept_qn = _qname("MyConcept")
        shares = QName(namespace=NS_XBRLI, local_name="shares")
        inst.units["shares"] = XbrlUnit(
            unit_id="shares",
            measure_uri="xbrli:shares",
            measure_qname=shares,
            simple_measure_count=1,
            simple_measure_qnames=(shares,),
        )
        inst.facts.append(
            Fact(
                concept=concept_qn,
                context_ref="ctx1",
                unit_ref="shares",
                value="1000",
                precision="4",
            )
        )
        taxonomy = _minimal_taxonomy(type_local="sharesItemType")

        findings = StructuralConformanceValidator().validate(inst, taxonomy)

        assert not any(f.rule_id == "structural:unit-consistency" for f in findings)


# ---------------------------------------------------------------------------
# Essence-alias unit checks (structural:essence-alias-unit)
# ---------------------------------------------------------------------------


class TestEssenceAliasUnitChecks:
    def test_essence_alias_facts_with_different_units_are_flagged(self) -> None:
        inst = _minimal_instance()
        concept_a = _qname("ConceptA")
        concept_b = _qname("ConceptB")
        inst.units["feet"] = XbrlUnit(
            unit_id="feet",
            measure_uri="ex:feet",
            measure_qname=_qname("feet"),
            simple_measure_count=1,
            simple_measure_qnames=(_qname("feet"),),
        )
        inst.units["pounds"] = XbrlUnit(
            unit_id="pounds",
            measure_uri="ex:pounds",
            measure_qname=_qname("pounds"),
            simple_measure_count=1,
            simple_measure_qnames=(_qname("pounds"),),
        )
        inst.facts.extend(
            [
                Fact(concept_a, "ctx1", "feet", "5.6", precision="4"),
                Fact(concept_b, "ctx1", "pounds", "5.6", precision="4"),
            ]
        )
        taxonomy = _minimal_taxonomy(type_local="decimalItemType")
        base = taxonomy.concepts[_qname("MyConcept")]
        taxonomy = TaxonomyStructure(
            metadata=taxonomy.metadata,
            concepts={
                concept_a: Concept(
                    qname=concept_a,
                    data_type=base.data_type,
                    period_type=base.period_type,
                ),
                concept_b: Concept(
                    qname=concept_b,
                    data_type=base.data_type,
                    period_type=base.period_type,
                ),
            },
            labels=taxonomy.labels,
            presentation=taxonomy.presentation,
            calculation=taxonomy.calculation,
            definition={
                "http://www.xbrl.org/2003/role/link": [
                    DefinitionArc(
                        arcrole="http://www.xbrl.org/2003/arcrole/essence-alias",
                        source=concept_a,
                        target=concept_b,
                        order=1.0,
                        extended_link_role="http://www.xbrl.org/2003/role/link",
                    )
                ]
            },
            hypercubes=taxonomy.hypercubes,
            dimensions=taxonomy.dimensions,
            tables=taxonomy.tables,
            formula_assertion_set=taxonomy.formula_assertion_set,
        )

        findings = StructuralConformanceValidator().validate(inst, taxonomy)

        assert any(f.rule_id == "structural:essence-alias-unit" for f in findings)


# ---------------------------------------------------------------------------
# Clean instance: all checks pass
# ---------------------------------------------------------------------------


class TestCleanInstance:
    def test_clean_instance_no_findings(self) -> None:
        """A well-formed instance with all references resolved produces zero findings."""
        inst = _minimal_instance()
        concept_qn = _qname("MyConcept")
        inst.units["EUR"] = XbrlUnit(unit_id="EUR", measure_uri="iso4217:EUR")
        inst.facts.append(
            Fact(
                concept=concept_qn,
                context_ref="ctx1",
                unit_ref="EUR",
                value="500",
                decimals="0",
            )
        )
        taxonomy = _minimal_taxonomy(period_type="instant", type_local="monetaryItemType")
        findings = StructuralConformanceValidator().validate(inst, taxonomy)
        assert findings == []

    def test_instance_no_facts_no_findings(self) -> None:
        """An instance with no facts produces no structural findings."""
        inst = _minimal_instance()
        findings = StructuralConformanceValidator().validate(inst)
        assert findings == []
