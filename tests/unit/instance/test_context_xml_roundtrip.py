"""Regression coverage for editable, lossless context content."""

from pathlib import Path

import pytest
from lxml import etree

from bde_xbrl_editor.instance.constants import XBRLDI_NS, XBRLI_NS
from bde_xbrl_editor.instance.models import XbrlInstance
from bde_xbrl_editor.instance.parser import _parse_context
from bde_xbrl_editor.instance.serializer import InstanceSerializer
from bde_xbrl_editor.taxonomy.models import QName

D = QName("urn:test", "Axis")
T = QName("urn:test", "Typed")


def source_context_element():
    return etree.fromstring(f'''<x:context xmlns:x="{XBRLI_NS}"
      xmlns:di="{XBRLDI_NS}" xmlns:d="urn:test" id="c">
      <x:entity><x:identifier scheme="urn:entity">entity</x:identifier>
      <x:segment><di:explicitMember dimension="d:Axis">d:Old</di:explicitMember></x:segment>
      </x:entity><x:period><x:instant>2025-01-01</x:instant></x:period>
      <x:scenario><d:Other flag="yes">  keep  </d:Other>
      <di:typedMember dimension="d:Typed"><d:Domain flag="x"><d:Nested>value</d:Nested></d:Domain></di:typedMember>
      </x:scenario></x:context>''')


def context():
    return _parse_context(source_context_element())


def serialize(ctx):
    instance = XbrlInstance(
        Path("test.xsd"), "test.xsd", ctx.entity, ctx.period, contexts={ctx.context_id: ctx}
    )
    root = etree.fromstring(InstanceSerializer().to_xml(instance))
    return root.find(f"{{{XBRLI_NS}}}context")


def test_segment_parent_roundtrip():
    ctx = context()
    output = serialize(ctx)
    assert output.find(f"{{{XBRLI_NS}}}segment") is None
    assert _parse_context(output).dimensions[D] == ctx.dimensions[D]


def test_nested_typed_and_non_dimensional_content_survive():
    output = serialize(context())
    assert output.find(".//{urn:test}Nested").text == "value"
    assert output.find(".//{urn:test}Domain").get("flag") == "x"
    assert output.find(".//{urn:test}Other").text == "  keep  "


def test_edit_and_delete_dimensions_do_not_resurrect_source():
    ctx = context()
    ctx.dimensions[D] = QName("urn:test", "New")
    ctx.typed_dimensions.clear()
    del ctx.dimensions[T]
    output = serialize(ctx)
    reparsed = _parse_context(output)
    assert reparsed.dimensions[D] == QName("urn:test", "New")
    assert T not in reparsed.dimensions
    assert output.find(".//{urn:test}Other") is not None


def test_complex_scalar_edit_is_rejected_without_mutating_source():
    ctx = context()
    original = ctx.scenario_xml
    ctx.typed_dimensions[T] = "replacement"
    with pytest.raises(ValueError, match="complex typed"):
        serialize(ctx)
    assert ctx.scenario_xml == original


def test_ui_context_clone_preserves_source_content_and_location():
    from bde_xbrl_editor.ui.widgets.xbrl_table_view import _ensure_context_ref_for_dimensions

    ctx = context()
    instance = XbrlInstance(
        Path("test.xsd"), "test.xsd", ctx.entity, ctx.period, contexts={"c": ctx}
    )
    ref = _ensure_context_ref_for_dimensions(
        instance,
        dimensions={D: QName("urn:test", "New")},
        typed_dimensions=ctx.typed_dimensions,
        typed_dimension_elements=ctx.typed_dimension_elements,
        source_context=ctx,
    )
    output = serialize(instance.contexts[ref])
    assert output.find(".//{urn:test}Nested") is not None
    assert output.find(".//{urn:test}Other") is not None
    assert _parse_context(output).dim_containers[D] == "segment"


