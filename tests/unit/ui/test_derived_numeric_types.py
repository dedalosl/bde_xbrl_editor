"""Real derived-type editors preserve lexical precision and reject invalid mutations."""

from dataclasses import replace
from types import SimpleNamespace

import pytest
from PySide6.QtGui import QStandardItemModel
from PySide6.QtWidgets import QLineEdit, QStyleOptionViewItem, QWidget

from bde_xbrl_editor.instance.models import Fact
from bde_xbrl_editor.table_renderer.models import BodyCell, CellCoordinate
from bde_xbrl_editor.taxonomy.models import QName
from bde_xbrl_editor.ui.instance_editor_adapter import InstanceEditorAdapter
from bde_xbrl_editor.ui.widgets.cell_edit_delegate import CellEditDelegate
from tests.unit.taxonomy.test_type_traits import XSD, A, concept, instance, taxonomy


def editor_fixture(qtbot, declaration, facts=()):
    document = instance(*facts)
    document._dirty = False
    adapter = InstanceEditorAdapter(document)
    layout = SimpleNamespace(body=[[BodyCell(0, 0, CellCoordinate(concept=A))]])
    delegate = CellEditDelegate(taxonomy(declaration), adapter, layout, decimal_separator=",")
    model = QStandardItemModel(1, 1)
    parent = QWidget()
    qtbot.addWidget(parent)
    widget = delegate.createEditor(parent, QStyleOptionViewItem(), model.index(0, 0))
    assert isinstance(widget, QLineEdit)
    widget._parent_keepalive = parent
    delegate._adapter_keepalive = adapter
    return document, delegate, model, widget


@pytest.mark.parametrize("submitted", ["12.9", "1.234,56", "12,bad"])
def test_derived_decimal_invalid_edit_preserves_existing_fact(qtbot, submitted):
    fact = Fact(A, "c", "u", "42.0000", decimals="2")
    document, delegate, model, widget = editor_fixture(qtbot, concept(), [fact])
    widget.setText(submitted)
    delegate.setModelData(widget, model, model.index(0, 0))
    assert document.facts == [fact]
    assert document.facts[0] is fact
    assert not document.has_unsaved_changes
    assert document.edit_history == []


def test_derived_decimal_editor_commits_exact_canonical_value(qtbot):
    fact = Fact(A, "c", "u", "42.0000", decimals="2")
    document, delegate, model, widget = editor_fixture(qtbot, concept(), [fact])
    raw = "+" + "9" * 5000 + ",0000123400"
    widget.setText(raw)
    delegate.setModelData(widget, model, model.index(0, 0))
    assert document.facts[0].value == raw.replace(",", ".")
    assert document.has_unsaved_changes


@pytest.mark.parametrize("base", ["float", "double"])
def test_new_floating_fact_has_unit_and_preserves_scientific_lexical(qtbot, base):
    declaration = concept("Floating", (QName(XSD, base),))
    document, delegate, model, widget = editor_fixture(qtbot, declaration)
    widget.setText("1.2300E+04")
    delegate.setModelData(widget, model, model.index(0, 0))
    assert document.facts[0].value == "1.2300E+04"
    assert document.facts[0].unit_ref == "u"


def test_custom_namespace_decimal_name_remains_string_editor(qtbot):
    declaration = replace(
        concept("decimalItemType", ()), data_type=QName("urn:other", "decimalItemType")
    )
    document, delegate, model, widget = editor_fixture(qtbot, declaration)
    widget.setText("1234,5600")
    delegate.setModelData(widget, model, model.index(0, 0))
    assert document.facts[0].value == "1234,5600"
    assert document.facts[0].unit_ref is None


@pytest.mark.parametrize("submitted", ["12.9", "12,9", "-1.5"])
def test_derived_integer_editor_rejects_fraction_without_mutation(qtbot, submitted):
    fact = Fact(A, "c", "u", "42", decimals="0")
    declaration = concept("Count", (QName(XSD, "int"), QName(XSD, "decimal")))
    document, delegate, model, widget = editor_fixture(qtbot, declaration, [fact])
    widget.setText(submitted)
    delegate.setModelData(widget, model, model.index(0, 0))
    assert document.facts[0] is fact
    assert fact.value == "42"
    assert not document.has_unsaved_changes
    assert document.edit_history == []


@pytest.mark.parametrize("family", ["monetary", "shares", "pure"])
@pytest.mark.parametrize("derived", [False, True])
@pytest.mark.parametrize("compatible_present", [False, True])
def test_new_standard_family_chooses_or_creates_compatible_unit(
    qtbot, family, derived, compatible_present
):
    from bde_xbrl_editor.instance.models import XbrlUnit
    from tests.unit.taxonomy.test_type_traits import XBRLI

    base = QName(XBRLI, family + "ItemType")
    declaration = concept("Derived", (base,)) if derived else concept(base.local_name, (), XBRLI)
    document, delegate, model, widget = editor_fixture(qtbot, declaration)
    measure = (
        QName("http://www.xbrl.org/2003/iso4217", "EUR")
        if family == "monetary"
        else QName(XBRLI, family)
    )
    wrong = (
        QName(XBRLI, "pure")
        if family != "pure"
        else QName("http://www.xbrl.org/2003/iso4217", "EUR")
    )
    document.units = {"wrong": XbrlUnit("wrong", str(wrong), measure_qname=wrong)}
    if compatible_present:
        document.units["compatible"] = XbrlUnit("compatible", str(measure), measure_qname=measure)
    widget.setText("1234,5600")
    delegate.setModelData(widget, model, model.index(0, 0))
    fact = document.facts[0]
    assert fact.value == "1234.5600"
    assert document.units[fact.unit_ref].measure_qname == measure
    if compatible_present:
        assert fact.unit_ref == "compatible"
        assert len(document.units) == 2


def test_existing_derived_fact_update_keeps_original_unit(qtbot):
    fact = Fact(A, "c", "u", "42.0000", decimals="2")
    document, delegate, model, widget = editor_fixture(qtbot, concept(), [fact])
    units = dict(document.units)
    widget.setText("43,0000")
    delegate.setModelData(widget, model, model.index(0, 0))
    assert document.facts[0].unit_ref == "u"
    assert document.units == units
