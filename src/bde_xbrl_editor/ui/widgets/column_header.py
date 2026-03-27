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
        """Paint a single column section — overridden to suppress default painting.

        We handle all painting in paintEvent via the grid.
        """
        # Suppress the default single-row paint; all done in paintEvent
        pass

    def paintEvent(self, event: Any) -> None:
        """Paint all header levels with correct spanning."""
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

        # Build cumulative leaf widths map: leaf_index → x_offset
        # We use the visible section widths
        leaf_x_offsets: list[int] = []
        x = 0
        for i in range(self.count()):
            leaf_x_offsets.append(x)
            x += self.sectionSize(i)

        # For each level, paint each HeaderCell
        for level_idx, cells in enumerate(self._grid.levels):
            y = level_idx * _LEVEL_HEIGHT
            leaf_cursor = 0
            for cell in cells:
                if leaf_cursor >= len(leaf_x_offsets):
                    break
                x_start = leaf_x_offsets[leaf_cursor]
                # Width = sum of section sizes for span
                width = sum(
                    self.sectionSize(leaf_cursor + k)
                    for k in range(cell.span)
                    if leaf_cursor + k < self.count()
                )
                rect = QRect(x_start, y, width, _LEVEL_HEIGHT)

                # Draw cell background + border
                painter.fillRect(rect, self.palette().window())
                painter.setPen(self.palette().mid().color())
                painter.drawRect(rect.adjusted(0, 0, -1, -1))

                # Draw label
                painter.setPen(self.palette().windowText().color())
                if cell.rc_code:
                    # Draw main label in upper portion, RC code below
                    label_rect = QRect(x_start + 2, y + 2, width - 4, _LEVEL_HEIGHT // 2 - 2)
                    rc_rect = QRect(x_start + 2, y + _LEVEL_HEIGHT // 2, width - 4, _LEVEL_HEIGHT // 2 - 2)
                    painter.drawText(label_rect, Qt.AlignmentFlag.AlignCenter, cell.label)
                    rc_font = QFont(painter.font())
                    rc_font.setPointSizeF(rc_font.pointSizeF() * _RC_FONT_SCALE)
                    painter.setFont(rc_font)
                    painter.drawText(rc_rect, Qt.AlignmentFlag.AlignCenter, cell.rc_code)
                    painter.setFont(QFont())  # reset
                else:
                    inner_rect = rect.adjusted(2, 2, -2, -2)
                    painter.drawText(inner_rect, Qt.AlignmentFlag.AlignCenter, cell.label)

                if not cell.is_leaf:
                    leaf_cursor += cell.span
                else:
                    leaf_cursor += 1
