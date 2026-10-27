"""Integer editing rejects invalid input without modifying existing facts."""

from datetime import date, datetime
from pathlib import Path
from types import SimpleNamespace

import pytest
from PySide6.QtGui import QStandardItemModel
from PySide6.QtWidgets import QLineEdit

from bde_xbrl_editor.instance.models import (
    Fact,
    ReportingEntity,
    ReportingPeriod,
    XbrlContext,
    XbrlInstance,
)
from bde_xbrl_editor.table_renderer.models import BodyCell, CellCoordinate
from bde_xbrl_editor.taxonomy.models import Concept, QName, TaxonomyMetadata, TaxonomyStructure
from bde_xbrl_editor.ui.instance_editor_adapter import InstanceEditorAdapter
from bde_xbrl_editor.ui.widgets.cell_edit_delegate import CellEditDelegate


@pytest.mark.parametrize("submitted", ["12.9", "12.bad", "-1.5", "12,9", "1,234"])
def test_invalid_integer_edit_preserves_fact_and_clean_state(qtbot, submitted: str) -> None:
    concept = QName("urn:test", "Count")
    taxonomy = TaxonomyStructure(
        metadata=TaxonomyMetadata("Test", "1", "Test", Path("test.xsd"), datetime.now(), ("en",)),
        concepts={
            concept: Concept(
                concept, QName("http://www.xbrl.org/2003/instance", "integerItemType"), "instant"
            )
        },
        labels=None,
        presentation={},
        calculation={},
        definition={},
        hypercubes=(),
        dimensions={},
        tables=(),
    )
    entity = ReportingEntity("entity", "urn:entity")
    period = ReportingPeriod("instant", instant_date=date(2026, 1, 1))
    fact = Fact(concept, "c", None, "42")
    instance = XbrlInstance(
        Path("test.xsd"),
        "test.xsd",
        entity,
        period,
        contexts={"c": XbrlContext("c", entity, period)},
        facts=[fact],
        _dirty=False,
    )
    adapter = InstanceEditorAdapter(instance)
    changes = []
    adapter.changes_made.connect(lambda: changes.append(True))
    layout = SimpleNamespace(body=[[BodyCell(0, 0, CellCoordinate(concept=concept))]])
    delegate = CellEditDelegate(taxonomy, adapter, layout)
    model = QStandardItemModel(1, 1)
    widget = QLineEdit(submitted)
    qtbot.addWidget(widget)

    delegate.setModelData(widget, model, model.index(0, 0))

    assert instance.facts == [fact]
    assert instance.facts[0] is fact
    assert fact.value == "42"
    assert not instance.has_unsaved_changes
    assert instance.edit_history == []
    assert changes == []
    assert id(widget) in delegate._invalid_editors
