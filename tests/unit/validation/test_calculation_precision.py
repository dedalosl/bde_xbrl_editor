"""Calculation precision is operand-derived, exact, and independent of ambient context."""

from dataclasses import replace
from decimal import ROUND_UP, Decimal, Inexact, Rounded, localcontext

import pytest
from lxml import etree

from bde_xbrl_editor.instance.models import Fact
from bde_xbrl_editor.taxonomy.linkbases.calculation import parse_calculation_linkbase_from_root
from bde_xbrl_editor.validation.calculation import CalculationConsistencyValidator, _round_fact
from bde_xbrl_editor.validation.orchestrator import InstanceValidator
from tests.unit.validation.test_calculation import (
    _ELR,
    _instance_with_facts,
    _q,
    _taxonomy_summation_a_equals_b,
    _taxonomy_with_abc_calculation,
)


def fact(name, value, **accuracy):
    return Fact(_q(name), "ctx1", "u1", value, **accuracy)


def run(values, taxonomy=None):
    return CalculationConsistencyValidator().validate(
        _instance_with_facts(values), taxonomy or _taxonomy_summation_a_equals_b()
    )


@pytest.mark.parametrize(
    "raw,accuracy,expected",
    [
        ("12345678901234567890123456789", {"decimals": "0"}, "12345678901234567890123456789"),
        ("1.2345E400", {"precision": "3"}, "1.23E400"),
        ("1.2345E-400", {"precision": "3"}, "1.23E-400"),
        ("1.123456789012345678901234567895", {"decimals": "29"}, "1.12345678901234567890123456790"),
        ("-123550", {"decimals": "-2"}, "-123600"),
    ],
)
def test_rounding_large_tiny_and_ties(raw, accuracy, expected):
    assert _round_fact(fact("A", raw, **accuracy)) == Decimal(expected)


@pytest.mark.parametrize("delta", [0, 1])
def test_real_validator_and_orchestrator_large_integer(delta):
    total = "12345678901234567890123456789"
    other = "1234567890123456789012345678" + str(9 - delta)
    values = [fact("A", total, decimals="0"), fact("B", other, decimals="0")]
    findings = run(values)
    assert [f.rule_id for f in findings] == (
        ["calculation:summation-inconsistent"] if delta else []
    )
    report = InstanceValidator(
        _taxonomy_summation_a_equals_b(), include_dimensional=False, include_formula=False
    ).validate_sync(_instance_with_facts(values))
    assert [f.rule_id for f in report.findings if f.source == "calculation"] == (
        ["calculation:summation-inconsistent"] if delta else []
    )
    assert values[0].value == total


def test_exact_sum_and_weighted_cancellation_under_hostile_context():
    tax = _taxonomy_with_abc_calculation()
    values = [
        fact("A", "10000000000000000000000000001", decimals="INF"),
        fact("B", "10000000000000000000000000000", decimals="INF"),
        fact("C", "1", decimals="INF"),
    ]
    with localcontext() as ctx:
        ctx.prec = 3
        ctx.rounding = ROUND_UP
        ctx.Emax = 10
        ctx.Emin = -10
        ctx.traps[Inexact] = True
        ctx.traps[Rounded] = True
        before = ctx.copy()
        assert run(values, tax) == []
        assert ctx == before or (
            ctx.prec,
            ctx.rounding,
            ctx.Emax,
            ctx.Emin,
            ctx.traps,
            ctx.flags,
        ) == (before.prec, before.rounding, before.Emax, before.Emin, before.traps, before.flags)
    arcs = list(tax.calculation[_ELR])
    arcs[1] = replace(arcs[1], weight=Decimal("-1"))
    tax = replace(tax, calculation={_ELR: arcs})
    assert (
        run(
            [
                fact("A", "1", decimals="INF"),
                fact("B", "10000000000000000000000000001", decimals="INF"),
                fact("C", "10000000000000000000000000000", decimals="INF"),
            ],
            tax,
        )
        == []
    )


def test_extreme_alignment_returns_explicit_incomplete_finding():
    tax = _taxonomy_with_abc_calculation()
    findings = run(
        [
            fact("A", "1E100001", decimals="INF"),
            fact("B", "1E100001", decimals="INF"),
            fact("C", "1", decimals="INF"),
        ],
        tax,
    )
    assert [f.rule_id for f in findings] == ["calculation:arithmetic-incomplete"]


