"""Regressions for item metadata and tuple ownership across save/reopen."""

from datetime import date
from pathlib import Path

import pytest
from lxml import etree

from bde_xbrl_editor.instance.constants import XBRLI_NS
from bde_xbrl_editor.instance.models import Fact, ReportingEntity, ReportingPeriod, XbrlInstance
from bde_xbrl_editor.instance.serializer import InstanceSerializer
from bde_xbrl_editor.taxonomy.models import QName

XSI_NIL = "{http://www.w3.org/2001/XMLSchema-instance}nil"
LANG = "{http://www.w3.org/XML/1998/namespace}lang"


def instance_with(*facts):
    return XbrlInstance(
        Path("test.xsd"),
        "test.xsd",
        ReportingEntity("entity", "urn:entity"),
        ReportingPeriod("instant", instant_date=date(2025, 1, 1)),
        facts=list(facts),
    )


@pytest.mark.parametrize("unit", [None, "EUR"])
def test_nil_items_preserve_nil(unit):
    fact = Fact(QName("urn:test", "Item"), "c", unit, "", is_nil=True)
    root = etree.fromstring(InstanceSerializer().to_xml(instance_with(fact)))
    item = root.find("{urn:test}Item")
    assert item.get(XSI_NIL) == "true"
    assert not item.text


def test_source_metadata_survives_but_current_model_attributes_win():
    fact = Fact(
        QName("urn:test", "Item"),
        "new",
        None,
        "changed",
        precision="4",
        source_element_xml=b'<t:Item xmlns:t="urn:test" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" '
        b'id="f1" xml:lang="es" contextRef="old" unitRef="EUR" decimals="2" xsi:nil="true" custom="keep"/>',
    )
    root = etree.fromstring(InstanceSerializer().to_xml(instance_with(fact)))
    item = root.find("{urn:test}Item")
    assert item.get("id") == "f1"
    assert item.get(LANG) == "es"
    assert item.get("custom") == "keep"
    assert item.get("contextRef") == "new"
    assert item.get("unitRef") is None
    assert item.get("decimals") is None
    assert item.get("precision") == "4"
    assert item.get(XSI_NIL) is None
    assert item.text == "changed"


def test_public_roundtrip_preserves_inherited_language_and_edited_nil(tmp_path):
    from tests.integration.instance.test_edit_roundtrip import (
        _make_parser,
        _make_taxonomy,
        _write_instance,
    )

    path = _write_instance(tmp_path)
    root = etree.parse(str(path)).getroot()
    root.set(LANG, "es")
    item = root.find("{http://example.com/xbrl/test}Assets")
    item.set("id", "original-id")
    item.set(XSI_NIL, "true")
    item.text = None
    path.write_bytes(etree.tostring(root))
    parser = _make_parser(_make_taxonomy())
    instance, _ = parser.load(path)
    assert instance.facts[0].is_nil
    output = tmp_path / "saved.xbrl"
    InstanceSerializer().save(instance, output)
    reopened, _ = parser.load(output)
    assert reopened.facts[0].is_nil
    saved_item = etree.fromstring(output.read_bytes()).find(item.tag)
    assert saved_item.get("id") == "original-id"
    assert saved_item.get(LANG) == "es"
    reopened.update_fact(0, "42")
    InstanceSerializer().save(reopened, output)
    edited, _ = parser.load(output)
    assert edited.facts[0].value == "42"
    assert not edited.facts[0].is_nil


def tuple_document(tmp_path):
    from dataclasses import replace

    from bde_xbrl_editor.taxonomy.models import Concept
    from tests.integration.instance.test_edit_roundtrip import (
        _make_parser,
        _make_taxonomy,
        _write_instance,
    )

    ns = "http://example.com/xbrl/test"
    taxonomy = _make_taxonomy()
    group = QName(ns, "Group")
    taxonomy = replace(
        taxonomy,
        concepts={
            **taxonomy.concepts,
            group: Concept(
                group,
                QName("http://www.w3.org/2001/XMLSchema", "anyType"),
                "duration",
                substitution_group=QName(XBRLI_NS, "tuple"),
            ),
        },
    )
    path = _write_instance(tmp_path)
    root = etree.parse(str(path)).getroot()
    original = root.find(f"{{{ns}}}Assets")
    root.remove(original)
    for index in range(2):
        outer = etree.SubElement(root, f"{{{ns}}}Group", id=f"group-{index}")
        outer.set(LANG, "es")
        inner = etree.SubElement(outer, f"{{{ns}}}Group", id=f"inner-{index}")
        for offset in range(2):
            item = etree.SubElement(inner, original.tag, attrib=dict(original.attrib))
            item.set("id", f"f-{index}-{offset}")
            item.text = str(10 * index + offset)
        unknown = etree.SubElement(inner, f"{{{ns}}}Unknown", contextRef="C1")
        unknown.text = "orphan"
    path.write_bytes(etree.tostring(root))
    return _make_parser(taxonomy), path, ns


