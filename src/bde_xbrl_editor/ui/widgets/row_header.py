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
        """Paint all header levels for this row section.

        For spanning cells we paint the full-height cell only when we are at
        the top-most logical index of that span, so each cell is drawn once.
        """
        if self._grid is None:
            super().paintSection(painter, rect, logical_index)
            return

        painter.save()
        painter.setClipping(False)

        for level_idx, cells in enumerate(self._grid.levels):
            x = level_idx * _LEVEL_WIDTH
            leaf_cursor = 0
            for cell in cells:
                span = 1 if cell.is_leaf else cell.span
                span_end = leaf_cursor + span

                if leaf_cursor <= logical_index < span_end:
                    if logical_index == leaf_cursor:
                        y_start = self.sectionViewportPosition(leaf_cursor)
                        full_height = sum(
                            self.sectionSize(leaf_cursor + k)
                            for k in range(span)
                            if leaf_cursor + k < self.count()
                        )
                        cell_rect = QRect(x, y_start, _LEVEL_WIDTH, full_height)
                        self._paint_cell(painter, cell_rect, cell)
                    break

                leaf_cursor += span

        painter.restore()

    def _paint_cell(self, painter: QPainter, rect: QRect, cell: Any) -> None:
        painter.fillRect(rect, self.palette().window())
        painter.setPen(self.palette().mid().color())
        painter.drawRect(rect.adjusted(0, 0, -1, -1))
        painter.setPen(self.palette().windowText().color())

        if cell.rc_code:
            label_rect = QRect(rect.x() + 2, rect.y() + 2, _LEVEL_WIDTH - 4, rect.height() // 2 - 2)
            rc_rect = QRect(rect.x() + 2, rect.y() + rect.height() // 2, _LEVEL_WIDTH - 4, rect.height() // 2 - 2)
            painter.drawText(
                label_rect,
                Qt.AlignmentFlag.AlignCenter | Qt.AlignmentFlag.AlignVCenter,
                cell.label,
            )
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