def parsed_arcs(weights):
    arcs = "".join(
        f'<link:calculationArc xlink:from="a" xlink:to="b" xlink:arcrole="http://www.xbrl.org/2003/arcrole/summation-item" weight="{weight}" use="{use}" priority="{priority}"/>'
        for weight, use, priority in weights
    )
    root = etree.fromstring(
        f'<link:linkbase xmlns:link="http://www.xbrl.org/2003/linkbase" xmlns:xlink="http://www.w3.org/1999/xlink"><link:calculationLink xlink:role="{_ELR}"><link:loc xlink:href="t.xsd#a" xlink:label="a"/><link:loc xlink:href="t.xsd#b" xlink:label="b"/>{arcs}</link:calculationLink></link:linkbase>'
    )
    return parse_calculation_linkbase_from_root(root, {"a": _q("A"), "b": _q("B")})[_ELR]


def test_xml_weight_and_equivalence_preserve_exact_digits():
    first = "0.123456789012345678901234567891"
    second = "0.123456789012345678901234567892"
    with localcontext() as ctx:
        ctx.prec = 3
        arcs = parsed_arcs([(first, "optional", 0), (second, "prohibited", 1)])
    assert arcs[0].weight == Decimal(first)
    assert arcs[0].equivalence_key != arcs[1].equivalence_key
    assert CalculationConsistencyValidator._effective_summation_arcs(arcs) == [arcs[0]]
    tax = replace(_taxonomy_summation_a_equals_b(), calculation={_ELR: [arcs[0]]})
    assert run([fact("A", first, decimals="INF"), fact("B", "1", decimals="INF")], tax) == []
    equal = parsed_arcs([("1", "optional", 0), ("1.00", "prohibited", 1)])
    assert equal[0].equivalence_key == equal[1].equivalence_key
    assert CalculationConsistencyValidator._effective_summation_arcs(equal) == []


def test_total_rounding_uses_reported_zero_infinite_inferred_accuracy():
    assert _round_fact(fact("A", "0", precision="3"), v_decimal=Decimal("1")) == Decimal("1")


def test_invalid_accuracy_direct_validator_does_not_raise_or_mutate_ambient():
    values = [fact("A", "1", decimals="bad"), fact("B", "1", decimals="0")]
    with localcontext() as ctx:
        ctx.prec = 2
        ctx.traps[Inexact] = True
        before = dict(ctx.flags)
        findings = run(values)
        assert [f.rule_id for f in findings] == ["calculation:arithmetic-incomplete"]
        assert dict(ctx.flags) == before


@pytest.mark.parametrize("raw", ["NaN", "INF", "-INF"])
def test_nonfinite_inputs_do_not_escape_direct_validator(raw):
    values = [fact("A", raw, decimals="INF"), fact("B", raw, decimals="INF")]
    with localcontext() as ctx:
        before = dict(ctx.flags)
        run(values)
        assert dict(ctx.flags) == before


@pytest.mark.parametrize("exponent", [400, -400])
@pytest.mark.parametrize("inconsistent", [False, True])
def test_real_binding_extreme_precision_infers_from_reported_value(exponent, inconsistent):
    raw = f"1.23E{exponent}"
    child = f"{1.24 if inconsistent else 1.23}E{exponent}"
    values = [fact("A", raw, precision="3"), fact("B", child, precision="3")]
    findings = run(values)
    assert [f.rule_id for f in findings] == (
        ["calculation:summation-inconsistent"] if inconsistent else []
    )


def test_cancellation_retains_small_middle_contributor():
    tax = _taxonomy_with_abc_calculation()
    concepts = dict(tax.concepts)
    concepts[_q("D")] = replace(concepts[_q("C")], qname=_q("D"))
    arcs = list(tax.calculation[_ELR])
    arcs.append(replace(arcs[0], child=_q("D"), weight=Decimal("-1")))
    tax = replace(tax, concepts=concepts, calculation={_ELR: arcs})
    values = [
        fact("A", "1", decimals="INF"),
        fact("B", "1E400", decimals="INF"),
        fact("C", "1", decimals="INF"),
        fact("D", "1E400", decimals="INF"),
    ]
    assert run(values, tax) == []


def test_resource_failure_preserves_other_binding_and_ambient_flags():
    tax = _taxonomy_with_abc_calculation()
    values = [
        fact("A", "1E100001", decimals="INF"),
        fact("B", "1E100001", decimals="INF"),
        fact("C", "1", decimals="INF"),
    ]
    document = _instance_with_facts(values)
    # A second distinct unit binding must still report its actual inconsistency.
    document.units["u2"] = replace(
        document.units["u1"],
        unit_id="u2",
        measure_uri="iso4217:USD",
        simple_measure_qnames=(replace(document.units["u1"].measure_qname, local_name="USD"),),
        measure_qname=replace(document.units["u1"].measure_qname, local_name="USD"),
    )
    document.facts.extend(
        [
            replace(fact("A", "3", decimals="0"), unit_ref="u2"),
            replace(fact("B", "1", decimals="0"), unit_ref="u2"),
            replace(fact("C", "1", decimals="0"), unit_ref="u2"),
        ]
    )
    with localcontext() as ctx:
        ctx.prec = 2
        ctx.Emax = 10
        ctx.traps[Inexact] = True
        before = ctx.copy()
        result = CalculationConsistencyValidator().validate(document, tax)
        assert sorted(f.rule_id for f in result) == [
            "calculation:arithmetic-incomplete",
            "calculation:summation-inconsistent",
        ]
        assert dict(ctx.flags) == dict(before.flags)
        assert dict(ctx.traps) == dict(before.traps)


