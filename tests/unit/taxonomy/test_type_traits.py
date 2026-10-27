"""Numeric consumers honor expanded type names and retained type ancestry."""

from dataclasses import replace
from datetime import date, datetime
from decimal import Decimal
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
from bde_xbrl_editor.instance.validator import XbrlTypeValidator
from bde_xbrl_editor.table_renderer.fact_formatter import FactFormatter
from bde_xbrl_editor.taxonomy import LoaderSettings, TaxonomyCache, TaxonomyLoader
from bde_xbrl_editor.taxonomy.models import (
    CalculationArc,
    Concept,
    QName,
    TaxonomyMetadata,
    TaxonomyStructure,
)
from bde_xbrl_editor.validation.calculation import CalculationConsistencyValidator
from bde_xbrl_editor.validation.structural import StructuralConformanceValidator

XBRLI = "http://www.xbrl.org/2003/instance"
XSD = "http://www.w3.org/2001/XMLSchema"
A = QName("urn:test", "A")
B = QName("urn:test", "B")


_DEFAULT_BASES = (QName(XBRLI, "monetaryItemType"), QName(XSD, "decimal"))


def concept(type_name="AmountType", bases=_DEFAULT_BASES, namespace="urn:custom"):
    return Concept(A, QName(namespace, type_name), "instant", data_type_ancestry=bases)


def taxonomy(declaration):
    return TaxonomyStructure(
        TaxonomyMetadata("Test", "1", "Test", Path("t.xsd"), datetime.now(), ("en",)),
        {A: declaration, B: replace(declaration, qname=B)},
        None,
        {},
        {"elr": [CalculationArc(A, B, 1, 1, "elr")]},
        {},
        (),
        {},
        (),
    )


def instance(*facts):
    entity = ReportingEntity("E", "urn:entity")
    period = ReportingPeriod("instant", instant_date=date(2026, 1, 1))
    return XbrlInstance(
        Path("t.xsd"),
        "t.xsd",
        entity,
        period,
        contexts={"c": XbrlContext("c", entity, period)},
        units={
            "u": XbrlUnit(
                "u", "EUR", measure_qname=QName("http://www.xbrl.org/2003/iso4217", "EUR")
            )
        },
        facts=list(facts),
    )


@pytest.mark.parametrize(
    "declaration,expected",
    [
        (concept(), "monetary"),
        (
            concept(
                "Counter",
                (
                    QName("urn:custom", "Other"),
                    QName(XSD, "int"),
                    QName(XSD, "integer"),
                    QName(XSD, "decimal"),
                ),
            ),
            "integer",
        ),
        (concept("Shares", (QName(XBRLI, "sharesItemType"), QName(XSD, "decimal"))), "decimal"),
        (concept("Ratio", (QName(XBRLI, "pureItemType"), QName(XSD, "decimal"))), "decimal"),
        (concept("Float", (QName(XSD, "float"),)), "float"),
        (concept("Double", (QName(XSD, "double"),)), "double"),
        (concept("decimalItemType", (), "urn:unrelated"), "string"),
        (concept("DecimalLookingString", (QName(XSD, "string"),)), "string"),
        (concept("integerItemType", (), XBRLI), "integer"),
        (concept("fractionItemType", (), XBRLI), "fraction"),
    ],
)
def test_complete_qname_and_closest_base_classification(declaration, expected):
    from bde_xbrl_editor.taxonomy.type_traits import concept_type_category

    assert concept_type_category(declaration) == expected


def test_legacy_absent_ancestry_is_conservative():
    from bde_xbrl_editor.taxonomy.type_traits import concept_type_category

    declaration = concept("decimalItemType", (), "urn:unrelated")
    object.__delattr__(declaration, "data_type_ancestry")
    assert concept_type_category(declaration) == "string"
    assert (
        concept_type_category(replace(concept(), data_type_ancestry=(), monetary_item_type=True))
        == "monetary"
    )


@pytest.mark.parametrize(
    "base",
    [
        QName(XBRLI, "monetaryItemType"),
        QName(XBRLI, "sharesItemType"),
        QName(XBRLI, "pureItemType"),
        QName(XSD, "decimal"),
    ],
)
def test_derived_decimal_editor_and_formatter_match_base(base):
    derived = taxonomy(concept(bases=(base, QName(XSD, "decimal"))))
    original = taxonomy(concept(base.local_name, (), base.namespace))
    for tax in (original, derived):
        validator = XbrlTypeValidator(tax, ",")
        assert not validator.validate("12.bad", A)[0]
        assert validator.normalise("1234,5600", A) == "1234.5600"
        assert FactFormatter(tax, ",").format("1234.5600", A, "0") == "1234,5600"


def test_derived_integer_keeps_strict_lexical_input():
    tax = taxonomy(
        concept("Counter", (QName(XSD, "int"), QName(XSD, "integer"), QName(XSD, "decimal")))
    )
    validator = XbrlTypeValidator(tax, ",")
    assert not validator.validate("12.9", A)[0]
    assert not validator.validate("12,9", A)[0]
    assert validator.validate("9" * 5000, A) == (True, "")
    assert validator.normalise("+00042", A) == "+00042"


def test_derived_numeric_calculation_and_units_match_base():
    derived = taxonomy(concept())
    original = taxonomy(concept("monetaryItemType", (), XBRLI))
    document = instance(
        Fact(A, "c", "u", "100", decimals="0"), Fact(B, "c", "u", "90", decimals="0")
    )
    for tax in (original, derived):
        assert [f.rule_id for f in CalculationConsistencyValidator().validate(document, tax)] == [
            "calculation:summation-inconsistent"
        ]
        missing = instance(Fact(A, "c", None, "100"))
        result = StructuralConformanceValidator().validate(missing, tax)
        assert "structural:unresolved-unit-ref" in [f.rule_id for f in result]
        assert "structural:decimals-precision" in [f.rule_id for f in result]


