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
from bde_xbrl_editor.taxonomy.constants import ARCROLE_DOMAIN_MEMBER
from bde_xbrl_editor.taxonomy.models import (
    BreakdownNode,
    DefinitionArc,
    DimensionModel,
    DomainMember,
    HypercubeModel,
    QName,
    TableDefinitionPWD,
    TaxonomyMetadata,
    TaxonomyStructure,
)
from bde_xbrl_editor.ui.widgets.activity_sidebar import _InstancePanel
from bde_xbrl_editor.ui.widgets.xbrl_table_view import XbrlTableView


class _LabelResolverStub:
    def __init__(self, mapping: dict[QName, str] | None = None) -> None:
        self._mapping = mapping or {}

    def resolve(self, qname, **kwargs) -> str:
        return self._mapping.get(qname, getattr(qname, "local_name", str(qname)))

    def get_all_labels(self, qname) -> list:
        return []


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
        labels=_LabelResolverStub(),
        presentation={},
        calculation={},
        definition={},
        hypercubes=[],
        dimensions={},
        tables=list(tables),
    )


def _taxonomy_with_single_view_z_axis(table: TableDefinitionPWD) -> TaxonomyStructure:
    dim_qname = QName(namespace="http://example.com/dim", local_name="DimZ", prefix="dim")
    root_member = QName(namespace="http://example.com/mem", local_name="RootMember", prefix="mem")
    member_a = QName(namespace="http://example.com/mem", local_name="MemberA", prefix="mem")
    member_b = QName(namespace="http://example.com/mem", local_name="MemberB", prefix="mem")
    other_member = QName(namespace="http://example.com/mem", local_name="OtherMember", prefix="mem")
    filter_linkrole = "http://example.com/role/filter"

    labels = _LabelResolverStub({
        dim_qname: "Dim Z",
        root_member: "Root Member",
        member_a: "Member A",
        member_b: "Member B",
        other_member: "Other Member",
    })

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
        labels=labels,
        presentation={},
        calculation={},
        definition={
            filter_linkrole: [
                DefinitionArc(
                    arcrole=ARCROLE_DOMAIN_MEMBER,
                    source=root_member,
                    target=member_a,
                    order=1.0,
                    extended_link_role=filter_linkrole,
                    usable=True,
                ),
                DefinitionArc(
                    arcrole=ARCROLE_DOMAIN_MEMBER,
                    source=root_member,
                    target=member_b,
                    order=2.0,
                    extended_link_role=filter_linkrole,
                    usable=True,
                ),
            ]
        },
        hypercubes=[
            HypercubeModel(
                qname=QName(namespace="http://example.com/hc", local_name="hc", prefix="hc"),
                arcrole="all",
                closed=True,
                context_element="scenario",
                primary_items=(),
                dimensions=(dim_qname,),
                extended_link_role=table.extended_link_role,
            )
        ],
        dimensions={
            dim_qname: DimensionModel(
                qname=dim_qname,
                dimension_type="explicit",
                default_member=None,
                domain=None,
                members=(
                    DomainMember(qname=root_member, parent=None, order=1.0),
                    DomainMember(qname=member_a, parent=None, order=1.0),
                    DomainMember(qname=member_b, parent=None, order=2.0),
                    DomainMember(qname=other_member, parent=None, order=3.0),
                ),
            )
        },
        tables=[table],
    )


def _taxonomy_with_filter_only_z_axis(table: TableDefinitionPWD) -> TaxonomyStructure:
    labels = _LabelResolverStub()

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
        labels=labels,
        presentation={},
        calculation={},
        definition={},
        hypercubes=[],
        dimensions={},
        tables=[table],
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
        dimensional_configs={},
    )


def _instance_with_filing_indicators(*template_ids: str) -> SimpleNamespace:
    return SimpleNamespace(
        schema_ref_href="http://www.bde.es/example.xsd",
        entity=SimpleNamespace(identifier="ES0001", scheme="http://example.com/entity"),
        period=SimpleNamespace(period_type="instant", instant_date=date(2024, 12, 31)),
        filing_indicators=[SimpleNamespace(template_id=template_id, filed=True) for template_id in template_ids],
        included_table_ids=list(template_ids),
        facts=[],
        contexts={},
        bde_preambulo=BdePreambulo(
            context_ref="cBasico",
            estados_reportados=[
                BdeEstadoReportado(codigo=template_id, blanco=False, context_ref="cBasico")
                for template_id in template_ids
            ],
        ),
        dimensional_configs={},
    )


def _instance_with_z_usage(
    table_id: str,
    dimension_qname: QName,
    selected_member: QName,
) -> SimpleNamespace:
    return SimpleNamespace(
        schema_ref_href="http://www.bde.es/example.xsd",
        entity=SimpleNamespace(identifier="ES0001", scheme="http://example.com/entity"),
        period=SimpleNamespace(period_type="instant", instant_date=date(2024, 12, 31)),
        filing_indicators=[],
        included_table_ids=[table_id],
        facts=[],
        contexts={
            "ctxZ": SimpleNamespace(dimensions={dimension_qname: selected_member}),
        },
        dimensional_configs={
            table_id: SimpleNamespace(
                table_id=table_id,
                dimension_assignments={dimension_qname: selected_member},
            )
        },
        bde_preambulo=None,
    )


