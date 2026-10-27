"""Explicit decimal presentation and editing keep domain values canonical."""

from datetime import date, datetime
from pathlib import Path
from types import SimpleNamespace

import pytest
from PySide6.QtCore import Qt
from PySide6.QtGui import QStandardItemModel
from PySide6.QtWidgets import QApplication, QLineEdit, QStyleOptionViewItem, QWidget

from bde_xbrl_editor.instance.models import (
    Fact,
    ReportingEntity,
    ReportingPeriod,
    XbrlContext,
    XbrlInstance,
)
from bde_xbrl_editor.instance.validator import XbrlTypeValidator
from bde_xbrl_editor.table_renderer.fact_formatter import FactFormatter
from bde_xbrl_editor.table_renderer.models import BodyCell, CellCoordinate
from bde_xbrl_editor.taxonomy import LoaderSettings
from bde_xbrl_editor.taxonomy.models import Concept, QName, TaxonomyMetadata, TaxonomyStructure
from bde_xbrl_editor.ui.instance_editor_adapter import InstanceEditorAdapter
from bde_xbrl_editor.ui.widgets import loader_settings_dialog as settings
from bde_xbrl_editor.ui.widgets.cell_edit_delegate import CellEditDelegate
from bde_xbrl_editor.ui.widgets.loader_settings_dialog import LoaderSettingsDialog
from bde_xbrl_editor.ui.widgets.table_body_model import TableBodyModel

Q = QName("urn:test", "Amount")
STRING = QName("urn:test", "Text")


def taxonomy():
    return TaxonomyStructure(
        TaxonomyMetadata("Test", "1", "Test", Path("tax.xsd"), datetime.now(), ("en",)),
        {
            Q: Concept(Q, QName("http://www.xbrl.org/2003/instance", "decimalItemType"), "instant"),
            STRING: Concept(
                STRING, QName("http://www.xbrl.org/2003/instance", "stringItemType"), "instant"
            ),
        },
        None,
        {},
        {},
        {},
        (),
        {},
        (),
    )


def document():
    entity = ReportingEntity("entity", "urn:entity")
    period = ReportingPeriod("instant", instant_date=date(2026, 1, 1))
    return XbrlInstance(
        Path("tax.xsd"),
        "tax.xsd",
        entity,
        period,
        contexts={"c": XbrlContext("c", entity, period)},
        facts=[Fact(Q, "c", None, "1234.5600", decimals="2")],
        _dirty=False,
    )


@pytest.mark.parametrize("separator", [".", ","])
def test_explicit_decimal_lexical_and_reversible_display(separator):
    tax = taxonomy()
    validator = XbrlTypeValidator(tax, decimal_separator=separator)
    raw = "+" + "9" * 5000 + ".0000123400"
    localized = raw.replace(".", separator)
    assert validator.validate(localized, Q) == (True, "")
    assert validator.normalise(localized, Q) == raw
    formatter = FactFormatter(tax, decimal_separator=separator)
    assert formatter.format(raw, Q, "2") == localized
    assert formatter.format("1234.5600", STRING, "0") == "1234.5600"
    for invalid in (
        "1,234.56",
        "1.234,56",
        "1_234",
        "NaN",
        "Infinity",
        "1e3",
        "１２.２",
        "--1",
        "1..2",
        "1,,2",
    ):
        assert not validator.validate(invalid, Q)[0]
        assert validator.normalise(invalid, Q) == invalid
    wrong = "12,9" if separator == "." else "12.9"
    assert not validator.validate(wrong, Q)[0]
    assert XbrlTypeValidator(tax).validate("1234.56", Q) == (True, "")


def test_settings_persist_cancel_and_preserve_other_keys(qtbot, monkeypatch, tmp_path):
    monkeypatch.setattr(settings, "_SETTINGS_FILE", tmp_path / "settings.json")
    settings._write_raw({"recent_files": ["existing"], "decimal_separator": "invalid"})
    assert settings.load_decimal_separator() == "."
    dialog = LoaderSettingsDialog(LoaderSettings())
    qtbot.addWidget(dialog)
    dialog._decimal_separator.setCurrentIndex(dialog._decimal_separator.findData(","))
    dialog.reject()
    assert settings.load_decimal_separator() == "."
    dialog._on_accept()
    assert settings.load_decimal_separator() == ","
    assert settings._read_raw()["recent_files"] == ["existing"]