def test_namespace_collision_is_not_numeric_or_localized():
    declaration = concept("decimalItemType", (QName(XSD, "string"),), "urn:unrelated")
    tax = taxonomy(declaration)
    assert FactFormatter(tax, ",").format("1234.5600", A) == "1234.5600"
    assert XbrlTypeValidator(tax).validate("text", A) == (True, "")
    assert not StructuralConformanceValidator()._check_unresolved_unit_refs(
        instance(Fact(A, "c", None, "text")), tax
    )


@pytest.mark.parametrize("local", ["float", "double"])
def test_float_families_do_not_use_decimal_input_policy(local):
    tax = taxonomy(concept("Floating", (QName(XSD, local),)))
    for value in ("INF", "-INF", "NaN", "1.23E4"):
        assert XbrlTypeValidator(tax, ",").validate(value, A) == (True, "")
        assert XbrlTypeValidator(tax, ",").normalise(value, A) == value
        assert FactFormatter(tax, ",").format(value, A) == value


def test_formula_fact_and_filter_context_use_derived_types():
    from bde_xbrl_editor.validation.formula.evaluator import FormulaEvaluator
    from bde_xbrl_editor.validation.formula.filters import _general_filter_context_item

    tax = taxonomy(concept())
    fact = Fact(A, "c", "u", "1234.5600")
    evaluator = FormulaEvaluator(taxonomy=tax)
    assert evaluator._fact_atomic_type(fact) == "decimal"
    assert evaluator._coerce_fact_xpath_value(fact, namespaces={}, xpath_expr="$v + 1") == Decimal(
        "1234.5600"
    )
    string_tax = taxonomy(concept("DecimalLookingString", (QName(XSD, "string"),)))
    assert _general_filter_context_item(fact, ".", string_tax.concepts) == "1234.5600"


def test_loader_retains_real_local_named_type_chain(tmp_path):
    path = tmp_path / "taxonomy.xsd"
    path.write_text("""<xs:schema xmlns:xs="http://www.w3.org/2001/XMLSchema" xmlns:xbrli="http://www.xbrl.org/2003/instance" xmlns:t="urn:test" targetNamespace="urn:test">
      <xs:simpleType name="CountBase"><xs:restriction base="xs:int"/></xs:simpleType>
      <xs:simpleType name="CustomCount"><xs:restriction base="t:CountBase"/></xs:simpleType>
      <xs:element name="A" type="t:CustomCount" substitutionGroup="xbrli:item" xbrli:periodType="instant"/>
    </xs:schema>""")
    loaded = TaxonomyLoader(TaxonomyCache(), LoaderSettings(allow_network=False)).load(path)
    assert loaded.concepts[A].data_type_ancestry == (
        QName("urn:test", "CountBase"),
        QName(XSD, "int"),
    )
    assert not XbrlTypeValidator(loaded).validate("12.9", A)[0]


@pytest.mark.parametrize("local", ["float", "double"])
@pytest.mark.parametrize("value", ["1,23", "1.2,3", "12.bad", "Infinity", "+INF", "١٢"])
def test_float_families_reject_invalid_lexical_values(local, value):
    tax = taxonomy(concept("Floating", (QName(XSD, local),)))
    validator = XbrlTypeValidator(tax, ",")
    assert not validator.validate(value, A)[0]
    assert validator.normalise(value, A) == value


def test_formula_type_filter_and_xpath_nodes_retain_derived_families():
    from bde_xbrl_editor.validation.formula.evaluator import (
        FormulaEvaluator,
        _fact_node_xsd_type,
    )
    from bde_xbrl_editor.validation.formula.filters import _concept_data_type_matches

    declaration = concept()
    fact = Fact(A, "c", "u", "1.00")
    assert _concept_data_type_matches(
        fact, [QName(XBRLI, "monetaryItemType")], strict=False, concepts={A: declaration}
    )
    assert not _concept_data_type_matches(
        fact, [QName(XBRLI, "monetaryItemType")], strict=True, concepts={A: declaration}
    )
    assert not _concept_data_type_matches(
        fact, [QName("urn:other", "monetaryItemType")], strict=False, concepts={A: declaration}
    )
    for base in ("integer", "float", "double", "boolean", "date"):
        derived = concept("Derived", (QName(XSD, base),))
        assert _fact_node_xsd_type(derived, "1") == base
    floating = taxonomy(concept("Derived", (QName(XSD, "double"),)))
    evaluator = FormulaEvaluator(taxonomy=floating)
    assert (
        evaluator._coerce_fact_xpath_value(
            Fact(A, "c", "u", "1.25E2"), namespaces={}, xpath_expr="$v + 1"
        )
        == 125
    )


def test_essence_alias_numeric_equality_uses_derived_types():
    from bde_xbrl_editor.validation.essence_alias import _alias_values_equal

    left = Fact(A, "c", "u", "1.00", decimals="2")
    right = Fact(B, "c", "u", "1.0", decimals="2")
    assert _alias_values_equal(left, right, taxonomy(concept()))
    assert not _alias_values_equal(left, right, taxonomy(concept("Text", (QName(XSD, "string"),))))


@pytest.mark.parametrize(
    "name", ["int", "long", "unsignedInt", "positiveInteger", "nonNegativeInteger"]
)
def test_standard_direct_integer_variants_are_strict(name):
    for namespace, local in ((XSD, name), (XBRLI, name + "ItemType")):
        validator = XbrlTypeValidator(taxonomy(concept(local, (), namespace)))
        assert validator.validate("+000123", A) == (True, "")
        assert not validator.validate("12.9", A)[0]
        assert validator.normalise("12.9", A) == "12.9"