def test_nested_repeated_tuples_and_orphan_ownership_survive(tmp_path):
    parser, path, ns = tuple_document(tmp_path)
    instance, _ = parser.load(path)
    assert len(instance.tuple_facts) == 4
    saved = tmp_path / "saved.xbrl"
    InstanceSerializer().save(instance, saved)
    reopened, _ = parser.load(saved)
    assert len(reopened.tuple_facts) == 4
    root = etree.parse(str(saved)).getroot()
    groups = root.findall(f"{{{ns}}}Group")
    assert [g.get("id") for g in groups] == ["group-0", "group-1"]
    for group in groups:
        inner = group.find(f"{{{ns}}}Group")
        assert [etree.QName(c).localname for c in inner] == ["Assets", "Assets", "Unknown"]
        assert inner[0].get(LANG) == "es"
    assert all(f.tuple_path for f in reopened.facts)
    assert all(f.tuple_path for f in reopened.orphaned_facts)


def test_tuple_edit_delete_and_append_do_not_resurrect_source_children(tmp_path):
    parser, path, ns = tuple_document(tmp_path)
    instance, _ = parser.load(path)
    owner = instance.facts[0].tuple_path
    instance.update_fact(0, "edited")
    instance.remove_fact(1)
    instance.add_fact(Fact(QName(ns, "Liabilities"), "C1", "EUR", "99", tuple_path=owner))
    saved = tmp_path / "edited.xbrl"
    InstanceSerializer().save(instance, saved)
    reopened, _ = parser.load(saved)
    root = etree.parse(str(saved)).getroot()
    inner = root.find(f"{{{ns}}}Group/{{{ns}}}Group")
    assert inner is not None
    assert [etree.QName(c).localname for c in inner] == ["Assets", "Unknown", "Liabilities"]
    assert [c.text for c in inner] == ["edited", "orphan", "99"]
    assert [f.value for f in reopened.facts] == ["edited", "99", "10", "11"]
    assert not root.findall(f"{{{ns}}}Assets")


def test_missing_tuple_owner_fails_instead_of_flattening(tmp_path):
    from bde_xbrl_editor.instance.models import InstanceSaveError

    instance = instance_with(Fact(QName("urn:test", "Item"), "c", None, "value", tuple_path=(99,)))
    with pytest.raises(InstanceSaveError, match="tuple parent"):
        InstanceSerializer().save(instance, tmp_path / "invalid.xbrl")


def test_adding_a_tuple_and_removing_an_orphan_keeps_sibling_ownership(tmp_path):
    parser, path, ns = tuple_document(tmp_path)
    instance, _ = parser.load(path)
    del instance.orphaned_facts[0]
    instance.tuple_facts.append(
        Fact(QName(ns, "Group"), "", None, "", is_tuple=True, position_path=(99,))
    )
    instance.add_fact(Fact(QName(ns, "Assets"), "C1", "EUR", "77", tuple_path=(99,)))
    saved = tmp_path / "added.xbrl"
    InstanceSerializer().save(instance, saved)
    reopened, _ = parser.load(saved)
    assert len(reopened.tuple_facts) == 5
    assert len(reopened.orphaned_facts) == 1
    groups = etree.parse(str(saved)).getroot().findall(f"{{{ns}}}Group")
    assert groups[0].find(f".//{{{ns}}}Unknown") is None
    assert groups[1].find(f".//{{{ns}}}Unknown") is not None
    assert groups[2].find(f"{{{ns}}}Assets").text == "77"


def test_local_language_override_survives_inherited_language(tmp_path):
    parser, path, ns = tuple_document(tmp_path)
    root = etree.parse(str(path)).getroot()
    item = root.find(f"{{{ns}}}Group/{{{ns}}}Group/{{{ns}}}Assets")
    item.set(LANG, "")
    path.write_bytes(etree.tostring(root))
    instance, _ = parser.load(path)
    output = etree.fromstring(InstanceSerializer().to_xml(instance))
    item = output.find(f"{{{ns}}}Group/{{{ns}}}Group/{{{ns}}}Assets")
    assert item.get(LANG) == ""


def test_structured_item_scalar_edit_cannot_reuse_old_children(tmp_path):
    from bde_xbrl_editor.instance.models import InstanceSaveError

    fact = Fact(
        QName("urn:test", "Item"),
        "c",
        None,
        "changed",
        source_element_xml=b'<t:Item xmlns:t="urn:test" contextRef="c"><t:Part>old</t:Part></t:Item>',
    )
    with pytest.raises(InstanceSaveError, match="structured item"):
        InstanceSerializer().save(instance_with(fact), tmp_path / "invalid.xbrl")


def test_nil_output_does_not_carry_numeric_accuracy():
    fact = Fact(QName("urn:test", "Item"), "c", "EUR", "", decimals="2", is_nil=True)
    item = etree.fromstring(InstanceSerializer().to_xml(instance_with(fact))).find("{urn:test}Item")
    assert item.get(XSI_NIL) == "true"
    assert item.get("decimals") is None
    assert item.get("precision") is None