@pytest.mark.parametrize("separator,submitted", [(".", "1234.56"), (",", "1234,56")])
def test_real_delegate_edit_and_paste_remain_canonical(qtbot, separator, submitted):
    tax = taxonomy()
    instance = document()
    adapter = InstanceEditorAdapter(instance)
    layout = SimpleNamespace(
        body=[[BodyCell(0, 0, CellCoordinate(concept=Q), fact_value="1234.5600")]]
    )
    delegate = CellEditDelegate(tax, adapter, layout, decimal_separator=separator)
    model = QStandardItemModel(1, 1)
    index = model.index(0, 0)
    model.setData(index, "1234.5600", Qt.ItemDataRole.UserRole)
    parent = QWidget()
    qtbot.addWidget(parent)
    widget = delegate.createEditor(parent, QStyleOptionViewItem(), index)
    assert isinstance(widget, QLineEdit)
    delegate.setEditorData(widget, index)
    assert widget.text() == "1234" + separator + "5600"
    widget.selectAll()
    clipboard = QApplication.clipboard()
    previous = clipboard.text()
    try:
        clipboard.setText(submitted)
        widget.paste()
    finally:
        clipboard.setText(previous)
    delegate.setModelData(widget, model, index)
    assert instance.facts[0].value == "1234.56"


@pytest.mark.parametrize("submitted", ["12.9", "1,234.56", "1.234,56", "NaN", "1e3"])
def test_invalid_comma_edit_preserves_clean_document(qtbot, submitted):
    instance = document()
    fact = instance.facts[0]
    delegate = CellEditDelegate(
        taxonomy(),
        InstanceEditorAdapter(instance),
        SimpleNamespace(body=[[BodyCell(0, 0, CellCoordinate(concept=Q))]]),
        decimal_separator=",",
    )
    model = QStandardItemModel(1, 1)
    widget = QLineEdit(submitted)
    qtbot.addWidget(widget)
    delegate.setModelData(widget, model, model.index(0, 0))
    assert instance.facts[0] is fact
    assert not instance.has_unsaved_changes
    assert instance.edit_history == []


def test_model_roles_keep_raw_canonical():
    tax = taxonomy()
    layout = SimpleNamespace(
        body=[
            [BodyCell(0, 0, CellCoordinate(concept=Q), fact_value="1234.5600", fact_decimals="0")]
        ],
        row_header=SimpleNamespace(leaf_count=1),
        column_header=SimpleNamespace(leaf_count=1),
    )
    model = TableBodyModel(layout)
    model.set_formatter(FactFormatter(tax, decimal_separator=","), tax)
    assert model.data(model.index(0, 0)) == "1234,5600"
    assert model.data(model.index(0, 0), Qt.ItemDataRole.UserRole) == "1234.5600"


def test_active_editor_pins_separator_and_new_editor_uses_preference(qtbot):
    instance = document()
    delegate = CellEditDelegate(
        taxonomy(),
        InstanceEditorAdapter(instance),
        SimpleNamespace(body=[[BodyCell(0, 0, CellCoordinate(concept=Q))]]),
        decimal_separator=",",
    )
    model = QStandardItemModel(1, 1)
    index = model.index(0, 0)
    parent = QWidget()
    qtbot.addWidget(parent)
    active = delegate.createEditor(parent, QStyleOptionViewItem(), index)
    active.setText("12,900")
    delegate.set_decimal_separator(".")
    assert (
        delegate.createEditor(parent, QStyleOptionViewItem(), index).property("decimal_separator")
        == "."
    )
    delegate.setModelData(active, model, index)
    assert instance.facts[0].value == "12.900"


@pytest.mark.parametrize("dirty", [False, True])
def test_live_preference_preserves_document_and_revisions(qtbot, monkeypatch, tmp_path, dirty):
    from bde_xbrl_editor.ui.main_window import MainWindow
    from bde_xbrl_editor.ui.widgets.xbrl_table_view import XbrlTableView

    monkeypatch.setattr(settings, "_SETTINGS_FILE", tmp_path / "settings.json")
    monkeypatch.setattr("bde_xbrl_editor.ui.main_window.load_loader_page_mode", lambda: "classic")
    window = MainWindow()
    qtbot.addWidget(window, before_close_func=lambda _: setattr(instance, "_dirty", False))
    instance = document()
    instance._dirty = dirty
    window._current_instance = instance
    view = XbrlTableView(window)
    view._taxonomy = taxonomy()
    view._instance = instance
    window._table_view = view
    layout = SimpleNamespace(
        body=[[BodyCell(0, 0, CellCoordinate(concept=Q), fact_value="1234.5600")]],
        row_header=SimpleNamespace(leaf_count=1),
        column_header=SimpleNamespace(leaf_count=1),
    )
    model = TableBodyModel(layout)
    view._body_view.setModel(model)
    delegate = CellEditDelegate(view._taxonomy, InstanceEditorAdapter(instance), layout)
    view._body_view.setItemDelegate(delegate)
    fact = instance.facts[0]
    revision = window._content_revision
    rules_revision = window._rules_revision

    def accept_dialog(dialog):
        dialog._decimal_separator.setCurrentIndex(dialog._decimal_separator.findData(","))
        dialog._on_accept()
        return 1

    monkeypatch.setattr(LoaderSettingsDialog, "exec", accept_dialog)
    window._on_display_settings()
    assert settings.load_decimal_separator() == ","
    assert window._current_instance is instance
    assert instance.facts[0] is fact
    assert instance.has_unsaved_changes == dirty
    assert window._content_revision == revision
    assert window._rules_revision == rules_revision
    assert model.data(model.index(0, 0)) == "1234,5600"
    assert model.data(model.index(0, 0), Qt.ItemDataRole.UserRole) == "1234.5600"
    assert delegate._decimal_separator == ","
    view.shutdown_background_tasks()


