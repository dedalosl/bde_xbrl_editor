"""Regression coverage for destructive document transitions and save outcomes."""

from datetime import date
from pathlib import Path
from unittest.mock import Mock

import pytest
from PySide6.QtGui import QCloseEvent
from PySide6.QtWidgets import QFileDialog, QMessageBox

from bde_xbrl_editor.instance.models import (
    InstanceSaveError,
    ReportingEntity,
    ReportingPeriod,
    XbrlInstance,
)
from bde_xbrl_editor.instance.serializer import InstanceSerializer
from bde_xbrl_editor.ui.instance_editor_adapter import InstanceEditorAdapter
from bde_xbrl_editor.ui.main_window import MainWindow


@pytest.fixture
def document_window(qtbot, monkeypatch):
    monkeypatch.setattr("bde_xbrl_editor.ui.main_window.load_loader_page_mode", lambda: "classic")
    window = MainWindow()
    qtbot.addWidget(
        window,
        before_close_func=lambda window: (
            setattr(window._current_instance, "_dirty", False)
            if window._current_instance is not None
            else None
        ),
    )
    instance = XbrlInstance(
        taxonomy_entry_point=Path("tax.xsd"),
        schema_ref_href="tax.xsd",
        entity=ReportingEntity(identifier="ENTITY", scheme="urn:entity"),
        period=ReportingPeriod(period_type="instant", instant_date=date(2025, 12, 31)),
    )
    window._current_instance = instance
    window._editor = InstanceEditorAdapter(instance, parent=window)
    window._editor.changes_made.connect(window._on_changes_made)
    window._editor.filing_indicators_changed.connect(window._on_filing_indicators_changed)
    yield window
    instance._dirty = False


def configure_save(monkeypatch, window, tmp_path, outcome):
    target = tmp_path / "saved.xbrl"
    monkeypatch.setattr(QFileDialog, "getSaveFileName", lambda *args: (str(target), ""))
    monkeypatch.setattr(QMessageBox, "critical", Mock())
    if outcome == "dialog_cancel":
        monkeypatch.setattr(QFileDialog, "getSaveFileName", lambda *args: ("", ""))
    elif outcome == "bde_cancel":
        monkeypatch.setattr(
            "bde_xbrl_editor.instance.constants.is_bde_schema_ref", lambda href: True
        )
    elif outcome == "error":
        monkeypatch.setattr(
            InstanceSerializer,
            "save",
            Mock(side_effect=InstanceSaveError(str(target), "write failed")),
        )
    monkeypatch.setattr(
        QMessageBox,
        "question",
        lambda parent, title, *args: (
            QMessageBox.StandardButton.Cancel
            if title == "Check Filing Indicators"
            else QMessageBox.StandardButton.Save
        ),
    )
    return target


@pytest.mark.parametrize(
    "outcome,expected",
    [
        ("success", "SUCCESS"),
        ("dialog_cancel", "CANCELLED"),
        ("bde_cancel", "CANCELLED"),
        ("error", "ERROR"),
    ],
)
def test_save_has_explicit_outcome(document_window, monkeypatch, tmp_path, outcome, expected):
    target = configure_save(monkeypatch, document_window, tmp_path, outcome)
    result = document_window._on_save()
    assert result.name == expected
    assert document_window._current_instance.has_unsaved_changes == (outcome != "success")
    assert target.exists() == (outcome == "success")


@pytest.mark.parametrize("outcome", ["success", "dialog_cancel", "bde_cancel", "error"])
@pytest.mark.parametrize("transition", ["close", "guard"])
def test_save_result_controls_transition(
    document_window, monkeypatch, tmp_path, outcome, transition
):
    window = document_window
    instance, editor = window._current_instance, window._editor
    configure_save(monkeypatch, window, tmp_path, outcome)
    shutdown = Mock()
    monkeypatch.setattr(window, "_shutdown_background_tasks", shutdown)
    if transition == "close":
        event = QCloseEvent()
        window.closeEvent(event)
        allowed = event.isAccepted()
        assert shutdown.called == (outcome == "success")
    else:
        allowed = window._check_unsaved_changes()
    assert allowed == (outcome == "success")
    if transition == "close" and allowed:
        assert window._current_instance is None
        assert window._editor is None
    else:
        assert window._current_instance is instance
        assert window._editor is editor
    assert instance.has_unsaved_changes == (outcome != "success")


@pytest.mark.parametrize("dirty", [False, True])
@pytest.mark.parametrize("choice", ["Save", "Discard", "Cancel"])
@pytest.mark.parametrize(
    "transition", ["reload", "new", "open", "taxonomy", "close_instance", "close_taxonomy"]
)
def test_destructive_transition_matrix(
    document_window, monkeypatch, tmp_path, dirty, choice, transition
):
    from types import SimpleNamespace

    from PySide6.QtWidgets import QDialog

    window = document_window
    instance = window._current_instance
    instance._dirty = dirty
    window._current_taxonomy = SimpleNamespace(
        metadata=SimpleNamespace(entry_point_path=Path("tax.xsd"), name="Test", version="1.0")
    )
    configure_save(monkeypatch, window, tmp_path, "success")
    question = Mock(return_value=getattr(QMessageBox.StandardButton, choice))
    monkeypatch.setattr(QMessageBox, "question", question)
    loader = Mock()
    replace = Mock()
    monkeypatch.setattr(window, "_show_loader_widget", loader)
    monkeypatch.setattr(window, "_load_instance", replace)
    monkeypatch.setattr(window, "_begin_instance_open", replace)
    monkeypatch.setattr(QFileDialog, "getOpenFileName", lambda *args: ("other.xbrl", ""))
    monkeypatch.setattr(window, "_clear_browser_view_refs", Mock())
    monkeypatch.setattr(window, "_setup_browser_layout", Mock())
    monkeypatch.setattr(window, "_start_formula_hydration_if_needed", Mock())
    monkeypatch.setattr(window._loader_widget, "_on_load", Mock())
    wizard = SimpleNamespace(exec=lambda: QDialog.DialogCode.Accepted, created_instance=object())
    monkeypatch.setattr(
        "bde_xbrl_editor.ui.widgets.instance_creation_wizard.wizard.InstanceCreationWizard",
        lambda **kwargs: wizard,
    )
    action = {
        "reload": window._on_reload,
        "new": window._on_new_instance,
        "open": window._on_open_instance,
        "taxonomy": window._show_loader,
        "close_instance": window._on_close_instance,
        "close_taxonomy": window._on_close_taxonomy,
    }[transition]
    action()
    allowed = not dirty or choice != "Cancel"
    if transition in {"close_instance", "close_taxonomy"}:
        assert (window._current_instance is None) == allowed
    else:
        assert (loader.called or replace.called) == allowed
    assert question.call_count == int(dirty)


