"""Regression tests for loader-widget handoff into the main window."""

from __future__ import annotations

import os
from datetime import date, datetime
from pathlib import Path

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

pytest.importorskip("PySide6", reason="PySide6 not available - UI flow tests skipped")

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QScrollArea, QSplitter

from bde_xbrl_editor.instance.models import ReportingEntity, ReportingPeriod, XbrlInstance
from bde_xbrl_editor.performance import LoadTiming, StageTiming
from bde_xbrl_editor.taxonomy.models import (
    FactVariableDefinition,
    FormulaAssertionSet,
    QName,
    TaxonomyMetadata,
    TaxonomyStructure,
    ValueAssertionDefinition,
)
from bde_xbrl_editor.ui.main_window import MainWindow
from bde_xbrl_editor.ui.widgets.activity_sidebar import _ValidationsPanel
from bde_xbrl_editor.ui.widgets.progress_dialog import TaxonomyProgressDialog
from bde_xbrl_editor.ui.widgets.taxonomy_loader_widget import TaxonomyLoaderWidget


def _taxonomy() -> TaxonomyStructure:
    return TaxonomyStructure(
        metadata=TaxonomyMetadata(
            name="SmokeTax",
            version="1.0",
            publisher="Test",
            entry_point_path=Path("tax.xsd"),
            loaded_at=datetime(2024, 1, 1),
            declared_languages=("en",),
        ),
        concepts={},
        labels=None,
        presentation={},
        calculation={},
        definition={},
        hypercubes=[],
        dimensions={},
        tables=[],
        formula_assertion_set=FormulaAssertionSet(),
    )


def _taxonomy_with_assertion() -> TaxonomyStructure:
    assertion = ValueAssertionDefinition(
        assertion_id="VA001",
        label="Example assertion",
        severity="error",
        abstract=False,
        variables=(
            FactVariableDefinition(
                variable_name="v",
                concept_filter=QName(namespace="http://example.com/tax", local_name="Amount"),
            ),
        ),
        precondition_xpath="$v",
        test_xpath="$v > 0",
    )
    taxonomy = _taxonomy()
    return TaxonomyStructure(
        metadata=taxonomy.metadata,
        concepts=taxonomy.concepts,
        labels=taxonomy.labels,
        presentation=taxonomy.presentation,
        calculation=taxonomy.calculation,
        definition=taxonomy.definition,
        hypercubes=taxonomy.hypercubes,
        dimensions=taxonomy.dimensions,
        tables=taxonomy.tables,
        formula_assertion_set=FormulaAssertionSet(assertions=(assertion,)),
    )


def _instance() -> XbrlInstance:
    return XbrlInstance(
        taxonomy_entry_point=Path("tax.xsd"),
        schema_ref_href="tax.xsd",
        entity=ReportingEntity(identifier="ENTITY", scheme="http://example.com"),
        period=ReportingPeriod(period_type="instant", instant_date=date(2024, 12, 31)),
    )


def test_loader_instance_handoff_survives_recent_file_write_error(qtbot, qapp, monkeypatch) -> None:
    """Opening an instance must still switch away from the loader if recents persistence fails."""
    monkeypatch.setattr(
        "bde_xbrl_editor.ui.widgets.taxonomy_loader_widget.add_recent_instance",
        lambda _path: (_ for _ in ()).throw(PermissionError("settings not writable")),
    )

    window = MainWindow()
    qtbot.addWidget(window)

    loader = window.centralWidget()
    assert isinstance(loader, TaxonomyLoaderWidget)

    loader._inst_path_edit.setText("sample-instance.xbrl")
    loader._show_progress_dialog("Loading", "Preparing")

    loader._on_inst_load_finished(_instance(), _taxonomy())
    qtbot.waitUntil(lambda: window._current_instance is not None, timeout=1000)

    assert window._current_instance is not None
    assert window._sidebar is not None
    assert not isinstance(window.centralWidget(), TaxonomyLoaderWidget)


