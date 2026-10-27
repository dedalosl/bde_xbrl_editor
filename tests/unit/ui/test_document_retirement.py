"""Retired document owners must release data and reject delayed notifications."""

import gc
import weakref
from dataclasses import replace
from datetime import datetime
from threading import Event, Thread

import pytest
from PySide6.QtCore import QCoreApplication, QEvent, Qt
from PySide6.QtGui import QStandardItemModel
from PySide6.QtWidgets import QComboBox, QLineEdit, QMessageBox
from shiboken6 import isValid
from test_main_window_loader_flow import _instance, _taxonomy

from bde_xbrl_editor.instance.models import Fact, XbrlContext
from bde_xbrl_editor.table_renderer.models import BodyCell, CellCoordinate
from bde_xbrl_editor.taxonomy.models import Concept, QName
from bde_xbrl_editor.ui.instance_editor_adapter import InstanceEditorAdapter
from bde_xbrl_editor.ui.main_window import MainWindow, SaveResult
from bde_xbrl_editor.ui.validation_lifecycle import validation_supervisor
from bde_xbrl_editor.ui.widgets.cell_edit_delegate import CellEditDelegate
from bde_xbrl_editor.ui.widgets.table_body_model import FACT_OPTIONS_ROLE
from bde_xbrl_editor.ui.widgets.xbrl_table_view import _empty_layout
from bde_xbrl_editor.validation.models import ValidationReport


@pytest.fixture
def window(qtbot, monkeypatch, tmp_path, qapp):
    monkeypatch.setattr("bde_xbrl_editor.ui.main_window.load_loader_page_mode", lambda: "classic")
    monkeypatch.setattr(
        "bde_xbrl_editor.ui.widgets.loader_settings_dialog._SETTINGS_FILE",
        tmp_path / "settings.json",
    )
    monkeypatch.setattr(QMessageBox, "critical", lambda *args: None)
    policy = qapp.quitOnLastWindowClosed()
    qapp.setQuitOnLastWindowClosed(False)
    result = MainWindow()
    result._current_taxonomy = _taxonomy()

    def clean(widget):
        if widget._current_instance is not None:
            widget._current_instance._dirty = False

    qtbot.addWidget(result, before_close_func=clean)
    yield result
    if isValid(result):
        clean(result)
    qapp.setQuitOnLastWindowClosed(policy)


def flush(qapp):
    QCoreApplication.sendPostedEvents(None, QEvent.Type.DeferredDelete)
    qapp.processEvents()
    QCoreApplication.sendPostedEvents(None, QEvent.Type.DeferredDelete)
    gc.collect()


def attach(window, label="document"):
    instance = _instance()
    instance.contexts["ctx"] = XbrlContext("ctx", instance.entity, instance.period)
    instance.facts.extend(
        Fact(QName("urn:lifetime", f"amount{index}"), "ctx", None, str(index))
        for index in range(200)
    )
    instance._dirty = False
    if window._current_taxonomy is None:
        window._current_taxonomy = _taxonomy()
    window._load_instance(instance)
    window._table_view.refresh_instance(instance)
    window._table_view._install_layout(replace(_empty_layout(), table_id=label))
    return weakref.ref(instance)


def retire(window, route):
    if route == "loader":
        window._show_loader_widget()
    elif route == "replace":
        attach(window, "replacement")
    elif route == "instance":
        window._on_close_instance()
    elif route == "taxonomy":
        window._on_close_taxonomy()
    else:
        assert window.close()


@pytest.mark.parametrize("route", ["loader", "replace", "instance", "taxonomy", "window"])
def test_repeated_retirement_collects_originals_and_bounds_adapters(window, qapp, route):
    originals = []
    for index in range(4):
        originals.append(attach(window, f"document{index}"))
        retire(window, route)
        flush(qapp)
        assert all(reference() is None for reference in originals)
        expected = 1 if route == "replace" else 0
        assert len(window.findChildren(InstanceEditorAdapter)) == expected
        if expected:
            assert isValid(window._editor)
            assert len(window._editor.instance.facts) == 200
        else:
            assert window._editor is None
            assert window._current_instance is None


@pytest.mark.parametrize("route", ["loader", "replace", "instance", "taxonomy", "window"])
def test_retired_consumers_release_document_and_editor_before_delete(window, qapp, route):
    original = attach(window)
    view, sidebar = window._table_view, window._sidebar
    delegate = view._body_view.itemDelegate()
    editor = weakref.ref(window._editor)
    retire(window, route)
    assert view._instance is None
    assert view._editor is None
    assert delegate._editor is None
    assert sidebar._instance_panel._instance is None
    assert sidebar._instance_panel._editor is None
    flush(qapp)
    assert original() is None
    assert editor() is None or not isValid(editor())


