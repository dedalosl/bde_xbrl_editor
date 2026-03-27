"""MultiLevelRowHeader — custom QHeaderView for Y-axis spanning headers."""

from __future__ import annotations

from typing import Any

from PySide6.QtCore import QRect, QSize, Qt
from PySide6.QtGui import QFont, QPainter
from PySide6.QtWidgets import QHeaderView, QWidget

from bde_xbrl_editor.table_renderer.models import HeaderGrid

_LEVEL_WIDTH = 120  # px per header level
_RC_FONT_SCALE = 0.75


class MultiLevelRowHeader(QHeaderView):
    """Custom vertical header that paints multi-level spanning row headers."""

    def __init__(self, header_grid: HeaderGrid | None = None, parent: QWidget | None = None) -> None:
        super().__init__(Qt.Orientation.Vertical, parent)
        self._grid: HeaderGrid | None = header_grid
        self.setDefaultSectionSize(24)
        self.setSectionResizeMode(QHeaderView.ResizeMode.Interactive)

    def set_header_grid(self, header_grid: HeaderGrid) -> None:
        self._grid = header_grid
        self.viewport().update()

    def sizeHint(self) -> QSize:
        if self._grid is None:
            return super().sizeHint()
        return QSize(self._grid.depth * _LEVEL_WIDTH, super().sizeHint().height())

    def paintSection(self, painter: QPainter, rect: QRect, logical_index: int) -> None:
        pass  # All painting in paintEvent

    def paintEvent(self, event: Any) -> None:
        if self._grid is None:
            super().paintEvent(event)
            return
        painter = QPainter(self.viewport())
        try:
            self._paint_all_levels(painter)
        finally:
            painter.end()

    def _paint_all_levels(self, painter: QPainter) -> None:
        if self._grid is None:
            return

        # Build cumulative row y-offsets
        leaf_y_offsets: list[int] = []
        y = 0
        for i in range(self.count()):
            leaf_y_offsets.append(y)
            y += self.sectionSize(i)

        for level_idx, cells in enumerate(self._grid.levels):
            x = level_idx * _LEVEL_WIDTH
            leaf_cursor = 0
            for cell in cells:
                if leaf_cursor >= len(leaf_y_offsets):
                    break
                y_start = leaf_y_offsets[leaf_cursor]
                height = sum(
                    self.sectionSize(leaf_cursor + k)
                    for k in range(cell.span)
                    if leaf_cursor + k < self.count()
                )
                rect = QRect(x, y_start, _LEVEL_WIDTH, height)

                painter.fillRect(rect, self.palette().window())
                painter.setPen(self.palette().mid().color())
                painter.drawRect(rect.adjusted(0, 0, -1, -1))

                painter.setPen(self.palette().windowText().color())
                if cell.rc_code:
                    label_rect = QRect(x + 2, y_start + 2, _LEVEL_WIDTH - 4, height // 2 - 2)
                    rc_rect = QRect(x + 2, y_start + height // 2, _LEVEL_WIDTH - 4, height // 2 - 2)
                    painter.drawText(label_rect, Qt.AlignmentFlag.AlignCenter | Qt.AlignmentFlag.AlignVCenter, cell.label)
                    rc_font = QFont(painter.font())
                    rc_font.setPointSizeF(rc_font.pointSizeF() * _RC_FONT_SCALE)
                    painter.setFont(rc_font)
                    painter.drawText(rc_rect, Qt.AlignmentFlag.AlignCenter, cell.rc_code)
                    painter.setFont(QFont())
                else:
                    inner_rect = rect.adjusted(2, 2, -2, -2)
                    painter.drawText(
                        inner_rect,
                        Qt.AlignmentFlag.AlignCenter | Qt.AlignmentFlag.AlignVCenter,
                        cell.label,
                    )

                if not cell.is_leaf:
                    leaf_cursor += cell.span
                else:
                    leaf_cursor += 1
