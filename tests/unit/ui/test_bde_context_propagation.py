"""Regression tests for BDE report-level Agrupacion propagation in UI context creation."""

from __future__ import annotations

from datetime import date
from pathlib import Path

from bde_xbrl_editor.instance.constants import BDE_DIM_NS
from bde_xbrl_editor.instance.context_builder import build_dimensional_context
from bde_xbrl_editor.instance.models import Fact, ReportingEntity, ReportingPeriod, XbrlInstance
from bde_xbrl_editor.table_renderer.models import CellCoordinate
from bde_xbrl_editor.taxonomy.models import QName
from bde_xbrl_editor.ui.widgets.cell_edit_delegate import _ensure_context_ref, _find_fact_index
from bde_xbrl_editor.ui.widgets.xbrl_table_view import _ensure_context_ref_for_dimensions


def _entity() -> ReportingEntity:
    return ReportingEntity(identifier="ES0001", scheme="http://www.bde.es/")


def _period() -> ReportingPeriod:
    return ReportingPeriod(period_type="instant", instant_date=date(2024, 12, 31))


def _instance_with_agrupacion() -> tuple[XbrlInstance, QName, QName]:
    agrupacion_dim = QName(BDE_DIM_NS, "Agrupacion", prefix="es-be-cm-dim")
    agrupacion_member = QName(
        BDE_DIM_NS,
        "AgrupacionIndividual",
        prefix="es-be-cm-dim",
    )
    base_context = build_dimensional_context(
        _entity(),
        _period(),
        {agrupacion_dim: agrupacion_member},
        context_element="scenario",
        dim_containers={agrupacion_dim: "segment"},
    )
    instance = XbrlInstance(
        taxonomy_entry_point=Path("tax.xsd"),
        schema_ref_href="http://www.bde.es/example.xsd",
        entity=_entity(),
        period=_period(),
        contexts={base_context.context_id: base_context},
        facts=[],
    )
    return instance, agrupacion_dim, agrupacion_member


def test_ensure_context_ref_preserves_agrupacion_on_new_fact_context() -> None:
    instance, agrupacion_dim, agrupacion_member = _instance_with_agrupacion()
    row_dim = QName("http://example.com/dim", "RowAxis", prefix="dim")
    row_member = QName("http://example.com/mem", "RowMember", prefix="mem")

    context_ref = _ensure_context_ref(
        instance,
        CellCoordinate(
            concept=QName("http://example.com/met", "Metric", prefix="met"),
            explicit_dimensions={row_dim: row_member},
        ),
    )

    created_context = instance.contexts[context_ref]
    assert created_context.dimensions[agrupacion_dim] == agrupacion_member
    assert created_context.dim_containers[agrupacion_dim] == "segment"
    assert created_context.dimensions[row_dim] == row_member


def test_find_fact_index_ignores_report_level_agrupacion() -> None:
    instance, agrupacion_dim, agrupacion_member = _instance_with_agrupacion()
    concept = QName("http://example.com/met", "Metric", prefix="met")
    row_dim = QName("http://example.com/dim", "RowAxis", prefix="dim")
    row_member = QName("http://example.com/mem", "RowMember", prefix="mem")
    fact_context = build_dimensional_context(
        instance.entity,
        instance.period,
        {
            agrupacion_dim: agrupacion_member,
            row_dim: row_member,
        },
        context_element="scenario",
        dim_containers={
            agrupacion_dim: "segment",
            row_dim: "scenario",
        },
    )
    instance.contexts[fact_context.context_id] = fact_context
    instance.facts.append(
        Fact(
            concept=concept,
            context_ref=fact_context.context_id,
            unit_ref=None,
            value="10",
        )
    )

    match_index = _find_fact_index(
        instance,
        CellCoordinate(
            concept=concept,
            explicit_dimensions={row_dim: row_member},
        ),
    )

    assert match_index == 0


def test_ensure_context_ref_for_dimensions_preserves_agrupacion() -> None:
    instance, agrupacion_dim, agrupacion_member = _instance_with_agrupacion()
    z_dim = QName("http://example.com/dim", "ZAxis", prefix="dim")
    z_member = QName("http://example.com/mem", "ZMember", prefix="mem")

    context_ref = _ensure_context_ref_for_dimensions(
        instance,
        dimensions={z_dim: z_member},
        context_element="scenario",
    )

    created_context = instance.contexts[context_ref]
    assert created_context.dimensions[agrupacion_dim] == agrupacion_member
    assert created_context.dim_containers[agrupacion_dim] == "segment"
    assert created_context.dimensions[z_dim] == z_member