def test_retirement_detaches_superseded_delegates_as_well_as_active_one(window, qapp):
    original = attach(window)
    view = window._table_view
    view._install_layout(replace(_empty_layout(), table_id="second layout"))
    view._install_layout(replace(_empty_layout(), table_id="third layout"))
    delegates = view._body_view.findChildren(CellEditDelegate)
    assert sum(delegate._editor is window._editor for delegate in delegates) >= 3
    window._on_close_instance()
    assert all(delegate._editor is None for delegate in delegates)
    flush(qapp)
    assert original() is None


def test_queued_old_notifications_do_not_change_new_document(window, qapp):
    attach(window, "old")
    old_editor, old_view = window._editor, window._table_view
    old_layout = old_view._layout

    def emit():
        old_editor.changes_made.emit()
        old_editor.filing_indicators_changed.emit()
        old_view.instance_changed.emit()
        old_view.layout_ready.emit(old_layout)

    thread = Thread(target=emit)
    thread.start()
    thread.join(timeout=2)
    assert not thread.is_alive()
    attach(window, "new")
    window.setWindowModified(False)
    revision = window._content_revision
    new_editor = window._editor
    flush(qapp)
    assert window._content_revision == revision
    assert not window.isWindowModified()
    assert window._editor is new_editor
    assert window._table_view._body_view.itemDelegate()._editor is new_editor
    assert window._table_view._body_view.itemDelegate()._table_layout.table_id == "new"


def test_deferred_old_refresh_never_rebinds_new_document_to_retired_view(window, monkeypatch, qapp):
    attach(window, "old")
    old_view = window._table_view
    calls = []
    monkeypatch.setattr(old_view, "refresh_instance", lambda instance: calls.append(instance))
    window._editor.update_fact(0, "111")
    window._current_instance._dirty = False
    attach(window, "new")
    # Process pending callbacks before deferred deletion to expose the race.
    qapp.processEvents()
    assert calls == []
    flush(qapp)


def test_active_editor_edit_and_filing_notifications_remain_functional(window, qapp):
    original = attach(window)
    editor = window._editor
    revision = window._content_revision
    editor.update_fact(0, "10.25")
    editor.set_filing_indicator("T1", True, context_ref="ctx")
    assert editor.instance is original()
    assert editor.instance.facts[0].value == "10.25"
    assert editor.instance.filing_indicators[0].template_id == "T1"
    assert window._content_revision == revision + 2
    assert window.isWindowModified()
    flush(qapp)
    assert isValid(editor)
    assert len(window.findChildren(InstanceEditorAdapter)) == 1


@pytest.mark.parametrize("outcome", ["cancel", "save_cancel", "save_error"])
@pytest.mark.parametrize("route", ["instance", "taxonomy", "window", "loader"])
def test_veto_keeps_active_document_and_adapter(window, monkeypatch, qapp, route, outcome):
    original = attach(window)
    editor = window._editor
    editor.instance._dirty = True
    monkeypatch.setattr(
        QMessageBox,
        "question",
        lambda *args: (
            QMessageBox.StandardButton.Cancel
            if outcome == "cancel"
            else QMessageBox.StandardButton.Save
        ),
    )
    monkeypatch.setattr(
        window,
        "_on_save",
        lambda: SaveResult.CANCELLED if outcome == "save_cancel" else SaveResult.ERROR,
    )
    if route == "loader":
        window._show_loader()
    elif route == "window":
        assert not window.close()
    else:
        retire(window, route)
    flush(qapp)
    assert window._current_instance is original()
    assert window._editor is editor and isValid(editor)
    assert len(window.findChildren(InstanceEditorAdapter)) == 1


@pytest.mark.parametrize("choice", ["Save", "Discard"])
@pytest.mark.parametrize("route", ["instance", "window"])
def test_authorized_dirty_close_releases_original_without_clearing_core(
    window, monkeypatch, qapp, tmp_path, route, choice
):
    original = attach(window)
    editor = weakref.ref(window._editor)
    window._current_instance._dirty = True
    monkeypatch.setattr(
        QMessageBox, "question", lambda *args: getattr(QMessageBox.StandardButton, choice)
    )

    def save():
        window._editor.mark_saved(tmp_path / "saved.xbrl")
        return SaveResult.SUCCESS

    monkeypatch.setattr(window, "_on_save", save)
    retire(window, route)
    assert window._current_instance is None and window._editor is None
    # Retirement releases ownership; it does not clear domain data as a shortcut.
    assert len(original().facts) == 200
    assert len(original().contexts) == 1
    assert original().facts[0].value == "0"
    flush(qapp)
    assert original() is None
    assert editor() is None or not isValid(editor())
    assert len(window.findChildren(InstanceEditorAdapter)) == 0


