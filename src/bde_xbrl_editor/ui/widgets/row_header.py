"""MultiLevelRowHeader — custom QHeaderView for Y-axis spanning headers."""

from __future__ import annotations

from typing import Any

from PySide6.QtCore import QRect, QSize, Qt
from PySide6.QtGui import QColor, QFont, QPainter
from PySide6.QtWidgets import QHeaderView, QWidget

from bde_xbrl_editor.table_renderer.models import HeaderGrid

_LEVEL_WIDTH = 140   # px per header level
_ROW_HEIGHT_MIN = 26 # minimum px per data row
_ROW_HEIGHT_PAD = 10 # total vertical padding (top + bottom) within a row
_RC_FONT_SCALE = 0.72
_LABEL_SPLIT = 0.62  # fraction of cell height allocated to label when rc_code present
_MIN_LABEL_PT = 9    # minimum point size for label text
_MIN_RC_PT = 8       # minimum point size for rc_code text

# Color palette — matching column header navy theme
_BG_LEAF = QColor("#EEF3FA")       # very light blue for leaf rows
_BG_SPAN = QColor("#DCE8F5")       # slightly darker for group rows
_BG_SPAN_OUTER = QColor("#C8D9EE") # darkest for outermost groups
_TEXT_MAIN = QColor("#1E3A5F")     # deep navy text
_TEXT_RC = QColor("#5A7FA8")       # muted blue for RC codes
_BORDER = QColor("#B8CCDE")        # soft blue-gray border
_BORDER_RIGHT = QColor("#2B5287")  # strong right border (separates from body)

_WRAP = int(Qt.AlignmentFlag.AlignLeft | Qt.TextFlag.TextWordWrap)


