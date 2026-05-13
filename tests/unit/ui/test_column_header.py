"""Regression tests for custom column header scrolling behaviour."""

from __future__ import annotations

import os

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

pytest.importorskip("PySide6", reason="PySide6 not available - UI tests skipped")

from PySide6.QtCore import QRect
from PySide6.QtGui import QPainter, QPixmap

from bde_xbrl_editor.table_renderer.models import HeaderCell, HeaderGrid
from bde_xbrl_editor.ui.widgets.column_header import MultiLevelColumnHeader


class _HeaderProbe(MultiLevelColumnHeader):
    def __init__(self, positions: list[int], sizes: list[int]) -> None:
        super().__init__()
        self._positions = positions
        self._sizes = sizes
        self.painted: list[tuple[QRect, QRect]] = []
        self.resize(300, 80)

    def count(self) -> int:  # type: ignore[override]
        return len(self._sizes)

    def sectionViewportPosition(self, logical_index: int) -> int:  # type: ignore[override]
        return self._positions[logical_index]

    def sectionSize(self, logical_index: int) -> int:  # type: ignore[override]
        return self._sizes[logical_index]

    def _paint_cell(self, painter, rect, *args, **kwargs) -> None:  # type: ignore[override]
        self.painted.append((QRect(rect), painter.clipBoundingRect().toAlignedRect()))


def _grid_with_one_span(span: int = 4) -> HeaderGrid:
    cell = HeaderCell(
        label="Spanned column",
        rc_code=None,
        span=span,
        level=0,
        is_leaf=False,
        is_abstract=False,
        source_node=object(),
    )
    return HeaderGrid(levels=[[cell]], leaf_count=span, depth=1, ordered_leaves=[])


def _paint_section(header: _HeaderProbe, logical_index: int) -> None:
    pixmap = QPixmap(300, 80)
    pixmap.fill()
    painter = QPainter(pixmap)
    try:
        x = header.sectionViewportPosition(logical_index)
        width = header.sectionSize(logical_index)
        header.paintSection(painter, QRect(x, 0, width, 80), logical_index)
    finally:
        painter.end()


def test_spanned_header_paints_visible_slice_when_start_is_offscreen(
    qtbot,
    qapp,
) -> None:
    header = _HeaderProbe(positions=[-240, -120, 0, 120], sizes=[120, 120, 120, 120])
    qtbot.addWidget(header)
    header.set_header_grid(_grid_with_one_span())
    header.show()

    _paint_section(header, 2)

    assert header.painted
    cell_rect, clip_rect = header.painted[-1]
    assert cell_rect.x() == -240
    assert cell_rect.width() == 480
    assert clip_rect == QRect(0, 0, 120, cell_rect.height())


def test_spanned_header_paints_following_visible_slices_when_start_is_visible(
    qtbot,
    qapp,
) -> None:
    header = _HeaderProbe(positions=[0, 120, 240, 360], sizes=[120, 120, 120, 120])
    qtbot.addWidget(header)
    header.set_header_grid(_grid_with_one_span())
    header.show()

    _paint_section(header, 1)

    assert header.painted
    cell_rect, clip_rect = header.painted[-1]
    assert cell_rect.x() == 0
    assert cell_rect.width() == 480
    assert clip_rect == QRect(120, 0, 120, cell_rect.height())
