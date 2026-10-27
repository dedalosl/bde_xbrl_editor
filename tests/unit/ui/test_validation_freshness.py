"""Validation results must describe the current document revision."""

from datetime import datetime
from threading import Event

import pytest
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QFileDialog
from test_main_window_document_safety import document_window as _document_window_fixture

from bde_xbrl_editor.instance.models import Fact
from bde_xbrl_editor.taxonomy.models import QName
from bde_xbrl_editor.ui.widgets.validation_panel import ValidationPanel
from bde_xbrl_editor.validation.models import (
    ValidationFinding,
    ValidationReport,
    ValidationSeverity,
)

document_window = _document_window_fixture


def report(message="old"):
    return ValidationReport(
        "instance.xbrl",
        "Test",
        "1",
        datetime(2025, 1, 1),
        (ValidationFinding("R", ValidationSeverity.ERROR, message, "structural"),),
        True,
    )


def test_edit_invalidates_result_and_export(document_window, monkeypatch, tmp_path):
    window = document_window
    window._ensure_validation_panel()
    window._on_validation_done(report())
    window._on_changes_made()
    assert not window._validation_panel._export_btn.isEnabled()
    assert "outdated" in window._validation_collapsed_button.text().lower()
    path = tmp_path / "report.json"
    monkeypatch.setattr(QFileDialog, "getSaveFileName", lambda *args: (str(path), "JSON"))
    window._validation_panel.export_report()
    assert not path.exists()


def test_equal_count_results_replace_rows(qtbot):
    panel = ValidationPanel()
    qtbot.addWidget(panel)
    panel.show_report(report("old"))
    panel.show_report(report("new"))
    assert panel._model.item(0, 0).data(Qt.ItemDataRole.UserRole).message == "new"


def test_export_rechecks_after_dialog(qtbot, monkeypatch, tmp_path):
    panel = ValidationPanel()
    qtbot.addWidget(panel)
    panel.show_report(report())
    path = tmp_path / "report.json"

    def dialog(*args):
        panel.invalidate_report()
        return str(path), "JSON"

    monkeypatch.setattr(QFileDialog, "getSaveFileName", dialog)
    panel.export_report()
    assert not path.exists()


def test_worker_snapshot_rejects_edit_then_revalidates(document_window, monkeypatch, qtbot):
    window = document_window
    window._current_taxonomy = object()
    monkeypatch.setattr(window, "_prompt_formula_general_variable_values", lambda: {})
    window._current_instance.add_fact(Fact(QName("urn:test", "amount"), "ctx", None, "10"))
    entered, release = Event(), Event()
    captured = []

    def validate(self, instance):
        captured.append(instance)
        entered.set()
        assert release.wait(3)
        return report()

    monkeypatch.setattr(
        "bde_xbrl_editor.validation.orchestrator.InstanceValidator.validate_sync", validate
    )
    window._trigger_validation()
    try:
        qtbot.waitUntil(entered.is_set, timeout=2000)
        assert captured[0] is not window._current_instance
        window._editor.update_fact(0, "20")
        assert captured[0].facts[0].value == "10"
        assert window._current_instance.facts[0].value == "20"
    finally:
        release.set()
        qtbot.waitUntil(lambda: window._validation_thread is None, timeout=3000)
    assert not window._validation_panel._export_btn.isEnabled()
    window._trigger_validation()
    qtbot.waitUntil(lambda: window._validation_thread is None, timeout=3000)
    assert window._validation_panel._export_btn.isEnabled()


def test_context_creation_notifies_even_without_fact(document_window):
    from bde_xbrl_editor.ui.widgets.xbrl_table_view import _ensure_context_ref_for_dimensions

    window = document_window
    window._ensure_validation_panel()
    window._on_validation_done(report())
    _ensure_context_ref_for_dimensions(
        window._current_instance, dimensions={}, on_changed=window._on_changes_made
    )
    assert not window._validation_panel._export_btn.isEnabled()


def test_cell_context_creation_notifies(document_window):
    from bde_xbrl_editor.table_renderer.models import CellCoordinate
    from bde_xbrl_editor.ui.widgets.cell_edit_delegate import _ensure_context_ref

    window = document_window
    window._ensure_validation_panel()
    window._on_validation_done(report())
    _ensure_context_ref(
        window._current_instance, CellCoordinate(), on_changed=window._on_changes_made
    )
    assert not window._validation_panel._export_btn.isEnabled()


