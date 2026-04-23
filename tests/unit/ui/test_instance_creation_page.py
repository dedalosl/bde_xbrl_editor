"""Unit tests for the new-instance entity page behavior."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path

import pytest

pytest.importorskip("PySide6", reason="PySide6 not available - UI tests skipped")

from bde_xbrl_editor.instance.constants import BDE_DIM_NS
from bde_xbrl_editor.taxonomy.models import (
    BreakdownNode,
    DimensionModel,
    DomainMember,
    QName,
    TableDefinitionPWD,
    TaxonomyMetadata,
    TaxonomyStructure,
)
from bde_xbrl_editor.ui.widgets.instance_creation_wizard.page_entity_period import EntityPeriodPage


class _LabelResolverStub:
    def resolve(self, qname, **kwargs) -> str:
        return getattr(qname, "local_name", str(qname))


def _taxonomy_with_agrupacion() -> TaxonomyStructure:
    agrupacion_dim = QName(BDE_DIM_NS, "Agrupacion", prefix="es-be-cm-dim")
    agrupacion_member = QName(BDE_DIM_NS, "AgrupacionIndividual", prefix="es-be-cm-dim")
    breakdown = BreakdownNode(node_type="rule")
    return TaxonomyStructure(
        metadata=TaxonomyMetadata(
            name="Test",
            version="1.0",
            publisher="Test",
            entry_point_path=Path("tax.xsd"),
            loaded_at=datetime(2024, 1, 1),
            declared_languages=("es",),
        ),
        concepts={},
        labels=_LabelResolverStub(),
        presentation={},
        calculation={},
        definition={},
        hypercubes=[],
        dimensions={
            agrupacion_dim: DimensionModel(
                qname=agrupacion_dim,
                dimension_type="explicit",
                members=(
                    DomainMember(
                        qname=agrupacion_member,
                        parent=None,
                        order=1.0,
                        usable=True,
                    ),
                ),
            )
        },
        tables=[
            TableDefinitionPWD(
                table_id="T1",
                label="T1",
                extended_link_role="elr",
                x_breakdown=breakdown,
                y_breakdown=breakdown,
            )
        ],
    )


def test_prefilled_scheme_counts_towards_page_completion(qtbot) -> None:
    page = EntityPeriodPage(_taxonomy_with_agrupacion())
    qtbot.addWidget(page)

    assert page.isComplete() is False

    page._identifier_edit.setText("ES123")  # noqa: SLF001

    assert page._scheme_edit.text() == "http://www.ecb.int/stats/money/mfi"  # noqa: SLF001
    assert page.isComplete() is True