def test_preserve_qname_content_with_conflicting_source_prefixes():
    ctx = context()
    ctx.scenario_xml = ctx.scenario_xml.replace(
        b'<d:Other flag="yes">  keep  </d:Other>',
        b'<z:Other xmlns:z="urn:other" xmlns:alias="urn:test">alias:Member</z:Other>',
    )
    output = serialize(ctx)
    node = output.find(".//{urn:other}Other")
    assert node.text == "alias:Member"
    assert node.nsmap.get("alias") == "urn:test"


def test_context_equality_changes_with_edit():
    from bde_xbrl_editor.instance.s_equal import context_s_equal_key

    ctx = context()
    before = context_s_equal_key(ctx)
    ctx.dimensions[D] = QName("urn:test", "New")
    assert context_s_equal_key(ctx) != before
    assert context_s_equal_key(ctx) == context_s_equal_key(_parse_context(serialize(ctx)))


def test_non_dimensional_only_container_survives():
    ctx = context()
    ctx.dimensions.clear()
    ctx.typed_dimensions.clear()
    output = serialize(ctx)
    assert output.find(".//{urn:test}Other").text == "  keep  "
    assert not output.findall(f".//{{{XBRLDI_NS}}}typedMember")


def test_typed_nested_qname_alias_survives_reconciliation():
    ctx = context()
    original = ctx.typed_dimension_xml[T].replace(
        b"<d:Nested>value</d:Nested>",
        b'<d:Nested xmlns:alias="urn:test">alias:Member</d:Nested>',
    )
    ctx.typed_dimension_xml[T] = original
    ctx.typed_dimensions[T] = "alias:Member"
    output = serialize(ctx)
    node = output.find(".//{urn:test}Nested")
    assert node.nsmap.get("alias") == "urn:test"


@pytest.mark.parametrize("aspect_row,reject_complex", [(True, False), (False, False), (True, True)])
def test_actual_open_key_handler_keeps_unedited_context_xml(
    monkeypatch, aspect_row, reject_complex
):
    from types import SimpleNamespace
    from unittest.mock import Mock

    from bde_xbrl_editor.instance.models import Fact
    from bde_xbrl_editor.ui.widgets import xbrl_table_view as view

    ctx = context()
    instance = XbrlInstance(
        Path("test.xsd"),
        "test.xsd",
        ctx.entity,
        ctx.period,
        contexts={"c": ctx},
        facts=[Fact(QName("urn:test", "Amount"), "c", None, "10")],
    )
    key = SimpleNamespace(
        cell_kind="open-key",
        open_key_signature=("aspect-row", 0) if aspect_row else ("open", "row"),
        open_key_dimension=T if reject_complex else D,
        open_key_member=ctx.dimensions[D],
        open_key_options=() if reject_complex else (QName("urn:test", "New"),),
    )
    fact_cell = SimpleNamespace(
        cell_kind="fact",
        coordinate=SimpleNamespace(
            concept=instance.facts[0].concept,
            explicit_dimensions={D: ctx.dimensions[D]},
            typed_dimensions=dict(ctx.typed_dimensions),
            typed_dimension_elements=dict(ctx.typed_dimension_elements),
        ),
    )
    widget = SimpleNamespace(
        _layout=SimpleNamespace(body=[[key, fact_cell]], table_extended_link_role=""),
        _table=SimpleNamespace(table_id="table"),
        _taxonomy=object(),
        _instance=instance,
        _editor=None,
        _open_aspect_rows_by_table={},
        _open_row_members_by_table={},
        set_table=Mock(),
        instance_changed=Mock(),
    )
    monkeypatch.setattr(view, "_find_fact_indexes", lambda *args, **kwargs: [0])
    if reject_complex:
        warning = Mock()
        monkeypatch.setattr(view.QMessageBox, "warning", warning)
        assert not view.XbrlTableView._handle_open_key_edit(widget, 0, 0, "replacement")
        assert instance.facts[0].context_ref == "c"
        assert len(instance.contexts) == 1
        assert "complex typed" in warning.call_args.args[2]
        widget.set_table.assert_not_called()
        widget.instance_changed.emit.assert_not_called()
        return
    assert view.XbrlTableView._handle_open_key_edit(widget, 0, 0, "{urn:test}New")
    assert widget.instance_changed.emit.call_count == 2  # Context creation and fact reassignment.
    output = serialize(instance.contexts[instance.facts[0].context_ref])
    assert output.find(".//{urn:test}Other") is not None
    assert output.find(".//{urn:test}Nested").text == "value"
    assert _parse_context(output).dim_containers[D] == "segment"
    assert _parse_context(output).dimensions[D] == QName("urn:test", "New")