@pytest.mark.parametrize(
    "transition", ["reload", "new", "open", "taxonomy", "close_instance", "close_taxonomy"]
)
@pytest.mark.parametrize("outcome", ["dialog_cancel", "bde_cancel", "error"])
def test_failed_save_preserves_document_on_transitions(
    document_window, monkeypatch, tmp_path, transition, outcome
):
    from types import SimpleNamespace

    from PySide6.QtWidgets import QDialog

    window = document_window
    instance, editor = window._current_instance, window._editor
    window._current_taxonomy = SimpleNamespace(
        metadata=SimpleNamespace(entry_point_path=Path("tax.xsd"), name="Test", version="1.0")
    )
    configure_save(monkeypatch, window, tmp_path, outcome)
    replace = Mock()
    monkeypatch.setattr(window, "_show_loader_widget", replace)
    monkeypatch.setattr(window, "_load_instance", replace)
    monkeypatch.setattr(window, "_begin_instance_open", replace)
    monkeypatch.setattr(window._loader_widget, "_on_load", Mock())
    monkeypatch.setattr(QFileDialog, "getOpenFileName", lambda *args: ("other.xbrl", ""))
    wizard = SimpleNamespace(exec=lambda: QDialog.DialogCode.Accepted, created_instance=object())
    monkeypatch.setattr(
        "bde_xbrl_editor.ui.widgets.instance_creation_wizard.wizard.InstanceCreationWizard",
        lambda **kwargs: wizard,
    )
    getattr(
        window,
        {
            "reload": "_on_reload",
            "new": "_on_new_instance",
            "open": "_on_open_instance",
            "taxonomy": "_show_loader",
            "close_instance": "_on_close_instance",
            "close_taxonomy": "_on_close_taxonomy",
        }[transition],
    )()
    assert not replace.called
    assert window._current_instance is instance
    assert window._editor is editor
    assert instance.has_unsaved_changes


def test_cancelled_creation_wizard_preserves_document(document_window, monkeypatch):
    from types import SimpleNamespace

    from PySide6.QtWidgets import QDialog

    window = document_window
    instance, editor = window._current_instance, window._editor
    window._current_taxonomy = object()
    wizard = SimpleNamespace(exec=lambda: QDialog.DialogCode.Rejected)
    monkeypatch.setattr(
        "bde_xbrl_editor.ui.widgets.instance_creation_wizard.wizard.InstanceCreationWizard",
        lambda **kwargs: wizard,
    )
    question = Mock(return_value=QMessageBox.StandardButton.Discard)
    monkeypatch.setattr(QMessageBox, "question", question)
    window._on_new_instance()
    assert window._current_instance is instance
    assert window._editor is editor
    assert instance.has_unsaved_changes
    assert not question.called


@pytest.mark.parametrize("dirty", [False, True])
@pytest.mark.parametrize("choice", ["Save", "Discard", "Cancel"])
def test_close_choice_matrix(document_window, monkeypatch, tmp_path, dirty, choice):
    window = document_window
    window._current_instance._dirty = dirty
    configure_save(monkeypatch, window, tmp_path, "success")
    question = Mock(return_value=getattr(QMessageBox.StandardButton, choice))
    monkeypatch.setattr(QMessageBox, "question", question)
    shutdown = Mock()
    monkeypatch.setattr(window, "_shutdown_background_tasks", shutdown)
    event = QCloseEvent()
    window.closeEvent(event)
    allowed = not dirty or choice != "Cancel"
    assert event.isAccepted() == allowed
    assert shutdown.called == allowed
    assert question.call_count == int(dirty)


def test_save_existing_path_propagates_success(document_window, monkeypatch, tmp_path):
    target = tmp_path / "existing.xbrl"
    document_window._current_instance.source_path = target
    dialog = Mock(side_effect=AssertionError("Save As must not open for existing path"))
    monkeypatch.setattr(QFileDialog, "getSaveFileName", dialog)
    assert document_window._on_save().name == "SUCCESS"
    assert target.exists()
    assert not document_window._current_instance.has_unsaved_changes


def test_declined_overwrite_preserves_existing_file(document_window, monkeypatch, tmp_path):
    target = tmp_path / "existing.xbrl"
    target.write_text("original", encoding="utf-8")
    monkeypatch.setattr(QFileDialog, "getSaveFileName", lambda *args: (str(target), ""))
    monkeypatch.setattr(QMessageBox, "question", lambda *args: QMessageBox.StandardButton.No)
    assert document_window._on_save_as().name == "CANCELLED"
    assert target.read_text(encoding="utf-8") == "original"
    assert document_window._current_instance.has_unsaved_changes
