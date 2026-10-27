"""Regression tests for row-header text sizing across platform fonts."""

from __future__ import annotations

import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest

pytest.importorskip("PySide6", reason="PySide6 not available - UI tests skipped")

from PySide6.QtCore import Qt
from PySide6.QtGui import QFont, QFontMetrics, QStandardItemModel
from PySide6.QtWidgets import QHeaderView

from bde_xbrl_editor.table_renderer.models import HeaderCell, HeaderGrid
from bde_xbrl_editor.ui.widgets.row_header import MultiLevelRowHeader, _label_font


def test_row_height_accounts_for_wrapping_at_actual_width_and_font(qtbot, qapp) -> None:
    label = "Pasivos financieros mantenidos para negociar (0010)"
    cell = HeaderCell(
        label=label,
        rc_code=None,
        span=1,
        level=0,
        is_leaf=True,
        is_abstract=False,
        source_node=object(),
    )
    grid = HeaderGrid(levels=[[cell]], leaf_count=1, depth=1)
    header = MultiLevelRowHeader()
    qtbot.addWidget(header)
    header.setModel(QStandardItemModel(1, 1, header))
    header.setSectionResizeMode(QHeaderView.ResizeMode.Interactive)
    header.resize(150, 100)
    header.setFont(QFont("Arial", 16))

    header.set_header_grid(grid)

    available_width = header.width() - (4 + 10) - 6
    metrics = QFontMetrics(header.font())
    expected_text_height = metrics.boundingRect(
        0,
        0,
        available_width,
        10000,
        int(Qt.AlignmentFlag.AlignLeft | Qt.TextFlag.TextWordWrap),
        label,
    ).height()

    assert header.sectionSize(0) >= expected_text_height + 12


def test_pixel_sized_stylesheet_font_is_not_promoted_to_point_size() -> None:
    font = QFont("Arial")
    font.setPixelSize(12)

    result = _label_font(font)

    assert result.pixelSize() == 12