def test_scalar_typed_edit_preserves_attributes():
    ctx = context()
    ctx.typed_dimension_xml[T] = ctx.typed_dimension_xml[T].replace(
        b"<d:Nested>value</d:Nested>", b"value"
    )
    ctx.typed_dimensions[T] = "edited"
    output = serialize(ctx)
    node = output.find(".//{urn:test}Domain")
    assert node.text == "edited"
    assert node.get("flag") == "x"


@pytest.mark.parametrize("destination", ["segment", "scenario"])
def test_both_dimension_kinds_can_move_between_containers(destination):
    ctx = context()
    ctx.dim_containers[D] = destination
    ctx.dim_containers[T] = destination
    output = serialize(ctx)
    reparsed = _parse_context(output)
    assert reparsed.dim_containers == {D: destination, T: destination}
    assert reparsed.typed_dimensions[T] == "value"
    assert output.find(".//{urn:test}Nested") is not None


def test_save_unrepresentable_edit_reports_save_error_without_writing(tmp_path):
    from bde_xbrl_editor.instance.models import InstanceSaveError

    ctx = context()
    ctx.typed_dimensions[T] = "replacement"
    instance = XbrlInstance(
        Path("test.xsd"), "test.xsd", ctx.entity, ctx.period, contexts={"c": ctx}
    )
    target = tmp_path / "report.xbrl"
    target.write_bytes(b"previous document")
    with pytest.raises(InstanceSaveError, match="complex typed"):
        InstanceSerializer().save(instance, target)
    assert target.read_bytes() == b"previous document"
    assert instance.has_unsaved_changes


def test_typed_element_rename_preserves_complex_xml():
    ctx = context()
    ctx.typed_dimension_elements[T] = QName("urn:new", "Domain", prefix="new")
    output = serialize(ctx)
    domain = output.find(".//{urn:new}Domain")
    assert domain.get("flag") == "x"
    assert domain.find("{urn:test}Nested").text == "value"


def test_public_parser_save_reopen_preserves_context_xml(tmp_path):
    from tests.integration.instance.test_edit_roundtrip import (
        _make_parser,
        _make_taxonomy,
        _write_instance,
    )

    path = _write_instance(tmp_path)
    root = etree.parse(str(path)).getroot()
    old = root.find(f"{{{XBRLI_NS}}}context")
    replacement = source_context_element()
    replacement.set("id", old.get("id"))
    root.replace(old, replacement)
    path.write_bytes(etree.tostring(root))
    parser = _make_parser(_make_taxonomy())
    instance, _ = parser.load(path)
    ctx = next(iter(instance.contexts.values()))
    ctx.dimensions[D] = QName("urn:test", "New")
    output = tmp_path / "saved.xbrl"
    InstanceSerializer().save(instance, output)
    reopened, _ = parser.load(output)
    saved = next(iter(reopened.contexts.values()))
    assert saved.dimensions[D] == QName("urn:test", "New")
    assert saved.dim_containers[D] == "segment"
    assert saved.typed_dimensions[T] == "value"
    raw = etree.fromstring(saved.scenario_xml)
    assert raw.find(".//{urn:test}Nested").text == "value"
    assert raw.find("{urn:test}Other").text == "  keep  "


def test_deleting_last_dimension_omits_empty_segment():
    ctx = context()
    del ctx.dimensions[D]
    output = serialize(ctx)
    assert output.find(f"{{{XBRLI_NS}}}entity/{{{XBRLI_NS}}}segment") is None