@pytest.mark.parametrize("mutation", ["add", "update", "remove", "context", "indicator"])
def test_editor_mutations_invalidate(document_window, mutation):
    window = document_window
    qname = QName("urn:test", "amount")
    window._editor.add_fact(qname, "ctx", "10")
    window._ensure_validation_panel()
    window._on_validation_done(report())
    if mutation == "add":
        window._editor.add_fact(QName("urn:test", "other"), "ctx", "20")
    elif mutation == "update":
        window._editor.update_fact(0, "20")
    elif mutation == "remove":
        window._editor.remove_fact(0)
    elif mutation == "context":
        window._editor.reassign_facts_context([0], "new-context")
    else:
        window._editor.set_filing_indicator("T1", True)
    assert window._validation_panel._current_report is None
    assert not window._validation_panel._export_btn.isEnabled()


@pytest.mark.parametrize("changed", ["content", "document", "rules", "run"])
def test_old_callbacks_cannot_publish_or_clean_new_worker(document_window, monkeypatch, changed):
    from PySide6.QtWidgets import QMessageBox

    from bde_xbrl_editor.ui.widgets.validation_panel import ValidationWorker

    window = document_window
    window._ensure_validation_panel()
    old = ValidationWorker(object(), window._current_instance)
    old.binding = window._validation_binding()
    old.progress_changed.connect(window._on_validation_progress)
    old.findings_ready.connect(window._on_validation_findings_ready)
    old.validation_completed.connect(window._on_validation_done)
    old.validation_failed.connect(window._on_validation_error)
    attribute = {
        "content": "_content_revision",
        "document": "_document_generation",
        "rules": "_rules_revision",
        "run": "_validation_run_id",
    }[changed]
    setattr(window, attribute, getattr(window, attribute) + 1)
    new = ValidationWorker(object(), window._current_instance)
    new.binding = window._validation_binding()
    window._validation_worker = new
    window._validation_panel.show_progress(0, 1, "new run")
    monkeypatch.setattr(QMessageBox, "critical", lambda *args: pytest.fail("stale error displayed"))
    old.progress_changed.emit(1, 1, "stale")
    old.findings_ready.emit(report().findings)
    old.validation_failed.emit("stale error")
    old.validation_completed.emit(report())
    assert window._validation_worker is new
    assert window._validation_panel._summary_label.text() == "new run"
    assert window._validation_panel._model.rowCount() == 0
    assert window._validation_panel._current_report is None
    window._validation_worker = None


@pytest.mark.parametrize("partial", [True, False])
def test_rule_hydration_invalidates(document_window, monkeypatch, partial):
    from types import SimpleNamespace

    window = document_window
    window._ensure_validation_panel()
    window._on_validation_done(report())
    monkeypatch.setattr(window, "_same_taxonomy", lambda taxonomy: True)
    monkeypatch.setattr(window, "_cleanup_formula_hydration_thread", lambda **kwargs: None)
    monkeypatch.setattr(window._cache, "put", lambda *args: None)
    taxonomy = SimpleNamespace(
        formula_assertion_set=SimpleNamespace(assertions=()),
        metadata=SimpleNamespace(entry_point_path=window._current_instance.taxonomy_entry_point),
    )
    action = (
        window._on_formula_hydration_partial if partial else window._on_formula_hydration_finished
    )
    action(taxonomy)
    assert window._rules_revision == 1
    assert not window._validation_panel._export_btn.isEnabled()


def test_source_context_creation_and_noop_notifications(document_window):
    from unittest.mock import Mock

    from bde_xbrl_editor.ui.widgets.xbrl_table_view import _ensure_context_ref_for_dimensions

    instance = document_window._current_instance
    ref = _ensure_context_ref_for_dimensions(instance, dimensions={})
    changed = Mock()
    kwargs = dict(
        dimensions={QName("urn:test", "dim"): QName("urn:test", "member")},
        source_context=instance.contexts[ref],
        on_changed=changed,
    )
    new_ref = _ensure_context_ref_for_dimensions(instance, **kwargs)
    assert new_ref != ref
    assert changed.call_count == 1
    _ensure_context_ref_for_dimensions(instance, **kwargs)
    assert changed.call_count == 1