def test_progress_dialog_keeps_recent_milestones(qtbot, qapp) -> None:
    dialog = TaxonomyProgressDialog()
    qtbot.addWidget(dialog)

    dialog.reset()
    dialog.set_context("Taxonomy", "/tmp/sample-taxonomy.xsd")
    dialog.update_progress("DTS discovered — 4 schemas, 3 linkbases", 1, 7)
    dialog.update_progress("Tables prepared — 12 available", 5, 7)
    dialog.update_progress("Tables prepared — 12 available", 5, 7)

    assert dialog._context_label.text().startswith("sample-taxonomy.xsd")
    assert dialog._activity_list.count() == 2
    assert dialog._activity_list.item(0).text() == "Tables prepared — 12 available"
    assert dialog._activity_count.text() == "2 updates"


def test_async_instance_open_path_uses_loading_dialog(qtbot, qapp, monkeypatch) -> None:
    def fake_run(self) -> None:
        self.progress.emit("Taxonomy ready — 0 tables, 0 concepts", 72, 100)
        self.finished.emit(_instance(), _taxonomy())

    monkeypatch.setattr("bde_xbrl_editor.ui.main_window.InstanceLoadWorker.run", fake_run)

    window = MainWindow()
    qtbot.addWidget(window)

    window._begin_instance_open("sample-instance.xbrl")
    qtbot.waitUntil(lambda: window._current_instance is not None, timeout=1000)

    assert window._loading_dialog is not None
    assert window._loading_dialog._activity_list.count() >= 1
    assert window._instance_open_thread is None
    assert window._open_instance_action.isEnabled()


def test_instance_open_stages_taxonomy_before_instance_finishes(qtbot, qapp, monkeypatch) -> None:
    staged_taxonomy = _taxonomy()

    window = MainWindow()
    qtbot.addWidget(window)

    window._on_open_instance_taxonomy_resolved(staged_taxonomy)

    assert window._current_taxonomy == staged_taxonomy
    assert window._current_instance is None
    assert window._sidebar is not None
    assert window._browser_splitter is not None
    assert [btn.text() for btn in window._sidebar._buttons if not btn.isHidden()] == ["TAB", "VAL"]


def test_instance_open_passes_current_taxonomy_for_reuse(qtbot, qapp, monkeypatch) -> None:
    current_taxonomy = _taxonomy()
    monkeypatch.setattr("bde_xbrl_editor.ui.main_window.QThread.start", lambda self: None)

    window = MainWindow()
    qtbot.addWidget(window)
    window._on_taxonomy_loaded(current_taxonomy)

    window._begin_instance_open("sample-instance.xbrl")

    assert window._instance_open_worker is not None
    assert window._instance_open_worker._preloaded_taxonomy is current_taxonomy
    assert window._current_taxonomy is current_taxonomy


def test_instance_load_worker_uses_thread_path_for_preloaded_taxonomy(qapp, monkeypatch) -> None:
    from bde_xbrl_editor.taxonomy import LoaderSettings, TaxonomyCache
    from bde_xbrl_editor.ui.loading import InstanceLoadWorker

    taxonomy = _taxonomy()
    instance = _instance()
    finished = []

    def fake_parse(path, settings, preloaded_taxonomy, *, progress_callback):
        progress_callback("Parsing with warm taxonomy", 50, 100)
        assert path == "sample-instance.xbrl"
        assert preloaded_taxonomy is taxonomy
        return instance, taxonomy, 0

    def fail_get_context(_method):
        raise AssertionError("warm taxonomy opens should not spawn a process")

    monkeypatch.setattr(
        "bde_xbrl_editor.ui.loading._parse_instance_with_preloaded_taxonomy",
        fake_parse,
    )
    monkeypatch.setattr("bde_xbrl_editor.ui.loading.multiprocessing.get_context", fail_get_context)

    worker = InstanceLoadWorker(TaxonomyCache(), LoaderSettings(), "sample-instance.xbrl")
    worker.set_preloaded_taxonomy(taxonomy)
    worker.finished.connect(lambda inst, tax: finished.append((inst, tax)))

    worker.run()

    assert finished == [(instance, taxonomy)]


