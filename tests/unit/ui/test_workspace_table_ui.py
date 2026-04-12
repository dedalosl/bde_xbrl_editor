"""UI regression tests for workspace table chrome and instance table list."""

from __future__ import annotations

import os
from datetime import date, datetime
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

pytest.importorskip("PySide6", reason="PySide6 not available - UI tests skipped")

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QTableView

from bde_xbrl_editor.instance.editor import InstanceEditor
from bde_xbrl_editor.instance.models import BdeEstadoReportado, BdePreambulo
from bde_xbrl_editor.taxonomy.models import BreakdownNode, TableDefinitionPWD, TaxonomyMetadata, TaxonomyStructure
from bde_xbrl_editor.ui.widgets.activity_sidebar import _InstancePanel
from bde_xbrl_editor.ui.widgets.xbrl_table_view import XbrlTableView


def _leaf(label: str) -> BreakdownNode:
    return BreakdownNode(node_type="rule", label=label, is_abstract=False)


def _table(table_id: str, label: str, *, table_code: str | None = None) -> TableDefinitionPWD:
    return TableDefinitionPWD(
        table_id=table_id,
        label=label,
        extended_link_role=f"http://example.com/role/{table_id}",
        x_breakdown=BreakdownNode(node_type="rule", is_abstract=True, children=[_leaf("Column")]),
        y_breakdown=BreakdownNode(node_type="rule", is_abstract=True, children=[_leaf("Row")]),
        table_code=table_code,
    )


def _taxonomy_with_tables(*tables: TableDefinitionPWD) -> TaxonomyStructure:
    return TaxonomyStructure(
        metadata=TaxonomyMetadata(
            name="SmokeTax",
            version="1.0",
            publisher="Test",
            entry_point_path=Path("tax.xsd"),
            loaded_at=datetime(2024, 1, 1),
            declared_languages=("es", "en"),
        ),
        concepts={},
        labels=MagicMock(),
        presentation={},
        calculation={},
        definition={},
        hypercubes=[],
        dimensions={},
        tables=list(tables),
    )


def _instance_with_tables(*table_ids: str) -> SimpleNamespace:
    return SimpleNamespace(
        schema_ref_href="http://www.bde.es/example.xsd",
        entity=SimpleNamespace(identifier="ES0001", scheme="http://example.com/entity"),
        period=SimpleNamespace(period_type="instant", instant_date=date(2024, 12, 31)),
        filing_indicators=[SimpleNamespace(template_id=table_id, filed=True) for table_id in table_ids],
        included_table_ids=list(table_ids),
        facts=[],
        contexts={},
        bde_preambulo=BdePreambulo(
            context_ref="cBasico",
            estados_reportados=[
                BdeEstadoReportado(codigo=table_id, blanco=False, context_ref="cBasico")
                for table_id in table_ids
            ],
        ),
    )


@pytest.mark.qt
def test_instance_panel_shows_table_codes_status_and_search(qtbot, monkeypatch) -> None:
    table_with_data = _table("es_tF1_10", "Derivados", table_code="0010")
    empty_table = _table("es_tF1_11", "Coberturas", table_code="0011")
    taxonomy = _taxonomy_with_tables(table_with_data, empty_table)
    instance = _instance_with_tables("0010", "0011")

    monkeypatch.setattr(
        _InstancePanel,
        "_compute_table_data_presence",
        staticmethod(lambda _instance, _taxonomy, _tables: {
            "es_tF1_10": True,
            "es_tF1_11": False,
        }),
    )

    panel = _InstancePanel()
    qtbot.addWidget(panel)
    panel.show()
    panel.populate(instance, taxonomy)

    assert panel._table_list.count() == 2
    assert "0010  |  es_tF1_10  |  Contains data" in panel._table_list.item(0).text()
    assert panel._table_list.item(0).font().bold()
    assert "0011  |  es_tF1_11  |  Empty" in panel._table_list.item(1).text()

    panel._table_search.setText("0011")
    qtbot.waitUntil(lambda: panel._table_list.count() == 1, timeout=1000)
    assert "Coberturas" in panel._table_list.item(0).text()


@pytest.mark.qt
def test_instance_panel_edits_bde_filing_indicators_with_checkboxes(qtbot, monkeypatch) -> None:
    table_with_data = _table("es_tF1_10", "Derivados", table_code="0010")
    empty_table = _table("es_tF1_11", "Coberturas", table_code="0011")
    taxonomy = _taxonomy_with_tables(table_with_data, empty_table)
    instance = _instance_with_tables("0010", "0011")
    editor = InstanceEditor(instance)

    monkeypatch.setattr(
        _InstancePanel,
        "_compute_table_data_presence",
        staticmethod(lambda _instance, _taxonomy, _tables: {
            "es_tF1_10": True,
            "es_tF1_11": False,
        }),
    )

    panel = _InstancePanel()
    qtbot.addWidget(panel)
    panel.show()
    panel.populate(instance, taxonomy)
    panel.set_editor(editor)
    panel.set_editing_enabled(False)

    assert panel._fi_list.count() == 2
    assert not panel._fi_list.isHidden()
    assert panel._fi_list.isEnabled()
    first_item = panel._fi_list.item(0)
    assert first_item.checkState() == Qt.CheckState.Checked
    assert not bool(first_item.flags() & Qt.ItemFlag.ItemIsUserCheckable)

    first_item.setCheckState(Qt.CheckState.Unchecked)

    assert instance.filing_indicators[0].filed is True
    panel.set_editing_enabled(True)
    assert panel._fi_list.isEnabled()
    assert bool(first_item.flags() & Qt.ItemFlag.ItemIsUserCheckable)

    first_item.setCheckState(Qt.CheckState.Checked)
    first_item.setCheckState(Qt.CheckState.Unchecked)

    assert instance.filing_indicators[0].filed is False
    assert instance.bde_preambulo is not None
    assert instance.bde_preambulo.estados_reportados[0].blanco is True


@pytest.mark.qt
def test_xbrl_table_view_uses_editing_switch_instead_of_passive_mode_pills(qtbot) -> None:
    table = _table("es_tF1_10", "Derivados", table_code="0010")
    taxonomy = _taxonomy_with_tables(table)
    instance = MagicMock()
    instance.facts = []
    instance.contexts = {}

    view = XbrlTableView()
    qtbot.addWidget(view)
    view.resize(960, 640)
    view.show()
    view.set_table(table, taxonomy, instance)

    qtbot.waitUntil(lambda: not view._editing_switch.isHidden(), timeout=1000)
    assert view._editing_switch.text() == "Editing mode off"
    assert view._body_view.editTriggers() == QTableView.EditTrigger.NoEditTriggers
    assert "0010  |  es_tF1_10" in view._subtitle_label.text()

    qtbot.mouseClick(view._editing_switch, Qt.MouseButton.LeftButton)
    assert view._editing_switch.text() == "Editing mode on"
    assert view._body_view.editTriggers() != QTableView.EditTrigger.NoEditTriggers


@pytest.mark.qt
def test_collapsible_section_arrow_matches_open_state(qtbot) -> None:
    section = _InstancePanel()
    qtbot.addWidget(section)
    section.show()

    assert section._tables_section._btn.text().startswith("▾")
    section._tables_section._btn.click()
    assert section._tables_section._btn.text().startswith("▸")
    section._tables_section._btn.click()
    assert section._tables_section._btn.text().startswith("▾")
