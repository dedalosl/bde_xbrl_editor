"""Unit tests for XBRL context S-equality (instance/s_equal.py)."""

from __future__ import annotations

from datetime import date

from lxml import etree

from bde_xbrl_editor.instance.constants import XBRLI_NS
from bde_xbrl_editor.instance.models import ReportingEntity, ReportingPeriod
from bde_xbrl_editor.instance.s_equal import build_s_equal_key_from_xml_fragments


def _entity() -> ReportingEntity:
    return ReportingEntity(identifier="example.com", scheme="http://nic.net")


def _instant() -> ReportingPeriod:
    return ReportingPeriod(period_type="instant", instant_date=date(2008, 6, 30))


def test_decimal_attribute_lexical_variants_segment_302_11() -> None:
    """302.11: xsd:decimal attribute values 1 and +1.0 are S-equal (X-equal)."""
    eg = "http://xbrl.example.com"
    seg1 = etree.fromstring(
        f'<xbrli:segment xmlns:xbrli="{XBRLI_NS}" xmlns:eg="{eg}">'
        f'<eg:evil elNumero="1"/></xbrli:segment>'
    )
    seg2 = etree.fromstring(
        f'<xbrli:segment xmlns:xbrli="{XBRLI_NS}" xmlns:eg="{eg}">'
        f'<eg:evil elNumero="+1.0"/></xbrli:segment>'
    )
    e, p = _entity(), _instant()
    k1 = build_s_equal_key_from_xml_fragments(e, p, None, seg1)
    k2 = build_s_equal_key_from_xml_fragments(e, p, None, seg2)
    assert k1 == k2


def test_decimal_attribute_lexical_variants_scenario_302_12() -> None:
    """302.12: same as 302.11 but scenario container."""
    eg = "http://xbrl.example.com"
    sc1 = etree.fromstring(
        f'<xbrli:scenario xmlns:xbrli="{XBRLI_NS}" xmlns:eg="{eg}">'
        f'<eg:evil elNumero="1"/></xbrli:scenario>'
    )
    sc2 = etree.fromstring(
        f'<xbrli:scenario xmlns:xbrli="{XBRLI_NS}" xmlns:eg="{eg}">'
        f'<eg:evil elNumero="+1.0"/></xbrli:scenario>'
    )
    e, p = _entity(), _instant()
    k1 = build_s_equal_key_from_xml_fragments(e, p, sc1, None)
    k2 = build_s_equal_key_from_xml_fragments(e, p, sc2, None)
    assert k1 == k2


def test_different_decimal_values_not_s_equal() -> None:
    eg = "http://xbrl.example.com"
    seg1 = etree.fromstring(
        f'<xbrli:segment xmlns:xbrli="{XBRLI_NS}" xmlns:eg="{eg}">'
        f'<eg:evil elNumero="1"/></xbrli:segment>'
    )
    seg2 = etree.fromstring(
        f'<xbrli:segment xmlns:xbrli="{XBRLI_NS}" xmlns:eg="{eg}">'
        f'<eg:evil elNumero="2"/></xbrli:segment>'
    )
    e, p = _entity(), _instant()
    k1 = build_s_equal_key_from_xml_fragments(e, p, None, seg1)
    k2 = build_s_equal_key_from_xml_fragments(e, p, None, seg2)
    assert k1 != k2
