"""MultiLevelColumnHeader — custom QHeaderView for X-axis spanning headers."""

from __future__ import annotations

from typing import Any

from PySide6.QtCore import QRect, QSize, Qt
from PySide6.QtGui import QFont, QPainter
from PySide6.QtWidgets import QHeaderView, QWidget

from bde_xbrl_editor.table_renderer.models import HeaderGrid

_LEVEL_HEIGHT = 28  # px per header level
_RC_FONT_SCALE = 0.75  # scale factor for RC code font


class MultiLevelColumnHeader(QHeaderView):
    """Custom horizontal header that paints multi-level spanning column headers."""

    def __init__(self, header_grid: HeaderGrid | None = None, parent: QWidget | None = None) -> None:
        super().__init__(Qt.Orientation.Horizontal, parent)
        self._grid: HeaderGrid | None = header_grid
        self.setDefaultSectionSize(80)
        self.setSectionResizeMode(QHeaderView.ResizeMode.Interactive)

    def set_header_grid(self, header_grid: HeaderGrid) -> None:
        """Update the header grid and repaint."""
        self._grid = header_grid
        self.viewport().update()

    def sizeHint(self) -> QSize:
        if self._grid is None:
            return super().sizeHint()
        return QSize(super().sizeHint().width(), self._grid.depth * _LEVEL_HEIGHT)

    def paintSection(self, painter: QPainter, rect: QRect, logical_index: int) -> None:
        """Paint all header levels for this column section.

        For spanning cells we paint the full-width cell only when we are at
        the left-most logical index of that span, so each cell is drawn once.
        """
        if self._grid is None:
            super().paintSection(painter, rect, logical_index)
            return

        painter.save()
        painter.setClipping(False)

        for level_idx, cells in enumerate(self._grid.levels):
            y = level_idx * _LEVEL_HEIGHT
            leaf_cursor = 0
            for cell in cells:
                span = 1 if cell.is_leaf else cell.span
                span_end = leaf_cursor + span

                if leaf_cursor <= logical_index < span_end:
                    # Only paint from the leftmost section of this span
                    if logical_index == leaf_cursor:
                        x_start = self.sectionViewportPosition(leaf_cursor)
                        full_width = sum(
                            self.sectionSize(leaf_cursor + k)
                            for k in range(span)
                            if leaf_cursor + k < self.count()
                        )
                        cell_rect = QRect(x_start, y, full_width, _LEVEL_HEIGHT)
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
            label_rect = QRect(rect.x() + 2, rect.y() + 2, rect.width() - 4, _LEVEL_HEIGHT // 2 - 2)
            rc_rect = QRect(rect.x() + 2, rect.y() + _LEVEL_HEIGHT // 2, rect.width() - 4, _LEVEL_HEIGHT // 2 - 2)
            painter.drawText(label_rect, Qt.AlignmentFlag.AlignCenter, cell.label)
            rc_font = QFont(painter.font())
            rc_font.setPointSizeF(rc_font.pointSizeF() * _RC_FONT_SCALE)
            painter.setFont(rc_font)
            painter.drawText(rc_rect, Qt.AlignmentFlag.AlignCenter, cell.rc_code)
            painter.setFont(QFont())
        else:
            inner_rect = rect.adjusted(2, 2, -2, -2)
            painter.drawText(inner_rect, Qt.AlignmentFlag.AlignCenter, cell.label)
