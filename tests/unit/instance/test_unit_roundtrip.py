"""Lossless serialization of XBRL unit structures and resolved measure QNames."""

from datetime import date
from pathlib import Path

import pytest
from lxml import etree

from bde_xbrl_editor.instance.constants import ISO4217_NS, XBRLI_NS
from bde_xbrl_editor.instance.models import ReportingEntity, ReportingPeriod, XbrlInstance, XbrlUnit
from bde_xbrl_editor.instance.parser import _parse_unit
from bde_xbrl_editor.instance.serializer import InstanceSerializer
from bde_xbrl_editor.taxonomy.models import QName


def instance_with(unit):
    return XbrlInstance(
        Path("test.xsd"),
        "test.xsd",
        ReportingEntity("entity", "urn:entity"),
        ReportingPeriod("instant", instant_date=date(2025, 1, 1)),
        units={unit.unit_id: unit},
    )


@pytest.mark.parametrize(
    "body",
    [
        "<x:measure>x:pure</x:measure>",
        "<x:measure>x:shares</x:measure>",
        "<x:measure>currency:EUR</x:measure>",
        "<x:measure>m:metre</x:measure>",
        "<x:measure>m:metre</x:measure><x:measure>m:metre</x:measure>",
        "<x:measure>m:metre</x:measure><x:measure>other:second</x:measure>",
        "<x:divide><x:unitNumerator><x:measure>currency:EUR</x:measure></x:unitNumerator>"
        "<x:unitDenominator><x:measure>x:shares</x:measure></x:unitDenominator></x:divide>",
        "<x:divide><x:unitNumerator><x:measure>m:metre</x:measure><x:measure>m:metre</x:measure>"
        "</x:unitNumerator><x:unitDenominator><x:measure>other:second</x:measure>"
        "<x:measure>other:second</x:measure></x:unitDenominator></x:divide>",
    ],
)
def test_parse_serialize_reparse_preserves_unit_structure(body):
    source = etree.fromstring(
        f'<x:unit xmlns:x="{XBRLI_NS}" xmlns:currency="{ISO4217_NS}" '
        f'xmlns:m="urn:metres" xmlns:other="urn:seconds" id="u">{body}</x:unit>'
    )
    unit = _parse_unit(source)
    root = etree.fromstring(InstanceSerializer().to_xml(instance_with(unit)))
    output = root.find(f"{{{XBRLI_NS}}}unit")
    for measure in output.iter(f"{{{XBRLI_NS}}}measure"):
        assert measure.text and not measure.text.startswith("{")
        assert " " not in measure.text
        prefix = measure.text.split(":")[0]
        assert prefix in measure.nsmap
    reparsed = _parse_unit(output)
    assert reparsed.unit_form == unit.unit_form
    assert reparsed.simple_measure_qnames == unit.simple_measure_qnames
    assert reparsed.numerator_measure_qnames == unit.numerator_measure_qnames
    assert reparsed.denominator_measure_qnames == unit.denominator_measure_qnames


@pytest.mark.parametrize(
    "lexical,expected",
    [
        (f"{ISO4217_NS}:EUR", QName(ISO4217_NS, "EUR")),
        (f"{XBRLI_NS}:pure", QName(XBRLI_NS, "pure")),
        ("xbrli:shares", QName(XBRLI_NS, "shares")),
        ("iso4217:USD", QName(ISO4217_NS, "USD")),
        ("{urn:custom}item", QName("urn:custom", "item")),
    ],
)
def test_legacy_measure_uri_only_units(lexical, expected):
    unit = XbrlUnit("legacy", lexical)
    root = etree.fromstring(InstanceSerializer().to_xml(instance_with(unit)))
    output = root.find(f"{{{XBRLI_NS}}}unit")
    assert not output[0].text.startswith("{")
    assert _parse_unit(output).simple_measure_qnames == (expected,)


def test_custom_prefix_collision_does_not_change_measure_namespace():
    unit = XbrlUnit("u", "", measure_qname=QName("urn:custom", "item", prefix="xbrli"))
    root = etree.fromstring(InstanceSerializer().to_xml(instance_with(unit)))
    assert _parse_unit(root.find(f"{{{XBRLI_NS}}}unit")).measure_qname == unit.measure_qname


def test_public_parser_save_reopen_keeps_product_and_quotient_units(tmp_path):
    from tests.integration.instance.test_edit_roundtrip import (
        _make_parser,
        _make_taxonomy,
        _write_instance,
    )

    path = _write_instance(tmp_path)
    text = path.read_text()
    extra = (
        f'<x:unit xmlns:x="{XBRLI_NS}" xmlns:m="urn:metres" xmlns:s="urn:seconds" id="compound">'
        "<x:divide><x:unitNumerator><x:measure>m:metre</x:measure><x:measure>m:metre</x:measure>"
        "</x:unitNumerator><x:unitDenominator><x:measure>s:second</x:measure>"
        "</x:unitDenominator></x:divide></x:unit>"
        f'<x:unit xmlns:x="{XBRLI_NS}" xmlns:m="urn:metres" id="product">'
        "<x:measure>m:metre</x:measure><x:measure>m:metre</x:measure></x:unit>"
    )
    path.write_text(text.replace("</xbrli:xbrl>", extra + "</xbrli:xbrl>"))
    parser = _make_parser(_make_taxonomy())
    instance, _ = parser.load(path)
    saved = tmp_path / "saved.xbrl"
    InstanceSerializer().save(instance, saved)
    reopened, _ = parser.load(saved)
    for unit_id, unit in instance.units.items():
        actual = reopened.units[unit_id]
        assert actual.unit_form == unit.unit_form
        assert actual.simple_measure_qnames == unit.simple_measure_qnames
        assert actual.numerator_measure_qnames == unit.numerator_measure_qnames
        assert actual.denominator_measure_qnames == unit.denominator_measure_qnames
    assert reopened.units["compound"].denominator_measure_qnames == (
        QName("urn:seconds", "second"),
    )
    assert len(reopened.units["product"].simple_measure_qnames) == 2