def test_instance_process_entry_does_not_queue_duplicate_taxonomy(monkeypatch) -> None:
    from bde_xbrl_editor.taxonomy import LoaderSettings
    from bde_xbrl_editor.ui.loading import _instance_load_process_entry

    taxonomy = _taxonomy()
    instance = _instance()
    messages = []

    class QueueStub:
        def put(self, message):
            messages.append(message)

    class ParserStub:
        def __init__(self, taxonomy_loader):
            self.taxonomy_loader = taxonomy_loader

        def load(
            self,
            path,
            *,
            progress_callback,
            taxonomy_resolved_callback,
            preloaded_taxonomy,
        ):
            assert preloaded_taxonomy is None
            progress_callback("Loading taxonomy…", 12, 100)
            taxonomy_resolved_callback(taxonomy)
            return instance, []

    monkeypatch.setattr("bde_xbrl_editor.instance.parser.InstanceParser", ParserStub)

    _instance_load_process_entry(
        "sample-instance.xbrl",
        LoaderSettings(),
        None,
        QueueStub(),
    )

    assert [message[0] for message in messages] == ["progress", "finished"]
    assert messages[-1][2] is taxonomy


def test_taxonomy_open_uses_tabs_and_validations_sidebar_only(qtbot, qapp) -> None:
    window = MainWindow()
    qtbot.addWidget(window)

    window._on_taxonomy_loaded(_taxonomy())

    assert window._sidebar is not None
    assert [btn.text() for btn in window._sidebar._buttons if not btn.isHidden()] == ["TAB", "VAL"]


def test_instance_open_uses_instance_sidebar_only(qtbot, qapp) -> None:
    window = MainWindow()
    qtbot.addWidget(window)

    window._current_taxonomy = _taxonomy()
    window._load_instance(_instance())

    assert window._sidebar is not None
    assert [btn.text() for btn in window._sidebar._buttons if not btn.isHidden()] == ["INS"]


def test_new_instance_load_enables_editing_mode_immediately(qtbot, qapp) -> None:
    window = MainWindow()
    qtbot.addWidget(window)

    window._current_taxonomy = _taxonomy()
    window._load_instance(_instance(), enable_editing=True)

    assert window._table_view is not None
    assert window._table_view.editing_enabled is True
    assert window._sidebar is not None
    assert window._sidebar._instance_panel is not None
    assert window._sidebar._instance_panel._editing_enabled is True


def test_taxonomy_load_status_shows_timing_breakdown(qtbot, qapp) -> None:
    window = MainWindow()
    qtbot.addWidget(window)
    window._loader_widget = type(
        "_LoaderStub",
        (),
        {
            "last_taxonomy_load_timing": LoadTiming(
                total_seconds=1.5,
                stages=(StageTiming("taxonomy load", 1.5),),
            )
        },
    )()

    window._on_taxonomy_loaded(_taxonomy())

    assert "taxonomy load" in window.statusBar().currentMessage()


def test_validation_done_status_shows_timing_breakdown(qtbot, qapp) -> None:
    from bde_xbrl_editor.validation.models import ValidationReport

    window = MainWindow()
    qtbot.addWidget(window)
    report = ValidationReport(
        instance_path="/tmp/inst.xbrl",
        taxonomy_name="SmokeTax",
        taxonomy_version="1.0",
        run_timestamp=datetime(2024, 1, 1),
        findings=(),
        formula_linkbase_available=True,
        stage_timings=(
            StageTiming("structural", 0.1),
            StageTiming("formula", 1.2),
        ),
    )

    window._on_validation_done(report)

    assert "Validation PASSED" in window.statusBar().currentMessage()
    assert "structural" in window.statusBar().currentMessage()


def test_workspace_initial_table_render_is_deferred_beyond_current_event_loop(
    qtbot, qapp, monkeypatch
) -> None:
    delays: list[int] = []

    monkeypatch.setattr(
        "bde_xbrl_editor.ui.main_window.QTimer.singleShot",
        lambda delay, callback: delays.append(delay),
    )

    window = MainWindow()
    qtbot.addWidget(window)

    window._on_taxonomy_loaded(_taxonomy())
    window._current_taxonomy = _taxonomy()
    window._load_instance(_instance())

    assert delays
    assert MainWindow._INITIAL_TABLE_RENDER_DELAY_MS in delays


