"""Tests for the public Formula engine entry point and output comparison."""

from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
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
    Concept,
    FactVariableDefinition,
    FormulaAssertionSet,
    FormulaOutputDefinition,
    QName,
    TaxonomyMetadata,
    TaxonomyStructure,
)
from bde_xbrl_editor.validation.formula.output_instance import compare_output_instances
from bde_xbrl_editor.validation.formula.processor import FormulaProcessor

_NS = "http://example.com/taxonomy"
_XBRLI_NS = "http://www.xbrl.org/2003/instance"
_AMOUNT = QName(_NS, "Amount", "ex")
_EUR = QName("http://www.xbrl.org/2003/iso4217", "EUR", "iso4217")


def _taxonomy(*formulas: FormulaOutputDefinition) -> TaxonomyStructure:
    concept = Concept(
        qname=_AMOUNT,
        data_type=QName(_XBRLI_NS, "monetaryItemType", "xbrli"),
        period_type="instant",
    )
    return TaxonomyStructure(
        metadata=TaxonomyMetadata(
            name="Test taxonomy",
            version="1",
            publisher="Test",
            entry_point_path=Path("taxonomy.xsd"),
            loaded_at=datetime(2026, 1, 1),
            declared_languages=("en",),
        ),
        concepts={_AMOUNT: concept},
        labels={},
        presentation={},
        calculation={},
        definition={},
        hypercubes=(),
        dimensions={},
        tables=(),
        formula_assertion_set=FormulaAssertionSet(output_formulas=formulas),
        custom_functions=(),
    )


def _instance(*, context_id: str = "c1", unit_id: str = "u1", value: str = "1") -> XbrlInstance:
    entity = ReportingEntity("ENTITY", "http://example.com/entity")
    period = ReportingPeriod("instant", instant_date=date(2025, 12, 31))
    instance = XbrlInstance(
        taxonomy_entry_point=Path("taxonomy.xsd"),
        schema_ref_href="taxonomy.xsd",
        entity=entity,
        period=period,
    )
    instance.contexts[context_id] = XbrlContext(context_id, entity, period)
    instance.units[unit_id] = XbrlUnit(
        unit_id,
        "iso4217:EUR",
        measure_qname=_EUR,
        simple_measure_count=1,
        simple_measure_qnames=(_EUR,),
    )
    instance.facts.append(
        Fact(
            concept=_AMOUNT,
            context_ref=context_id,
            unit_ref=unit_id,
            value=value,
            decimals="2",
        )
    )
    return instance


def test_formula_processor_generates_output_without_conformance_expectations() -> None:
    formula = FormulaOutputDefinition(
        formula_id="output",
        label=None,
        value_xpath="$amount + 1",
        source="amount",
        aspect_model="dimensional",
        implicit_filtering=True,
        variables=(FactVariableDefinition(variable_name="amount", concept_filter=_AMOUNT),),
    )

    result = FormulaProcessor(_taxonomy(formula)).evaluate(_instance())

    assert len(result.output_instance.facts) == 1
    assert Decimal(result.output_instance.facts[0].value) == Decimal(2)


def test_formula_processor_reports_output_runtime_errors_for_every_formula() -> None:
    formula = FormulaOutputDefinition(
        formula_id="output",
        label=None,
        value_xpath="1 div 0",
        source="amount",
        aspect_model="dimensional",
        implicit_filtering=True,
        variables=(FactVariableDefinition(variable_name="amount", concept_filter=_AMOUNT),),
    )

    result = FormulaProcessor(_taxonomy(formula)).evaluate(_instance())

    assert "err:FOAR0001" in {finding.rule_id for finding in result.findings}


def test_output_instance_comparison_is_semantic_not_identifier_or_lexical() -> None:
    actual = _instance(context_id="generated-context", unit_id="generated-unit", value="1.00")
    expected = _instance(context_id="expected-context", unit_id="expected-unit", value="1.0")

    comparison = compare_output_instances(actual, expected, _taxonomy())

    assert comparison.matched
    assert comparison.missing_facts == 0
    assert comparison.unexpected_facts == 0
