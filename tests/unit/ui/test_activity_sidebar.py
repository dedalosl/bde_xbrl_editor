"""Unit tests for formula detail formatting in the activity sidebar."""

from __future__ import annotations

from decimal import Decimal

import pytest

from bde_xbrl_editor.taxonomy.models import (
    BooleanFilterDefinition,
    ConsistencyAssertionDefinition,
    DimensionFilter,
    FactVariableDefinition,
    QName,
    XPathFilterDefinition,
)
from bde_xbrl_editor.validation.formula.details import (
    format_assertion_expression,
    format_assertion_type,
    format_operand_details,
)
from bde_xbrl_editor.validation.models import ValidationSeverity

_TAX_NS = "http://example.com/tax"


def _qn(local: str) -> QName:
    return QName(namespace=_TAX_NS, local_name=local, prefix="tax")


def test_format_operand_details_includes_filters_and_fallback() -> None:
    operand = FactVariableDefinition(
        variable_name="a",
        concept_filter=_qn("Amount"),
        period_filter="instant",
        dimension_filters=(
            DimensionFilter(
                dimension_qname=_qn("dim"),
                member_qnames=(_qn("member"),),
            ),
        ),
        fallback_value="0",
        xpath_filters=(
            XPathFilterDefinition(xpath_expr="$a > 0"),
        ),
        boolean_filters=(
            BooleanFilterDefinition(
                filter_type="and",
                children=(
                    DimensionFilter(
                        dimension_qname=_qn("otherDim"),
                        member_qnames=(_qn("otherMember"),),
                        exclude=True,
                    ),
                ),
            ),
        ),
    )

    text = format_operand_details((operand,))

    assert "$a" in text
    assert "concept: tax:Amount" in text
    assert "period: instant" in text
    assert "dimension: tax:dim = tax:member" in text
    assert "xpath: $a > 0" in text
    assert "boolean: (tax:otherDim != tax:otherMember)" in text
    assert "fallback: 0" in text


def test_format_operand_details_handles_unfiltered_variable() -> None:
    operand = FactVariableDefinition(variable_name="b")

    text = format_operand_details((operand,))

    assert text == "$b\n  matches: any fact"


def test_format_assertion_expression_includes_consistency_radius() -> None:
    assertion = ConsistencyAssertionDefinition(
        assertion_id="CA001",
        label=None,
        severity=ValidationSeverity.ERROR,
        abstract=False,
        variables=(),
        precondition_xpath=None,
        formula_xpath="$a + $b",
        absolute_radius=Decimal("0.5"),
    )

    text = format_assertion_expression(assertion)

    assert "$a + $b" in text
    assert "absolute radius: 0.5" in text
    assert format_assertion_type(assertion) == "Consistency Assertion"


@pytest.mark.qt
def test_activity_sidebar_merges_taxonomy_panels_into_tax_button(qtbot):
    from bde_xbrl_editor.ui.widgets.activity_sidebar import ActivitySidebar
    from tests.unit.ui.test_main_window_loader_flow import _taxonomy

    sidebar = ActivitySidebar(_taxonomy())
    qtbot.addWidget(sidebar)
    sidebar.show()

    assert [btn.text() for btn in sidebar._buttons] == ["TAX", "TAB", "VAL", "INS"]
    assert sidebar._buttons[0].accessibleName() == "Taxonomy"
    assert sidebar._stack.count() == 4


@pytest.mark.qt
def test_activity_sidebar_can_limit_visible_panels(qtbot):
    from bde_xbrl_editor.ui.widgets.activity_sidebar import ActivitySidebar
    from tests.unit.ui.test_main_window_loader_flow import _taxonomy

    sidebar = ActivitySidebar(_taxonomy(), visible_indexes=(1, 2), initial_index=1)
    qtbot.addWidget(sidebar)
    sidebar.show()

    visible = [btn.text() for btn in sidebar._buttons if not btn.isHidden()]
    assert visible == ["TAB", "VAL"]
    assert sidebar._active_index == 1


@pytest.mark.qt
def test_activity_sidebar_loads_validation_panel_lazily(qtbot, monkeypatch):
    from PySide6.QtWidgets import QWidget

    from bde_xbrl_editor.ui.widgets.activity_sidebar import ActivitySidebar
    from tests.unit.ui.test_main_window_loader_flow import _taxonomy

    created: list[str] = []

    class _FakeValidationsPanel(QWidget):
        def __init__(self, _taxonomy, parent=None) -> None:
            super().__init__(parent)
            created.append("created")

    monkeypatch.setattr(
        "bde_xbrl_editor.ui.widgets.activity_sidebar._ValidationsPanel",
        _FakeValidationsPanel,
    )

    sidebar = ActivitySidebar(_taxonomy(), visible_indexes=(1, 2), initial_index=1)
    qtbot.addWidget(sidebar)

    assert created == []

    sidebar._activate(2)

    assert created == ["created"]