@pytest.mark.qt
def test_instance_panel_data_presence_checks_only_active_z_slice(qtbot, monkeypatch) -> None:
    table = _table("es_tFI_20-4", "Geo assets", table_code="4530")
    taxonomy = _taxonomy_with_tables(table)
    dim_qname = QName(namespace="http://example.com/dim", local_name="qOOR", prefix="dim")
    member_qname = QName(namespace="http://example.com/mem", local_name="ES", prefix="mem")
    instance = _instance_with_z_usage(table.table_id, dim_qname, member_qname)

    calls: list[tuple[int, dict[QName, QName] | None]] = []

    class _FakeEngine:
        def __init__(self, _taxonomy) -> None:
            pass

        def compute(self, _table, instance=None, z_index=0, z_constraints=None):
            calls.append((z_index, z_constraints))
            return SimpleNamespace(
                body=[[SimpleNamespace(fact_value="1")]],
                z_members=[object(), object(), object()],
            )

    monkeypatch.setattr(
        "bde_xbrl_editor.table_renderer.layout_engine.TableLayoutEngine",
        _FakeEngine,
    )
    monkeypatch.setattr(
        "bde_xbrl_editor.ui.widgets.xbrl_table_view._derive_initial_z_constraints",
        lambda _table, _taxonomy, _instance, layout=None: {dim_qname: member_qname},
    )

    panel = _InstancePanel()
    qtbot.addWidget(panel)
    presence = panel._compute_table_data_presence(instance, taxonomy, [table])

    assert presence == {table.table_id: True}
    assert calls == [(0, {dim_qname: member_qname})]


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
def test_instance_panel_matches_b_table_indicator_to_t_table(qtbot, monkeypatch) -> None:
    table = _table("es_tFI_20-4", "Geo assets", table_code="4530")
    taxonomy = _taxonomy_with_tables(table)
    instance = _instance_with_filing_indicators("es_bFI_20-4")

    monkeypatch.setattr(
        _InstancePanel,
        "_compute_table_data_presence",
        staticmethod(lambda _instance, _taxonomy, _tables: {table.table_id: False}),
    )

    panel = _InstancePanel()
    qtbot.addWidget(panel)
    panel.show()
    panel.populate(instance, taxonomy)

    assert panel._table_list.count() == 1
    assert "es_tFI_20-4" in panel._table_list.item(0).text()
    assert "Geo assets" in panel._table_list.item(0).text()


@pytest.mark.qt
def test_instance_panel_shows_non_filed_taxonomy_tables(qtbot, monkeypatch) -> None:
    filed_table = _table("es_tF1_10", "Derivados", table_code="0010")
    non_filed_table = _table("es_tF1_11", "Coberturas", table_code="0011")
    taxonomy = _taxonomy_with_tables(filed_table, non_filed_table)
    instance = _instance_with_filing_indicators("0010")

    monkeypatch.setattr(
        _InstancePanel,
        "_compute_table_data_presence",
        staticmethod(lambda _instance, _taxonomy, _tables: {
            filed_table.table_id: True,
            non_filed_table.table_id: False,
        }),
    )

    panel = _InstancePanel()
    qtbot.addWidget(panel)
    panel.show()
    panel.populate(instance, taxonomy)

    assert panel._table_list.count() == 2
    table_texts = [panel._table_list.item(i).text() for i in range(panel._table_list.count())]
    assert any("es_tF1_10" in text for text in table_texts)
    assert any("es_tF1_11" in text for text in table_texts)


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
def test_xbrl_table_view_shows_allowed_z_axis_members_in_selector_for_single_view_table(qtbot) -> None:
    table = TableDefinitionPWD(
        table_id="es_tF1_20",
        label="Configured Z table",
        extended_link_role="http://example.com/role/es_tF1_20",
        x_breakdown=BreakdownNode(node_type="rule", is_abstract=True, children=[_leaf("Column")]),
        y_breakdown=BreakdownNode(node_type="rule", is_abstract=True, children=[_leaf("Row")]),
        z_breakdowns=(
            BreakdownNode(
                node_type="aspect",
                label="Configured view",
                is_abstract=False,
                aspect_constraints={
                    "dimensionAspect": "{http://example.com/dim}DimZ",
                    "explicitDimensionFilters": [
                        {
                            "dimension": "{http://example.com/dim}DimZ",
                            "members": [
                                {
                                    "member": "{http://example.com/mem}RootMember",
                                    "linkrole": "http://example.com/role/filter",
                                    "arcrole": ARCROLE_DOMAIN_MEMBER,
                                    "axis": "descendant",
                                }
                            ],
                            "complement": False,
                        }
                    ],
                },
            ),
        ),
    )
    taxonomy = _taxonomy_with_single_view_z_axis(table)

    view = XbrlTableView()
    qtbot.addWidget(view)
    view.resize(960, 640)
    view.show()
    view.set_table(table, taxonomy, None)

    dim_qname = QName(namespace="http://example.com/dim", local_name="DimZ", prefix="dim")
    assert view._z_selector is not None
    combo = view._z_selector._combo_by_dimension[dim_qname]
    assert combo.count() == 2
    assert combo.itemText(0) == "Member A"
    assert combo.itemText(1) == "Member B"
    assert view._z_axis_summary_label.isHidden()