def test_comma_edit_serializes_and_reopens_with_dot(qtbot, tmp_path):
    from lxml import etree

    from bde_xbrl_editor.instance.parser import InstanceParser
    from bde_xbrl_editor.instance.serializer import InstanceSerializer

    instance = document()
    tax = taxonomy()
    delegate = CellEditDelegate(
        tax,
        InstanceEditorAdapter(instance),
        SimpleNamespace(body=[[BodyCell(0, 0, CellCoordinate(concept=Q))]]),
        decimal_separator=",",
    )
    model = QStandardItemModel(1, 1)
    widget = QLineEdit("1234,5600123400")
    qtbot.addWidget(widget)
    delegate.setModelData(widget, model, model.index(0, 0))
    instance.facts.append(Fact(STRING, "c", None, "String 1,234.56"))
    path = tmp_path / "instance.xbrl"
    InstanceSerializer().save(instance, path)
    root = etree.parse(str(path))
    assert root.find("{urn:test}Amount").text == "1234.5600123400"
    assert root.find("{urn:test}Text").text == "String 1,234.56"
    (tmp_path / "tax.xsd").write_text("<schema/>")
    loader = SimpleNamespace(load=lambda *args, **kwargs: tax)
    loaded, _ = InstanceParser(loader).load(path)
    assert next(f for f in loaded.facts if f.concept == Q).value == "1234.5600123400"
    assert not loaded.has_unsaved_changes


def test_workspace_settings_cancel_preserves_preference(qtbot, monkeypatch, tmp_path):
    from bde_xbrl_editor.ui.main_window import MainWindow

    monkeypatch.setattr(settings, "_SETTINGS_FILE", tmp_path / "settings.json")
    monkeypatch.setattr("bde_xbrl_editor.ui.main_window.load_loader_page_mode", lambda: "classic")
    settings.save_decimal_separator(",")
    window = MainWindow()
    qtbot.addWidget(window)
    assert window._decimal_separator == ","
    actions = [action.text() for action in window.menuBar().actions()]
    assert "&Settings" in actions

    def reject_dialog(dialog):
        dialog._decimal_separator.setCurrentIndex(dialog._decimal_separator.findData("."))
        dialog.reject()
        return 0

    monkeypatch.setattr(LoaderSettingsDialog, "exec", reject_dialog)
    window._on_display_settings()
    assert window._decimal_separator == ","
    assert settings.load_decimal_separator() == ","


def test_table_replacement_keeps_preference_and_raw_value(qtbot):
    from bde_xbrl_editor.table_renderer.models import ComputedTableLayout, HeaderGrid
    from bde_xbrl_editor.ui.widgets.xbrl_table_view import XbrlTableView

    view = XbrlTableView()
    qtbot.addWidget(view)
    view._taxonomy = taxonomy()
    view.set_decimal_separator(",")
    header = HeaderGrid([[]], 1, 1)
    for table_id in ("first", "second"):
        layout = ComputedTableLayout(
            table_id,
            table_id,
            header,
            header,
            [],
            0,
            [[BodyCell(0, 0, CellCoordinate(concept=Q), fact_value="1234.5600")]],
        )
        view.set_layout(layout)
        model = view._body_view.model()
        assert model.data(model.index(0, 0)) == "1234,5600"
        assert model.data(model.index(0, 0), Qt.ItemDataRole.UserRole) == "1234.5600"
        assert view._body_view.itemDelegate()._decimal_separator == ","
    view.shutdown_background_tasks()


def test_loader_settings_uses_same_persisted_selector(qtbot, monkeypatch, tmp_path):
    from bde_xbrl_editor.ui.widgets.taxonomy_loader_widget import TaxonomyLoaderWidget

    monkeypatch.setattr(settings, "_SETTINGS_FILE", tmp_path / "settings.json")
    widget = TaxonomyLoaderWidget()
    qtbot.addWidget(widget)
    changes = []
    widget.settings_changed.connect(lambda: changes.append(True))

    def accept_dialog(dialog):
        dialog._decimal_separator.setCurrentIndex(dialog._decimal_separator.findData(","))
        dialog._on_accept()
        return 1

    monkeypatch.setattr(LoaderSettingsDialog, "exec", accept_dialog)
    widget._on_settings()
    assert settings.load_decimal_separator() == ","
    assert changes == [True]