def test_reload_to_loader_then_reopen_instance_rebuilds_browser_views(
    qtbot, qapp, monkeypatch
) -> None:
    """Reloading back to the loader must not reuse Qt widgets deleted with the old workspace."""
    monkeypatch.setattr(TaxonomyLoaderWidget, "_on_load", lambda self: None)

    window = MainWindow()
    qtbot.addWidget(window)

    window._on_taxonomy_loaded(_taxonomy())
    old_splitter = window._browser_splitter
    old_table_view = window._table_view

    window._on_reload()

    assert isinstance(window.centralWidget(), TaxonomyLoaderWidget)
    assert window._browser_splitter is None
    assert window._table_view is None

    loader = window.centralWidget()
    assert isinstance(loader, TaxonomyLoaderWidget)

    loader._inst_path_edit.setText("sample-instance.xbrl")
    loader._show_progress_dialog("Loading", "Preparing")
    loader._on_inst_load_finished(_instance(), _taxonomy())
    qtbot.waitUntil(lambda: window._current_instance is not None, timeout=1000)

    assert window._browser_splitter is not None
    assert window._table_view is not None
    assert window._browser_splitter is not old_splitter
    assert window._table_view is not old_table_view


def test_deferred_refresh_is_safe_after_returning_to_loader(qtbot, qapp) -> None:
    """A queued table refresh must no-op cleanly if the browser view is replaced first."""
    window = MainWindow()
    qtbot.addWidget(window)

    window._on_taxonomy_loaded(_taxonomy())
    window._on_changes_made()
    window._show_loader_widget()
    qtbot.wait(20)

    assert isinstance(window.centralWidget(), TaxonomyLoaderWidget)
    assert window._table_view is None


def test_collapsing_active_sidebar_button_reallocates_splitter_space(qtbot, qapp) -> None:
    """Clicking the active activity-bar button should give space back to the main view."""
    window = MainWindow()
    qtbot.addWidget(window)
    window.resize(1200, 700)
    window.show()

    window._on_taxonomy_loaded(_taxonomy())
    qtbot.waitUntil(lambda: window._browser_splitter is not None, timeout=1000)
    qtbot.waitUntil(lambda: sum(window._browser_splitter.sizes()) > 400, timeout=1000)

    assert window._sidebar is not None
    splitter = window._browser_splitter
    assert splitter is not None

    before = splitter.sizes()
    window._sidebar._on_button_clicked(1)
    qtbot.waitUntil(lambda: splitter.sizes()[0] <= 60, timeout=1000)
    qtbot.waitUntil(lambda: window._sidebar.width() == 44, timeout=1000)
    after = splitter.sizes()

    assert after[0] < before[0]
    assert after[1] > before[1]
    assert window._sidebar.width() == 44


def test_validation_details_are_wrapped_in_scroll_area(qtbot, qapp) -> None:
    """The formula validation detail section should be scrollable for long rule details."""
    panel = _ValidationsPanel(_taxonomy_with_assertion())
    qtbot.addWidget(panel)
    panel.resize(320, 640)
    panel.show()

    assert isinstance(panel._detail_scroll, QScrollArea)
    assert panel._detail_scroll.verticalScrollBarPolicy() == Qt.ScrollBarPolicy.ScrollBarAsNeeded
    assert isinstance(panel._content_splitter, QSplitter)
    assert panel._content_splitter.orientation() == Qt.Orientation.Vertical
    assert not panel._detail_section._btn.isChecked()
    assert panel._content_splitter.handleWidth() == 0

    sizes = panel._content_splitter.sizes()
    assert sizes[0] > 0
    assert sizes[1] > 0
    assert sizes[1] <= panel._detail_section._btn.sizeHint().height() + 6
    assert panel._assertion_lists[0].viewport().height() > 300


def test_validation_details_toggle_expands_resizable_split(qtbot, qapp) -> None:
    """Selecting a rule opens the details pane inside the vertical splitter."""
    panel = _ValidationsPanel(_taxonomy_with_assertion())
    qtbot.addWidget(panel)
    panel.resize(320, 640)
    panel.show()

    first_list = panel._assertion_lists[0]
    first_item = first_list.item(0)
    first_list.setCurrentItem(first_item)
    qtbot.waitUntil(lambda: panel._detail_section._btn.isChecked(), timeout=1000)

    sizes = panel._content_splitter.sizes()
    assert panel._detail_section._btn.isChecked()
    assert panel._content_splitter.handleWidth() == 6
    assert sizes[0] > 0
    assert sizes[1] > 0