def test_already_exact_extreme_accuracy_does_not_pad_zeroes():
    assert _round_fact(fact("A", "1", decimals="1000000000")) == Decimal(1)


def test_effective_concept_accuracy_defaults_preserved():
    tax = _taxonomy_summation_a_equals_b()
    declaration = replace(tax.concepts[_q("A")], default_precision="3")
    assert _round_fact(fact("A", "1.234E400"), concept=declaration) == Decimal("1.23E400")


@pytest.mark.parametrize(
    "weight", [0.1, Decimal("0.1"), Decimal("0.123456789012345678901234567891")]
)
def test_formula_weight_selector_and_xfi_attribute_keep_decimal_compatibility(weight):
    from bde_xbrl_editor.taxonomy.models import FormulaFilterResource, QName
    from bde_xbrl_editor.validation.formula.evaluator import FormulaEvaluator
    from bde_xbrl_editor.validation.formula.xfi_functions import xfi_relationship_attribute

    tax = _taxonomy_summation_a_equals_b()
    arc = replace(tax.calculation[_ELR][0], weight=weight)
    tax = replace(tax, calculation={_ELR: [arc]})
    parent = fact("A", "1", decimals="INF")
    child = fact("B", "1", decimals="INF")
    document = _instance_with_facts([parent, child])
    resource = FormulaFilterResource(
        "r",
        "urn:filter",
        "conceptRelation",
        attributes={"axis": "child"},
        variable="parent",
        test_xpath=f"weight eq {weight}",
    )
    evaluator = FormulaEvaluator(taxonomy=tax)
    assert evaluator._matching_concept_relation_facts(
        (resource,), {"parent": [parent]}, document
    ) == [child]
    node = etree.Element("relationship", weight=str(weight))
    assert xfi_relationship_attribute(node, QName("", "weight")) == Decimal(str(weight))


def test_equivalence_boolean_numeric_normalization_remains_compatible():
    from bde_xbrl_editor.taxonomy.linkbases.calculation import _normalise_equivalence_value

    assert _normalise_equivalence_value("true") == _normalise_equivalence_value("1.00")
    assert _normalise_equivalence_value("false") == _normalise_equivalence_value("-0.00")


def test_exact_product_underflow_is_explicit_not_silent_zero():
    from bde_xbrl_editor.validation.calculation import _exact_multiply

    with pytest.raises(ArithmeticError):
        _exact_multiply(Decimal("1E-999999999999999999"), Decimal(".01"))


def test_underflow_binding_reports_incomplete_without_skipping_other_binding():
    tax = _taxonomy_summation_a_equals_b()
    arc = replace(tax.calculation[_ELR][0], weight=Decimal(".01"))
    tax = replace(tax, calculation={_ELR: [arc]})
    values = [fact("A", "0", decimals="INF"), fact("B", "1E-999999999999999999", decimals="INF")]
    document = _instance_with_facts(values)
    document.units["u2"] = replace(
        document.units["u1"],
        unit_id="u2",
        measure_uri="iso4217:USD",
        simple_measure_qnames=(replace(document.units["u1"].measure_qname, local_name="USD"),),
    )
    document.facts.extend(
        [
            replace(fact("A", "2", decimals="INF"), unit_ref="u2"),
            replace(fact("B", "1", decimals="INF"), unit_ref="u2"),
        ]
    )
    with localcontext() as ctx:
        before = ctx.copy()
        result = CalculationConsistencyValidator().validate(document, tax)
        assert sorted(f.rule_id for f in result) == [
            "calculation:arithmetic-incomplete",
            "calculation:summation-inconsistent",
        ]
        assert dict(ctx.flags) == dict(before.flags)
        report = InstanceValidator(
            tax, include_dimensional=False, include_formula=False
        ).validate_sync(document)
        assert sorted(f.rule_id for f in report.findings if f.source == "calculation") == [
            "calculation:arithmetic-incomplete",
            "calculation:summation-inconsistent",
        ]
        assert dict(ctx.flags) == dict(before.flags)
