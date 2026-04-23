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

from bde_xbrl_editor.instance.constants import BDE_DIM_NS
from bde_xbrl_editor.instance.context_builder import build_dimensional_context
from bde_xbrl_editor.instance.editor import InstanceEditor
from bde_xbrl_editor.instance.models import (
    BdeEstadoReportado,
    BdePreambulo,
    Fact,
    ReportingEntity,
    ReportingPeriod,
    XbrlInstance,
)
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
from bde_xbrl_editor.ui.widgets.table_body_model import OPEN_KEY_ROLE
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


def _taxonomy_with_open_row_dimension(table: TableDefinitionPWD) -> tuple[TaxonomyStructure, QName, QName]:
    dim_qname = QName(namespace="http://example.com/dim", local_name="OpenDim", prefix="dim")
    member_a = QName(namespace="http://example.com/mem", local_name="MemberA", prefix="mem")
    member_b = QName(namespace="http://example.com/mem", local_name="MemberB", prefix="mem")
    member_c = QName(namespace="http://example.com/mem", local_name="MemberC", prefix="mem")
    concept_qname = QName(namespace="http://example.com/met", local_name="OpenConcept", prefix="met")
    labels = _LabelResolverStub({
        member_a: "Member A",
        member_b: "Member B",
        member_c: "Member C",
        dim_qname: "Open dimension",
        concept_qname: "Open concept",
    })
    taxonomy = TaxonomyStructure(
        metadata=TaxonomyMetadata(
            name="OpenRowsTax",
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
        dimensions={
            dim_qname: DimensionModel(
                qname=dim_qname,
                dimension_type="explicit",
                default_member=None,
                domain=None,
                members=(
                    DomainMember(qname=member_a, parent=None, order=1.0),
                    DomainMember(qname=member_b, parent=None, order=2.0),
                    DomainMember(qname=member_c, parent=None, order=3.0),
                ),
            )
        },
        tables=[table],
    )
    return taxonomy, dim_qname, member_c


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


def _instance_for_open_rows() -> SimpleNamespace:
    return SimpleNamespace(
        schema_ref_href="http://www.bde.es/example.xsd",
        entity=SimpleNamespace(identifier="ES0001", scheme="http://example.com/entity"),
        period=SimpleNamespace(period_type="instant", instant_date=date(2024, 12, 31)),
        filing_indicators=[],
        included_table_ids=[],
        facts=[],
        contexts={},
        dimensional_configs={},
        bde_preambulo=None,
    )


def _instance_with_open_row_fact(member_qname: QName) -> SimpleNamespace:
    concept_qname = QName(namespace="http://example.com/met", local_name="OpenConcept", prefix="met")
    row_dim_qname = QName(namespace="http://example.com/dim", local_name="OpenDim", prefix="dim")
    agrupacion_dim_qname = QName(namespace=BDE_DIM_NS, local_name="Agrupacion", prefix="bde")
    agrupacion_member = QName(namespace="http://example.com/bde", local_name="AgrupacionIndividual", prefix="bde")
    return SimpleNamespace(
        schema_ref_href="http://www.bde.es/example.xsd",
        entity=SimpleNamespace(identifier="ES0001", scheme="http://example.com/entity"),
        period=SimpleNamespace(period_type="instant", instant_date=date(2024, 12, 31)),
        filing_indicators=[],
        included_table_ids=[],
        facts=[
            SimpleNamespace(
                concept=concept_qname,
                context_ref="ctx_open_dynamic",
                value="10",
                decimals=None,
            )
        ],
        contexts={
            "ctx_open_dynamic": SimpleNamespace(
                dimensions={
                    row_dim_qname: member_qname,
                    agrupacion_dim_qname: agrupacion_member,
                }
            )
        },
        dimensional_configs={},
        bde_preambulo=None,
    )


def _editable_instance_with_open_row_fact(member_qname: QName) -> XbrlInstance:
    concept_qname = QName(namespace="http://example.com/met", local_name="OpenConcept", prefix="met")
    row_dim_qname = QName(namespace="http://example.com/dim", local_name="OpenDim", prefix="dim")
    entity = ReportingEntity(identifier="ES0001", scheme="http://example.com/entity")
    period = ReportingPeriod(period_type="instant", instant_date=date(2024, 12, 31))
    context = build_dimensional_context(entity, period, {row_dim_qname: member_qname})
    return XbrlInstance(
        taxonomy_entry_point=Path("tax.xsd"),
        schema_ref_href="http://www.bde.es/example.xsd",
        entity=entity,
        period=period,
        contexts={context.context_id: context},
        facts=[
            Fact(
                concept=concept_qname,
                context_ref=context.context_id,
                unit_ref=None,
                value="10",
            )
        ],
    )


def _open_row_table() -> TableDefinitionPWD:
    concept_clark = "{http://example.com/met}OpenConcept"
    dim_clark = "{http://example.com/dim}OpenDim"
    member_a = "{http://example.com/mem}MemberA"
    member_b = "{http://example.com/mem}MemberB"
    return TableDefinitionPWD(
        table_id="es_tOPEN_1",
        label="Open rows table",
        extended_link_role="http://example.com/role/es_tOPEN_1",
        x_breakdown=BreakdownNode(node_type="rule", is_abstract=True, children=[_leaf("Column")]),
        y_breakdown=BreakdownNode(
            node_type="rule",
            is_abstract=True,
            children=[
                BreakdownNode(
                    node_type="rule",
                    label="Dynamic section",
                    is_abstract=True,
                    aspect_constraints={"concept": concept_clark},
                    children=[
                        BreakdownNode(
                            node_type="rule",
                            label="Member A row",
                            is_abstract=False,
                            aspect_constraints={
                                "concept": concept_clark,
                                "explicitDimension": {dim_clark: member_a},
                            },
                        ),
                        BreakdownNode(
                            node_type="rule",
                            label="Member B row",
                            is_abstract=False,
                            aspect_constraints={
                                "concept": concept_clark,
                                "explicitDimension": {dim_clark: member_b},
                            },
                        ),
                    ],
                ),
            ],
        ),
    )


def _open_aspect_table() -> TableDefinitionPWD:
    dim_clark = "{http://example.com/dim}OpenDim"
    return TableDefinitionPWD(
        table_id="es_tOPEN_ASPECT",
        label="Open aspect rows table",
        extended_link_role="http://example.com/role/es_tOPEN_ASPECT",
        x_breakdown=BreakdownNode(node_type="rule", is_abstract=True, children=[_leaf("Column")]),
        y_breakdown=BreakdownNode(
            node_type="rule",
            is_abstract=True,
            children=[
                BreakdownNode(
                    node_type="aspect",
                    label="",
                    is_abstract=False,
                    aspect_constraints={"dimensionAspect": dim_clark},
                )
            ],
        ),
    )


def _mixed_open_aspect_table() -> TableDefinitionPWD:
    typed_dim_clark = "{http://example.com/dim}LineName"
    explicit_dim_clark = "{http://example.com/dim}LineCode"
    return TableDefinitionPWD(
        table_id="es_tOPEN_ASPECT_MIXED",
        label="Mixed open aspect rows table",
        extended_link_role="http://example.com/role/es_tOPEN_ASPECT_MIXED",
        x_breakdown=BreakdownNode(node_type="rule", is_abstract=True, children=[_leaf("Column")]),
        y_breakdown=BreakdownNode(
            node_type="rule",
            is_abstract=True,
            children=[
                BreakdownNode(
                    node_type="aspect",
                    label="",
                    is_abstract=False,
                    aspect_constraints={"dimensionAspect": typed_dim_clark},
                ),
                BreakdownNode(
                    node_type="aspect",
                    label="",
                    is_abstract=False,
                    aspect_constraints={"dimensionAspect": explicit_dim_clark},
                ),
            ],
        ),
    )


def _taxonomy_with_mixed_open_row_dimensions(table: TableDefinitionPWD) -> tuple[TaxonomyStructure, QName, QName, QName]:
    typed_dim = QName(namespace="http://example.com/dim", local_name="LineName", prefix="dim")
    explicit_dim = QName(namespace="http://example.com/dim", local_name="LineCode", prefix="dim")
    member_c = QName(namespace="http://example.com/mem", local_name="MemberC", prefix="mem")
    concept_qname = QName(namespace="http://example.com/met", local_name="OpenConcept", prefix="met")
    labels = _LabelResolverStub({
        typed_dim: "Nombre",
        explicit_dim: "Codigo",
        member_c: "Member C",
        concept_qname: "Open concept",
    })
    taxonomy = TaxonomyStructure(
        metadata=TaxonomyMetadata(
            name="OpenRowsTax",
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
        dimensions={
            typed_dim: DimensionModel(
                qname=typed_dim,
                dimension_type="typed",
                default_member=None,
                domain=None,
                members=(),
            ),
            explicit_dim: DimensionModel(
                qname=explicit_dim,
                dimension_type="explicit",
                default_member=None,
                domain=None,
                members=(DomainMember(qname=member_c, parent=None, order=1.0),),
            ),
        },
        tables=[table],
    )
    return taxonomy, typed_dim, explicit_dim, member_c


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
def test_instance_panel_data_presence_uses_filing_indicators_before_layout_compute(qtbot, monkeypatch) -> None:
    table_with_data = _table("es_tF1_10", "Derivados", table_code="0010")
    empty_table = _table("es_tF1_11", "Coberturas", table_code="0011")
    taxonomy = _taxonomy_with_tables(table_with_data, empty_table)
    instance = _instance_with_filing_indicators("0010")

    class _ExplodingEngine:
        def __init__(self, _taxonomy) -> None:
            raise AssertionError("layout engine should not be used when filing indicators are available")

    monkeypatch.setattr(
        "bde_xbrl_editor.table_renderer.layout_engine.TableLayoutEngine",
        _ExplodingEngine,
    )

    panel = _InstancePanel()
    qtbot.addWidget(panel)
    presence = panel._compute_table_data_presence(instance, taxonomy, [table_with_data, empty_table])

    assert presence == {
        table_with_data.table_id: True,
        empty_table.table_id: False,
    }


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
def test_instance_panel_keeps_taxonomy_order_within_filled_and_empty_groups(
    qtbot, monkeypatch
) -> None:
    first_table = _table("es_tF1_11", "Coberturas", table_code="0011")
    second_table = _table("es_tF1_10", "Derivados", table_code="0010")
    taxonomy = _taxonomy_with_tables(first_table, second_table)
    instance = _instance_with_filing_indicators("0010")

    monkeypatch.setattr(
        _InstancePanel,
        "_compute_table_data_presence",
        staticmethod(lambda _instance, _taxonomy, _tables: {
            first_table.table_id: False,
            second_table.table_id: True,
        }),
    )

    panel = _InstancePanel()
    qtbot.addWidget(panel)
    panel.show()
    panel.populate(instance, taxonomy)

    assert panel._table_list.count() == 2
    assert "es_tF1_10" in panel._table_list.item(0).text()
    assert "Contains data" in panel._table_list.item(0).text()
    assert "es_tF1_11" in panel._table_list.item(1).text()
    assert "Empty" in panel._table_list.item(1).text()


@pytest.mark.qt
def test_instance_panel_groups_filled_tables_first_without_reordering_within_group(
    qtbot, monkeypatch
) -> None:
    first_filled = _table("es_tF1_20", "First filled", table_code="0020")
    second_filled = _table("es_tF1_10", "Second filled", table_code="0010")
    first_empty = _table("es_tF1_30", "First empty", table_code="0030")
    second_empty = _table("es_tF1_11", "Second empty", table_code="0011")
    taxonomy = _taxonomy_with_tables(first_filled, second_filled, first_empty, second_empty)
    instance = _instance_with_filing_indicators("0020", "0010")

    monkeypatch.setattr(
        _InstancePanel,
        "_compute_table_data_presence",
        staticmethod(lambda _instance, _taxonomy, _tables: {
            first_filled.table_id: True,
            second_filled.table_id: True,
            first_empty.table_id: False,
            second_empty.table_id: False,
        }),
    )

    panel = _InstancePanel()
    qtbot.addWidget(panel)
    panel.show()
    panel.populate(instance, taxonomy)

    assert panel._table_list.count() == 4
    texts = [panel._table_list.item(i).text() for i in range(panel._table_list.count())]
    assert "es_tF1_20" in texts[0]
    assert "es_tF1_10" in texts[1]
    assert "es_tF1_30" in texts[2]
    assert "es_tF1_11" in texts[3]


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
def test_taxonomy_view_shows_dummy_open_row_for_open_breakdown_table(qtbot) -> None:
    table = _open_row_table()
    taxonomy, _, _ = _taxonomy_with_open_row_dimension(table)

    view = XbrlTableView()
    qtbot.addWidget(view)
    view.resize(960, 640)
    view.show()
    view.set_table(table, taxonomy, None)

    assert view._layout is not None
    labels = [row[0].label for row in view._layout.row_header.levels]
    rendered_labels = [view._row_header._section_cells[i].label for i in range(len(view._row_header._section_cells))]
    rendered_texts = [view._row_header._section_cells[i].label if view._row_header._section_cells[i].rc_code is None else f"{view._row_header._section_cells[i].label} ({view._row_header._section_cells[i].rc_code})" for i in range(len(view._row_header._section_cells))]
    assert labels == ["Dynamic section", "Member A row", "Member B row", "Open row"]
    assert rendered_labels[-1] == "Open row"
    assert rendered_texts[-1] == "Open row (999)"


@pytest.mark.qt
def test_instance_view_can_add_dynamic_open_row(qtbot, monkeypatch) -> None:
    table = _open_row_table()
    taxonomy, _, member_c = _taxonomy_with_open_row_dimension(table)
    instance = _instance_for_open_rows()

    selections = iter([("Member C", True)])
    monkeypatch.setattr(
        "bde_xbrl_editor.ui.widgets.xbrl_table_view.QInputDialog.getItem",
        lambda *args, **kwargs: next(selections),
    )

    view = XbrlTableView()
    qtbot.addWidget(view)
    view.resize(960, 640)
    view.show()
    view.set_table(table, taxonomy, instance)

    qtbot.mouseClick(view._editing_switch, Qt.MouseButton.LeftButton)
    assert view._add_open_row_button.isHidden()

    model = view._body_view.model()
    assert model.setData(
        model.index(3, 0),
        "{http://example.com/mem}MemberC",
        Qt.ItemDataRole.EditRole,
    )

    assert view._layout is not None
    labels = [row[0].label for row in view._layout.row_header.levels]
    assert labels[:3] == ["Dynamic section", "Member A row", "Member B row"]
    assert labels[3] in {"Member C", "mem:MemberC"}
    assert (
        "{http://example.com/mem}MemberC"
        in view._open_row_members_by_table[table.table_id][view._open_row_candidates[0]["signature"]]
    )


@pytest.mark.qt
def test_instance_view_shows_open_rows_already_present_in_file(qtbot) -> None:
    table = _open_row_table()
    taxonomy, _, member_c = _taxonomy_with_open_row_dimension(table)
    instance = _instance_with_open_row_fact(member_c)

    view = XbrlTableView()
    qtbot.addWidget(view)
    view.resize(960, 640)
    view.show()
    view.set_table(table, taxonomy, instance)

    assert view._layout is not None
    labels = [row[0].label for row in view._layout.row_header.levels]
    assert labels[:3] == ["Dynamic section", "Member A row", "Member B row"]
    assert labels[3] in {"Member C", "mem:MemberC"}


@pytest.mark.qt
def test_instance_view_keeps_single_placeholder_open_row_when_no_dynamic_rows_exist(qtbot) -> None:
    table = _open_row_table()
    taxonomy, _, _ = _taxonomy_with_open_row_dimension(table)
    instance = _instance_for_open_rows()

    view = XbrlTableView()
    qtbot.addWidget(view)
    view.resize(960, 640)
    view.show()
    view.set_table(table, taxonomy, instance)

    assert view._layout is not None
    labels = [row[0].label for row in view._layout.row_header.levels]
    assert labels == ["Dynamic section", "Member A row", "Member B row", "Open row"]
    placeholder_rows = [row[0] for row in view._layout.row_header.levels if row[0].label == "Open row"]
    assert len(placeholder_rows) == 1
    assert placeholder_rows[0].rc_code == "999"


@pytest.mark.qt
def test_open_row_placeholder_includes_key_column_with_available_members(qtbot) -> None:
    table = _open_row_table()
    taxonomy, dim_qname, member_c = _taxonomy_with_open_row_dimension(table)
    instance = _instance_for_open_rows()

    view = XbrlTableView()
    qtbot.addWidget(view)
    view.resize(960, 640)
    view.show()
    view.set_table(table, taxonomy, instance)

    assert view._layout is not None
    assert view._layout.column_header.leaf_count == 2
    assert view._layout.column_header.levels[0][0].label == "Open dimension"

    placeholder_key_cell = view._layout.body[3][0]
    assert placeholder_key_cell.cell_kind == "open-key"
    assert placeholder_key_cell.open_key_dimension == dim_qname
    assert placeholder_key_cell.open_key_member is None
    assert placeholder_key_cell.open_key_options == (member_c,)

    model = view._body_view.model()
    index = model.index(3, 0)
    role_data = index.data(OPEN_KEY_ROLE)
    assert role_data is not None
    assert role_data["dimension"] == dim_qname
    assert role_data["options"] == (member_c,)


@pytest.mark.qt
def test_taxonomy_view_shows_placeholder_for_aspect_open_table(qtbot) -> None:
    table = _open_aspect_table()
    taxonomy, dim_qname, member_c = _taxonomy_with_open_row_dimension(table)

    view = XbrlTableView()
    qtbot.addWidget(view)
    view.resize(960, 640)
    view.show()
    view.set_table(table, taxonomy, None)

    assert view._layout is not None
    assert [row[0].label for row in view._layout.row_header.levels] == ["Open row"]
    assert view._layout.row_header.levels[0][0].rc_code == "999"
    assert view._layout.column_header.levels[0][0].label == "Open dimension"
    assert view._layout.body[0][0].cell_kind == "open-key"
    assert view._layout.body[0][0].open_key_dimension == dim_qname
    assert member_c in view._layout.body[0][0].open_key_options


@pytest.mark.qt
def test_aspect_open_rows_preserve_free_text_keys_from_stored_rows(qtbot) -> None:
    table = _mixed_open_aspect_table()
    taxonomy, typed_dim, explicit_dim, member_c = _taxonomy_with_mixed_open_row_dimensions(table)

    view = XbrlTableView()
    view._open_aspect_rows_by_table[table.table_id] = [  # noqa: SLF001
        {
            f"{{{typed_dim.namespace}}}{typed_dim.local_name}": "Entidad A",
            f"{{{explicit_dim.namespace}}}{explicit_dim.local_name}": (
                f"{{{member_c.namespace}}}{member_c.local_name}"
            ),
        }
    ]
    qtbot.addWidget(view)
    view.resize(960, 640)
    view.show()
    view.set_table(table, taxonomy, None)

    assert view._layout is not None
    assert view._layout.body[0][0].cell_kind == "open-key"
    assert view._layout.body[0][0].open_key_text == "Entidad A"
    assert view._layout.body[0][0].open_key_options == ()
    assert view._layout.body[0][1].open_key_member == member_c


@pytest.mark.qt
def test_refresh_instance_does_not_duplicate_open_key_columns(qtbot) -> None:
    table = _mixed_open_aspect_table()
    taxonomy, typed_dim, explicit_dim, member_c = _taxonomy_with_mixed_open_row_dimensions(table)

    view = XbrlTableView()
    view._open_aspect_rows_by_table[table.table_id] = [  # noqa: SLF001
        {
            f"{{{typed_dim.namespace}}}{typed_dim.local_name}": "Entidad A",
            f"{{{explicit_dim.namespace}}}{explicit_dim.local_name}": (
                f"{{{member_c.namespace}}}{member_c.local_name}"
            ),
        }
    ]
    qtbot.addWidget(view)
    view.resize(960, 640)
    view.show()
    view.set_table(table, taxonomy, _instance_for_open_rows())

    assert view._layout is not None
    initial_col_count = view._layout.column_header.leaf_count
    initial_headers = [cell.label for cell in view._layout.column_header.levels[0][:2]]

    view.refresh_instance(_instance_for_open_rows())

    assert view._layout is not None
    assert view._layout.column_header.leaf_count == initial_col_count
    assert [cell.label for cell in view._layout.column_header.levels[0][:2]] == initial_headers
    assert [cell.cell_kind for cell in view._layout.body[0][:2]] == ["open-key", "open-key"]


@pytest.mark.qt
def test_known_enum_fact_cells_publish_dropdown_options() -> None:
    from bde_xbrl_editor.taxonomy.models import Concept
    from bde_xbrl_editor.ui.widgets.xbrl_table_view import _apply_taxonomy_fact_options

    table = _table("es_tFI_40-1", "Table 40-1")
    concept = QName(namespace="http://example.com/met", local_name="qBVQ", prefix="met")
    concept_def = Concept(
        qname=concept,
        data_type=QName(namespace="http://www.xbrl.org/2003/instance", local_name="QNameItemType"),
        period_type="instant",
        enumeration_values=("eba_qSC:qx3", "eba_qSC:qx4"),
    )
    meta = TaxonomyMetadata(
        name="t",
        version="1",
        publisher="p",
        entry_point_path=Path("/tmp/x.xsd"),
        loaded_at=datetime.now(),
        declared_languages=("en",),
    )
    taxonomy = TaxonomyStructure(
        metadata=meta,
        concepts={concept: concept_def},
        labels=MagicMock(),
        presentation={},
        calculation={},
        definition={},
        hypercubes=(),
        dimensions={},
        tables=(),
    )
    body_cell = SimpleNamespace(
        row_index=0,
        col_index=0,
        coordinate=SimpleNamespace(concept=concept, explicit_dimensions={}),
        cell_kind="fact",
        fact_options=(),
    )
    layout = SimpleNamespace(table_id=table.table_id, body=[[body_cell]])

    updated = _apply_taxonomy_fact_options(layout, taxonomy=taxonomy)

    assert updated.body[0][0].fact_options == ("eba_qSC:qx3", "eba_qSC:qx4")


@pytest.mark.qt
def test_editing_open_row_key_creates_dynamic_row_coordinates(qtbot) -> None:
    table = _open_row_table()
    taxonomy, dim_qname, member_c = _taxonomy_with_open_row_dimension(table)
    instance = _instance_for_open_rows()

    view = XbrlTableView()
    qtbot.addWidget(view)
    view.resize(960, 640)
    view.show()
    view.set_table(table, taxonomy, instance)

    model = view._body_view.model()
    assert model.setData(
        model.index(3, 0),
        "{http://example.com/mem}MemberC",
        Qt.ItemDataRole.EditRole,
    )

    assert view._layout is not None
    labels = [row[0].label for row in view._layout.row_header.levels]
    assert labels[:3] == ["Dynamic section", "Member A row", "Member B row"]
    assert labels[3] in {"Member C", "mem:MemberC"}

    dynamic_key_cell = view._layout.body[3][0]
    dynamic_fact_cell = view._layout.body[3][1]
    assert dynamic_key_cell.cell_kind == "open-key"
    assert dynamic_key_cell.open_key_member == member_c
    assert dynamic_fact_cell.cell_kind == "fact"
    assert dynamic_fact_cell.coordinate.explicit_dimensions == {dim_qname: member_c}


@pytest.mark.qt
def test_editing_existing_open_row_key_migrates_fact_context(qtbot) -> None:
    table = _open_row_table()
    taxonomy, dim_qname, member_c = _taxonomy_with_open_row_dimension(table)
    member_d = QName(namespace="http://example.com/mem", local_name="MemberD", prefix="mem")
    dim_model = taxonomy.dimensions[dim_qname]
    taxonomy.dimensions[dim_qname] = DimensionModel(
        qname=dim_model.qname,
        dimension_type=dim_model.dimension_type,
        default_member=dim_model.default_member,
        domain=dim_model.domain,
        members=dim_model.members + (DomainMember(qname=member_d, parent=None, order=4.0),),
    )
    taxonomy.labels._mapping[member_d] = "Member D"  # type: ignore[attr-defined]  # noqa: SLF001
    instance = _editable_instance_with_open_row_fact(member_c)
    editor = InstanceEditor(instance)

    view = XbrlTableView()
    view.set_editor(editor)
    qtbot.addWidget(view)
    view.resize(960, 640)
    view.show()
    view.set_table(table, taxonomy, instance)

    model = view._body_view.model()
    assert model.setData(
        model.index(3, 0),
        "{http://example.com/mem}MemberD",
        Qt.ItemDataRole.EditRole,
    )

    assert len(instance.facts) == 1
    moved_fact = instance.facts[0]
    moved_context = instance.contexts[moved_fact.context_ref]
    assert moved_context.dimensions == {dim_qname: member_d}
    assert moved_fact.value == "10"
    assert instance.has_unsaved_changes


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
