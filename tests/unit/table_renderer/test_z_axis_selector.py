"""Unit tests for the per-dimension ZAxisSelector widget."""

from __future__ import annotations

import pytest

pytest.importorskip("PySide6", reason="PySide6 not available - selector tests skipped")

from PySide6.QtCore import Qt

from bde_xbrl_editor.taxonomy.models import QName
from bde_xbrl_editor.ui.widgets.z_axis_selector import (
    ZAxisDimension,
    ZAxisOption,
    ZAxisSelector,
)


def _qname(local_name: str) -> QName:
    return QName(namespace="http://example.com", local_name=local_name, prefix="ex")


@pytest.mark.qt
class TestZAxisSelector:
    def test_hidden_for_no_dimensions(self, qtbot) -> None:
        widget = ZAxisSelector([])
        qtbot.addWidget(widget)
        assert not widget.isVisible()

    def test_emits_dimension_assignments_on_change(self, qtbot) -> None:
        dim = _qname("DimZ")
        member_a = _qname("MemberA")
        member_b = _qname("MemberB")

        widget = ZAxisSelector(
            [
                ZAxisDimension(
                    dimension_qname=dim,
                    label="Dim Z",
                    options=(
                        ZAxisOption(member_qname=member_a, label="Member A", is_used=True),
                        ZAxisOption(member_qname=member_b, label="Member B"),
                    ),
                    selected_member=member_a,
                )
            ]
        )
        qtbot.addWidget(widget)
        widget.show()

        combo = widget._combo_by_dimension[dim]
        with qtbot.waitSignal(widget.z_selection_changed, timeout=1000) as blocker:
            combo.setCurrentIndex(1)

        assert blocker.args[0] == {dim: member_b}

    def test_valid_combinations_filter_other_dimension_options(self, qtbot) -> None:
        dim_country = _qname("Country")
        dim_currency = _qname("Currency")
        es = _qname("ES")
        pt = _qname("PT")
        eur = _qname("EUR")
        usd = _qname("USD")

        widget = ZAxisSelector(
            [
                ZAxisDimension(
                    dimension_qname=dim_country,
                    label="Country",
                    options=(
                        ZAxisOption(member_qname=es, label="Spain", is_used=True),
                        ZAxisOption(member_qname=pt, label="Portugal"),
                    ),
                    selected_member=es,
                ),
                ZAxisDimension(
                    dimension_qname=dim_currency,
                    label="Currency",
                    options=(
                        ZAxisOption(member_qname=eur, label="Euro", is_used=True),
                        ZAxisOption(member_qname=usd, label="US Dollar"),
                    ),
                    selected_member=eur,
                ),
            ],
            valid_combinations=[
                {dim_country: es, dim_currency: eur},
                {dim_country: pt, dim_currency: eur},
                {dim_country: pt, dim_currency: usd},
            ],
        )
        qtbot.addWidget(widget)
        widget.show()

        country_combo = widget._combo_by_dimension[dim_country]
        currency_combo = widget._combo_by_dimension[dim_currency]

        assert currency_combo.count() == 1
        assert currency_combo.itemData(0) == eur

        country_combo.setCurrentIndex(1)
        qtbot.waitUntil(lambda: currency_combo.count() == 2, timeout=1000)
        assert currency_combo.itemData(0) == eur
        assert currency_combo.itemData(1) == usd

    def test_unused_options_are_dimmed(self, qtbot) -> None:
        dim = _qname("DimZ")
        used = _qname("Used")
        unused = _qname("Unused")

        widget = ZAxisSelector(
            [
                ZAxisDimension(
                    dimension_qname=dim,
                    label="Dim Z",
                    options=(
                        ZAxisOption(member_qname=used, label="Used", is_used=True),
                        ZAxisOption(member_qname=unused, label="Unused", is_used=False),
                    ),
                    selected_member=used,
                )
            ]
        )
        qtbot.addWidget(widget)
        widget.show()

        combo = widget._combo_by_dimension[dim]
        used_color = combo.itemData(0, Qt.ItemDataRole.ForegroundRole)
        unused_color = combo.itemData(1, Qt.ItemDataRole.ForegroundRole)

        assert used_color != unused_color
