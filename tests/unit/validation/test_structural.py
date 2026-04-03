"""Unit tests for StructuralConformanceValidator (validation/structural.py)."""
from __future__ import annotations

from datetime import date
from pathlib import Path

import pytest

from bde_xbrl_editor.instance.models import (
    Fact,
    ReportingEntity,
    ReportingPeriod,
    XbrlContext,
    XbrlInstance,
    XbrlUnit,
)
from bde_xbrl_editor.taxonomy.models import (
    Concept,
    QName,
    TaxonomyStructure,
    TaxonomyMetadata,
    FormulaAssertionSet,
)
from bde_xbrl_editor.validation.models import ValidationSeverity
from bde_xbrl_editor.validation.structural import StructuralConformanceValidator

from datetime import datetime

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
    from datetime import datetime
    meta = TaxonomyMetadata(
        name="Test",
        version="1.0",
        publisher="Example",
        entry_point_path=Path("tax.xsd"),
        loaded_at=datetime(2024, 1, 1),
        declared_languages=("en",),
    )
    concept_qn = _qname("MyConcept")
    concept = Concept(
        qname=concept_qn,
        data_type=QName(namespace=_XSD_NS, local_name=type_local),
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
        inst.facts.append(
            Fact(concept=concept, context_ref="ctx1", unit_ref=None, value="100")
        )
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
        inst.facts.append(
            Fact(concept=concept_qn, context_ref="ctx1", unit_ref=None, value="1000")
        )
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
        inst.facts.append(
            Fact(concept=concept_qn, context_ref="ctx1", unit_ref=None, value="1000")
        )
        findings = StructuralConformanceValidator().validate(inst, taxonomy=None)
        assert not any(f.rule_id == "structural:unresolved-unit-ref" for f in findings)

    def test_numeric_fact_with_undeclared_unit_id(self) -> None:
        """A numeric fact referencing an undeclared unit_id triggers check 3."""
        inst = _minimal_instance()
        concept_qn = _qname("MyConcept")
        inst.facts.append(
            Fact(concept=concept_qn, context_ref="ctx1", unit_ref="USD", value="42")
        )
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
        inst.facts.append(
            Fact(concept=concept_qn, context_ref="ctx1", unit_ref=None, value="val")
        )
        taxonomy = _minimal_taxonomy(period_type="instant", type_local="stringItemType")
        findings = StructuralConformanceValidator().validate(inst, taxonomy)
        assert any(f.rule_id == "structural:period-type-mismatch" for f in findings)

    def test_duration_concept_used_with_instant_context(self) -> None:
        """A concept declared as duration used with an instant context triggers mismatch."""
        inst = _minimal_instance()
        concept_qn = _qname("MyConcept")
        inst.facts.append(
            Fact(concept=concept_qn, context_ref="ctx1", unit_ref=None, value="val")
        )
        taxonomy = _minimal_taxonomy(period_type="duration", type_local="stringItemType")
        findings = StructuralConformanceValidator().validate(inst, taxonomy)
        assert any(f.rule_id == "structural:period-type-mismatch" for f in findings)

    def test_matching_period_type_no_finding(self) -> None:
        """A concept and context with matching period_type produce no mismatch finding."""
        inst = _minimal_instance()
        concept_qn = _qname("MyConcept")
        inst.facts.append(
            Fact(concept=concept_qn, context_ref="ctx1", unit_ref=None, value="val")
        )
        taxonomy = _minimal_taxonomy(period_type="instant", type_local="stringItemType")
        findings = StructuralConformanceValidator().validate(inst, taxonomy)
        assert not any(f.rule_id == "structural:period-type-mismatch" for f in findings)

    def test_no_taxonomy_skips_period_check(self) -> None:
        """When taxonomy=None, check 5 is skipped."""
        inst = _minimal_instance()
        concept_qn = _qname("MyConcept")
        inst.facts.append(
            Fact(concept=concept_qn, context_ref="ctx1", unit_ref=None, value="val")
        )
        findings = StructuralConformanceValidator().validate(inst, taxonomy=None)
        assert not any(f.rule_id == "structural:period-type-mismatch" for f in findings)


# ---------------------------------------------------------------------------
# Check 6: duplicate-fact
# ---------------------------------------------------------------------------


class TestDuplicateFact:
    def test_two_identical_facts_triggers_duplicate(self) -> None:
        """Two facts with same (concept, context_ref, unit_ref) trigger duplicate-fact."""
        inst = _minimal_instance()
        concept = _qname("Revenue")
        inst.facts.append(Fact(concept=concept, context_ref="ctx1", unit_ref="EUR", value="100"))
        inst.facts.append(Fact(concept=concept, context_ref="ctx1", unit_ref="EUR", value="200"))
        findings = StructuralConformanceValidator().validate(inst)
        assert any(f.rule_id == "structural:duplicate-fact" for f in findings)

    def test_different_context_no_duplicate(self) -> None:
        """Two facts with the same concept but different contexts are not duplicates."""
        inst = _minimal_instance()
        inst.contexts["ctx2"] = _context("ctx2")
        concept = _qname("Revenue")
        inst.facts.append(Fact(concept=concept, context_ref="ctx1", unit_ref=None, value="100"))
        inst.facts.append(Fact(concept=concept, context_ref="ctx2", unit_ref=None, value="200"))
        findings = StructuralConformanceValidator().validate(inst)
        assert not any(f.rule_id == "structural:duplicate-fact" for f in findings)

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
# Clean instance: all checks pass
# ---------------------------------------------------------------------------


class TestCleanInstance:
    def test_clean_instance_no_findings(self) -> None:
        """A well-formed instance with all references resolved produces zero findings."""
        inst = _minimal_instance()
        concept_qn = _qname("MyConcept")
        inst.units["EUR"] = XbrlUnit(unit_id="EUR", measure_uri="iso4217:EUR")
        inst.facts.append(
            Fact(concept=concept_qn, context_ref="ctx1", unit_ref="EUR", value="500")
        )
        taxonomy = _minimal_taxonomy(period_type="instant", type_local="monetaryItemType")
        findings = StructuralConformanceValidator().validate(inst, taxonomy)
        assert findings == []

    def test_instance_no_facts_no_findings(self) -> None:
        """An instance with no facts produces no structural findings."""
        inst = _minimal_instance()
        findings = StructuralConformanceValidator().validate(inst)
        assert findings == []