@pytest.mark.qt
def test_xbrl_table_view_shows_filter_only_z_axis_members_in_selector_without_hypercube_models(qtbot) -> None:
    table = TableDefinitionPWD(
        table_id="es_tF1_21",
        label="Filter-only Z table",
        extended_link_role="http://example.com/role/es_tF1_21",
        x_breakdown=BreakdownNode(node_type="rule", is_abstract=True, children=[_leaf("Column")]),
        y_breakdown=BreakdownNode(node_type="rule", is_abstract=True, children=[_leaf("Row")]),
        z_breakdowns=(
            BreakdownNode(
                node_type="aspect",
                label="Configured view",
                is_abstract=False,
                aspect_constraints={
                    "dimensionAspect": "{http://example.com/dim}DimZ",
                    "explicitDimensionFilters": [
                        {
                            "dimension": "{http://example.com/dim}DimZ",
                            "members": [
                                {
                                    "member": "{http://example.com/mem}RootMember",
                                    "linkrole": "http://example.com/role/filter",
                                    "arcrole": ARCROLE_DOMAIN_MEMBER,
                                    "axis": "descendant",
                                    "resolved_members": [
                                        "{http://example.com/mem}ChildA",
                                        "{http://example.com/mem}ChildB",
                                    ],
                                }
                            ],
                            "complement": False,
                        }
                    ],
                },
            ),
        ),
    )
    taxonomy = _taxonomy_with_filter_only_z_axis(table)

    view = XbrlTableView()
    qtbot.addWidget(view)
    view.resize(960, 640)
    view.show()
    view.set_table(table, taxonomy, None)

    dim_qname = QName(namespace="http://example.com/dim", local_name="DimZ", prefix="dim")
    assert view._z_selector is not None
    combo = view._z_selector._combo_by_dimension[dim_qname]
    assert combo.count() == 2
    assert combo.itemText(0) == "ChildA"
    assert combo.itemText(1) == "ChildB"
    assert view._z_axis_summary_label.isHidden()


@pytest.mark.qt
def test_xbrl_table_view_prioritises_instance_z_values_and_rerenders_on_change(qtbot) -> None:
    dim_qname = QName(namespace="http://example.com/dim", local_name="DimZ", prefix="dim")
    member_a = QName(namespace="http://example.com/mem", local_name="MemberA", prefix="mem")
    member_b = QName(namespace="http://example.com/mem", local_name="MemberB", prefix="mem")
    table = TableDefinitionPWD(
        table_id="es_tF1_22",
        label="Editable Z table",
        extended_link_role="http://example.com/role/es_tF1_22",
        x_breakdown=BreakdownNode(node_type="rule", is_abstract=True, children=[_leaf("Column")]),
        y_breakdown=BreakdownNode(node_type="rule", is_abstract=True, children=[_leaf("Row")]),
        z_breakdowns=(
            BreakdownNode(
                node_type="aspect",
                label="Configured view",
                is_abstract=False,
                aspect_constraints={
                    "dimensionAspect": "{http://example.com/dim}DimZ",
                    "explicitDimensionFilters": [
                        {
                            "dimension": "{http://example.com/dim}DimZ",
                            "members": [
                                {
                                    "member": "{http://example.com/mem}RootMember",
                                    "linkrole": "http://example.com/role/filter",
                                    "arcrole": ARCROLE_DOMAIN_MEMBER,
                                    "axis": "descendant",
                                }
                            ],
                            "complement": False,
                        }
                    ],
                },
            ),
        ),
    )
    taxonomy = _taxonomy_with_single_view_z_axis(table)
    instance = _instance_with_z_usage(table.table_id, dim_qname, member_b)

    view = XbrlTableView()
    qtbot.addWidget(view)
    view.resize(960, 640)
    view.show()
    view.set_table(table, taxonomy, instance)

    assert view._z_selector is not None
    combo = view._z_selector._combo_by_dimension[dim_qname]
    assert combo.itemText(0) == "Member B"
    assert combo.itemText(1) == "Member A"
    assert view._layout is not None
    assert view._layout.body[0][0].coordinate.explicit_dimensions == {dim_qname: member_b}

    combo.setCurrentIndex(1)
    qtbot.waitUntil(
        lambda: view._layout is not None
        and view._layout.body[0][0].coordinate.explicit_dimensions == {dim_qname: member_a},
        timeout=5000,
    )
    assert (
        instance.dimensional_configs[table.table_id].dimension_assignments[dim_qname]
        == member_a
    )


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