class MultiLevelRowHeader(QHeaderView):
    """Custom vertical header that paints multi-level spanning row headers."""

    def __init__(self, header_grid: HeaderGrid | None = None, parent: QWidget | None = None) -> None:
        super().__init__(Qt.Orientation.Vertical, parent)
        self._grid: HeaderGrid | None = header_grid
        self._col_font_pts: list[float] = []
        self.setDefaultSectionSize(_ROW_HEIGHT_MIN)
        self.setSectionResizeMode(QHeaderView.ResizeMode.Interactive)

    def set_header_grid(self, header_grid: HeaderGrid) -> None:
        self._grid = header_grid
        self._auto_size_sections()
        self._col_font_pts = self._compute_column_font_pts()
        self.viewport().update()

    # ------------------------------------------------------------------
    # Section sizing + per-column font normalisation
    # ------------------------------------------------------------------

    def _auto_size_sections(self) -> None:
        """Resize each leaf row section to fit its label text at the base font."""
        if self._grid is None or not self._grid.levels:
            return

        fm = self.fontMetrics()
        text_w = _LEVEL_WIDTH - 12
        rc_line_h = max(int(fm.height() * _RC_FONT_SCALE), _MIN_RC_PT) + 2

        if text_w <= 0:
            return

        for section_idx, cell in enumerate(self._grid.levels[-1]):
            if not cell.label:
                continue
            text_h = fm.boundingRect(0, 0, text_w, 10000, _WRAP, cell.label).height()
            if cell.rc_code:
                needed = max(int(text_h / _LABEL_SPLIT), text_h + rc_line_h) + _ROW_HEIGHT_PAD
            else:
                needed = text_h + _ROW_HEIGHT_PAD
            self.resizeSection(section_idx, max(_ROW_HEIGHT_MIN, needed))

    def _compute_column_font_pts(self) -> list[float]:
        """For each depth column, return the smallest font size needed by any cell.

        All cells in the same depth column will be rendered at this uniform size.
        """
        if self._grid is None or not self._grid.levels:
            return []

        fm = self.fontMetrics()
        base_pts = self.font().pointSizeF()
        if base_pts <= 0:
            base_pts = 12.0
        base_pts = max(base_pts, float(_MIN_LABEL_PT))
        text_w = _LEVEL_WIDTH - 12

        col_font_pts: list[float] = []

        for cells in self._grid.levels:
            min_scale = 1.0
            leaf_cursor = 0

            for cell in cells:
                span = 1 if cell.is_leaf else cell.span
                cell_h = sum(
                    self.sectionSize(leaf_cursor + k)
                    for k in range(span)
                    if leaf_cursor + k < self.count()
                )
                if cell_h <= 0:
                    cell_h = _ROW_HEIGHT_MIN

                if cell.label and text_w > 0:
                    text_h = fm.boundingRect(0, 0, text_w, 10000, _WRAP, cell.label).height()
                    if cell.rc_code:
                        avail = int(cell_h * _LABEL_SPLIT) - 2
                    else:
                        avail = cell_h - _ROW_HEIGHT_PAD
                    if text_h > 0 and avail > 0 and text_h > avail:
                        min_scale = min(min_scale, avail / text_h)

                leaf_cursor += span

            col_font_pts.append(max(base_pts * min_scale, float(_MIN_LABEL_PT)))

        return col_font_pts

    # ------------------------------------------------------------------
    # QHeaderView overrides
    # ------------------------------------------------------------------

    def sizeHint(self) -> QSize:
        if self._grid is None:
            return super().sizeHint()
        return QSize(self._grid.depth * _LEVEL_WIDTH, super().sizeHint().height())

    def paintSection(self, painter: QPainter, rect: QRect, logical_index: int) -> None:
        if self._grid is None:
            super().paintSection(painter, rect, logical_index)
            return

        painter.save()
        painter.setClipping(False)

        depth = self._grid.depth
        for level_idx, cells in enumerate(self._grid.levels):
            x = level_idx * _LEVEL_WIDTH
            font_pts = (
                self._col_font_pts[level_idx]
                if level_idx < len(self._col_font_pts)
                else float(_MIN_LABEL_PT)
            )
            leaf_cursor = 0
            for cell in cells:
                span = 1 if cell.is_leaf else cell.span
                if leaf_cursor <= logical_index < leaf_cursor + span:
                    y_start = self.sectionViewportPosition(leaf_cursor)
                    full_height = sum(
                        self.sectionSize(leaf_cursor + k)
                        for k in range(span)
                        if leaf_cursor + k < self.count()
                    )
                    cell_rect = QRect(x, y_start, _LEVEL_WIDTH, full_height)
                    is_leaf_level = (level_idx == depth - 1)
                    self._paint_cell(painter, cell_rect, cell, is_leaf_level, level_idx, depth, font_pts)
                    break
                leaf_cursor += span

        painter.restore()

    def _paint_cell(
        self,
        painter: QPainter,
        rect: QRect,
        cell: Any,
        is_leaf: bool,
        level_idx: int,
        total_levels: int,
        font_pts: float,
    ) -> None:
        if is_leaf:
            bg = _BG_LEAF
        elif level_idx == 0 and total_levels > 2:
            bg = _BG_SPAN_OUTER
        else:
            bg = _BG_SPAN

        painter.fillRect(rect, bg)

        # Borders
        painter.setPen(_BORDER)
        painter.drawLine(rect.bottomLeft(), rect.bottomRight())
        if is_leaf:
            painter.setPen(_BORDER_RIGHT)
        painter.drawLine(rect.topRight(), rect.bottomRight())

        # Label font — uniform size for this depth column
        painter.setPen(_TEXT_MAIN)
        base_font = QFont(painter.font())
        if not is_leaf:
            base_font.setBold(True)
        base_font.setPointSizeF(font_pts)
        painter.setFont(base_font)

        _wrap_flag = Qt.TextFlag.TextWordWrap
        if cell.rc_code:
            label_h = int(rect.height() * _LABEL_SPLIT)
            label_rect = QRect(rect.x() + 6, rect.y() + 2, _LEVEL_WIDTH - 10, label_h - 2)
            rc_rect = QRect(rect.x() + 6, rect.y() + label_h, _LEVEL_WIDTH - 10, rect.height() - label_h - 2)
            painter.drawText(
                label_rect,
                Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter | _wrap_flag,
                cell.label,
            )
            rc_font = QFont(base_font)
            rc_font.setBold(False)
            rc_font.setPointSizeF(max(font_pts * _RC_FONT_SCALE, float(_MIN_RC_PT)))
            painter.setFont(rc_font)
            painter.setPen(_TEXT_RC)
            painter.drawText(rc_rect, Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter | _wrap_flag, cell.rc_code)
        else:
            indent = 6 + level_idx * 4
            inner_rect = QRect(rect.x() + indent, rect.y() + 2, _LEVEL_WIDTH - indent - 4, rect.height() - 4)
            painter.drawText(
                inner_rect,
                Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter | _wrap_flag,
                cell.label,
            )
