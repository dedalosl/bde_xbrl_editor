"""Table body metadata tooltip presentation."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path

import pytest
from PySide6.QtCore import Qt

from bde_xbrl_editor.table_renderer.models import (
    BodyCell,
    CellCoordinate,
    ComputedTableLayout,
    HeaderGrid,
)
from bde_xbrl_editor.taxonomy.label_resolver import LabelResolver
from bde_xbrl_editor.taxonomy.models import (
    Concept,
    Label,
    QName,
    TaxonomyMetadata,
    TaxonomyStructure,
)
from bde_xbrl_editor.ui.widgets.table_body_model import TableBodyModel

_XBRLI = "http://www.xbrl.org/2003/instance"


def _taxonomy() -> TaxonomyStructure:
    metric = QName("http://example.com/met", "Amount", prefix="met")
    dim = QName("http://example.com/dim", "PortfolioAxis", prefix="dim")
    member = QName("http://example.com/mem", "Trading", prefix="mem")
    enum_a = QName("http://example.com/mem", "MemberA", prefix="mem")
    enum_b = QName("http://example.com/mem", "MemberB", prefix="mem")
    concepts = {
        metric: Concept(
            qname=metric,
            data_type=QName(_XBRLI, "QNameItemType"),
            period_type="instant",
            enumeration_values=("mem:MemberA", "mem:MemberB"),
        ),
        dim: Concept(qname=dim, data_type=QName(_XBRLI, "stringItemType"), period_type="instant"),
        member: Concept(qname=member, data_type=QName(_XBRLI, "stringItemType"), period_type="instant"),
        enum_a: Concept(qname=enum_a, data_type=QName(_XBRLI, "stringItemType"), period_type="instant"),
        enum_b: Concept(qname=enum_b, data_type=QName(_XBRLI, "stringItemType"), period_type="instant"),
    }
    labels = {
        metric: [Label("Importe en libros", "es", "http://www.xbrl.org/2003/role/label")],
        dim: [Label("Cartera", "es", "http://www.xbrl.org/2003/role/label")],
        member: [Label("Negociación", "es", "http://www.xbrl.org/2003/role/label")],
        enum_b: [Label("Opción B", "es", "http://www.xbrl.org/2003/role/label")],
    }
    return TaxonomyStructure(
        metadata=TaxonomyMetadata("t", "1", "p", Path("/tmp/t.xsd"), datetime.now(), ("es", "en")),
        concepts=concepts,
        labels=LabelResolver(labels, default_language_preference=["es", "en"]),
        presentation={},
        calculation={},
        definition={},
        hypercubes=(),
        dimensions={},
        tables=(),
    )


@pytest.mark.qt
def test_fact_tooltip_groups_metric_dimensions_and_allowed_values() -> None:
    taxonomy = _taxonomy()
    metric = QName("http://example.com/met", "Amount", prefix="met")
    dim = QName("http://example.com/dim", "PortfolioAxis", prefix="dim")
    member = QName("http://example.com/mem", "Trading", prefix="mem")
    layout = ComputedTableLayout(
        table_id="t",
        table_label="Table",
        column_header=HeaderGrid(levels=[[]], leaf_count=1, depth=0),
        row_header=HeaderGrid(levels=[[]], leaf_count=1, depth=0),
        z_members=[],
        active_z_index=0,
        body=[
            [
                BodyCell(
                    row_index=0,
                    col_index=0,
                    coordinate=CellCoordinate(concept=metric, explicit_dimensions={dim: member}),
                    fact_options=("mem:MemberA", "mem:MemberB"),
                )
            ]
        ],
    )
    model = TableBodyModel(layout)
    model.set_formatter(None, taxonomy)

    tooltip = model.data(model.index(0, 0), Qt.ItemDataRole.ToolTipRole)

    assert tooltip.startswith("<qt>")
    assert "Cell Information" in tooltip
    assert "Concept" in tooltip
    assert "Importe en libros" in tooltip
    assert "{http://example.com/met}Amount" in tooltip
    assert "Dimensions" in tooltip
    assert "Cartera" in tooltip
    assert "Negociación" in tooltip
    assert "Allowed Values" in tooltip
    assert "MemberA" in tooltip
    assert "Opción B" in tooltip


@pytest.mark.qt
def test_placeholder_tooltip_shows_open_dimension_allowed_values() -> None:
    taxonomy = _taxonomy()
    metric = QName("http://example.com/met", "Amount", prefix="met")
    dim = QName("http://example.com/dim", "PortfolioAxis", prefix="dim")
    member = QName("http://example.com/mem", "Trading", prefix="mem")
    layout = ComputedTableLayout(
        table_id="t",
        table_label="Table",
        column_header=HeaderGrid(levels=[[]], leaf_count=1, depth=0),
        row_header=HeaderGrid(levels=[[]], leaf_count=1, depth=0),
        z_members=[],
        active_z_index=0,
        body=[
            [
                BodyCell(
                    row_index=0,
                    col_index=0,
                    coordinate=CellCoordinate(concept=metric),
                    is_applicable=False,
                    cell_kind="placeholder",
                    open_dimension_info=(
                        {"dimension": dim, "options": (member,), "typed": False},
                    ),
                )
            ]
        ],
    )
    model = TableBodyModel(layout)
    model.set_formatter(None, taxonomy)

    tooltip = model.data(model.index(0, 0), Qt.ItemDataRole.ToolTipRole)

    assert tooltip.startswith("<qt>")
    assert "Concept" in tooltip
    assert "Importe en libros" in tooltip
    assert "Dimensions" in tooltip
    assert "Cartera" in tooltip
    assert "Negociación" in tooltip
    assert "{http://example.com/dim}PortfolioAxis" in tooltip