@pytest.mark.parametrize("taxonomy_changed", [False, True])
def test_open_failure_preserves_only_contractually_active_document(window, qapp, taxonomy_changed):
    original = attach(window)
    editor = weakref.ref(window._editor)
    if taxonomy_changed:
        window._on_taxonomy_loaded(_taxonomy())
    window._on_open_instance_error("parse failed")
    flush(qapp)
    if taxonomy_changed:
        assert original() is None
        assert len(window.findChildren(InstanceEditorAdapter)) == 0
    else:
        assert window._current_instance is original()
        assert window._editor is editor() and isValid(editor())
        assert len(window.findChildren(InstanceEditorAdapter)) == 1


def test_closed_original_collects_while_independent_validation_snapshot_runs(
    window, monkeypatch, qtbot, qapp
):
    original = attach(window)
    entered, release = Event(), Event()
    snapshot = []

    def validate(self, instance):
        snapshot.append(weakref.ref(instance))
        entered.set()
        assert release.wait(4)
        return ValidationReport("i.xbrl", "Test", "1", datetime(2025, 1, 1), (), True)

    monkeypatch.setattr(
        "bde_xbrl_editor.validation.orchestrator.InstanceValidator.validate_sync", validate
    )
    monkeypatch.setattr(window, "_prompt_formula_general_variable_values", lambda: {})
    window._trigger_validation()
    try:
        qtbot.waitUntil(entered.is_set)
        assert snapshot[0]() is not original()
        window._on_close_instance()
        flush(qapp)
        assert original() is None
        assert snapshot[0]() is not None
        assert len(snapshot[0]().facts) == 200
        assert len(validation_supervisor().runs) == 1
    finally:
        release.set()
        qtbot.waitUntil(lambda: not validation_supervisor().runs, timeout=5000)


@pytest.mark.parametrize("kind", ["plain", "enum", "fact_options"])
@pytest.mark.parametrize("retired", [False, True])
def test_superseded_delegate_commit_requires_active_editor(window, qtbot, kind, retired):
    attach(window)
    instance, adapter, view = window._current_instance, window._editor, window._table_view
    concept = QName("urn:commit", "Value")
    taxonomy = replace(
        window._current_taxonomy,
        concepts={
            concept: Concept(
                concept, QName("http://www.xbrl.org/2003/instance", "stringItemType"), "instant"
            )
        },
    )
    instance.facts.append(Fact(concept, "ctx", None, "before"))
    layout = replace(_empty_layout(), body=[[BodyCell(0, 0, CellCoordinate(concept=concept))]])
    delegate = CellEditDelegate(taxonomy, adapter, layout, view._body_view)
    view._body_view.setItemDelegate(delegate)
    view._install_layout(replace(_empty_layout(), table_id="replacement layout"))
    assert view._body_view.itemDelegate() is not delegate
    delegate.set_table_layout(layout)

    class CommitModel(QStandardItemModel):
        def data(self, index, role=Qt.ItemDataRole.DisplayRole):
            if role == FACT_OPTIONS_ROLE and kind == "fact_options":
                return ("before", "after")
            return super().data(index, role)

    model = CommitModel(1, 1)
    index = model.index(0, 0)
    model.setData(index, "unchanged", Qt.ItemDataRole.EditRole)
    if kind == "plain":
        widget = QLineEdit("after")
    else:
        widget = QComboBox()
        widget.addItem("after", "after")
    qtbot.addWidget(widget)
    changes = []
    adapter.changes_made.connect(lambda: changes.append(True))
    before = list(instance.facts)
    revision = window._content_revision
    if retired:
        view.set_editor(None)
        assert delegate._editor is None
    delegate.setModelData(widget, model, index)
    assert model.data(index, Qt.ItemDataRole.EditRole) == "unchanged"
    if retired:
        assert instance.facts == before
        assert instance.edit_history == []
        assert not instance.has_unsaved_changes
        assert changes == []
        assert window._content_revision == revision
    else:
        assert instance.facts[-1].value == "after"
        assert changes == [True]
        assert window._content_revision == revision + 1
    instance._dirty = False
