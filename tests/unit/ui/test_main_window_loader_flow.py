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
    qtbot.mouseClick(window._sidebar._buttons[1], Qt.MouseButton.LeftButton)
    qtbot.waitUntil(lambda: splitter.sizes()[0] <= 60, timeout=1000)
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
