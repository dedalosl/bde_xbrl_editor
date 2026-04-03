"""MultiLevelColumnHeader — custom QHeaderView for X-axis spanning headers."""

from __future__ import annotations

from typing import Any

from PySide6.QtCore import QRect, QSize, Qt
from PySide6.QtGui import QColor, QFont, QLinearGradient, QPainter
from PySide6.QtWidgets import QHeaderView, QWidget

from bde_xbrl_editor.table_renderer.models import HeaderGrid

_LEVEL_HEIGHT_MIN = 28   # minimum px per header level
_LEVEL_HEIGHT_MAX = 300  # generous cap — long labels fit without font scaling
_LEVEL_HEIGHT_PAD = 12   # total vertical padding (top + bottom) within a level
_RC_FONT_SCALE = 0.72
_LABEL_SPLIT = 0.78      # fraction of cell height allocated to label when rc_code present
_MIN_LABEL_PT = 9        # minimum point size for label text
_MIN_RC_PT = 8           # minimum point size for rc_code text

# Color palette — navy/blue financial theme
_BG_LEAF = QColor("#1E3A5F")       # deep navy for leaf (innermost) level
_BG_SPAN = QColor("#2B5287")       # medium blue for span (group) levels
_BG_SPAN_LIGHT = QColor("#3A6AA8") # lighter blue for outermost spans
_TEXT_HEADER = QColor("#FFFFFF")
_TEXT_RC = QColor("#A8C8EE")       # muted blue-white for RC codes
_BORDER = QColor("#16304F")        # darker navy border

_WRAP = int(Qt.AlignmentFlag.AlignCenter | Qt.TextFlag.TextWordWrap)


class MultiLevelColumnHeader(QHeaderView):
    """Custom horizontal header that paints multi-level spanning column headers."""

    def __init__(self, header_grid: HeaderGrid | None = None, parent: QWidget | None = None) -> None:
        super().__init__(Qt.Orientation.Horizontal, parent)
        self._grid: HeaderGrid | None = header_grid
        self._layout_cache: tuple[list[int], list[float]] | None = None
        self.setDefaultSectionSize(100)
        self.setSectionResizeMode(QHeaderView.ResizeMode.Interactive)
        self.sectionResized.connect(self._invalidate_layout)

    def _invalidate_layout(self, *_: Any) -> None:
        self._layout_cache = None
        self.updateGeometry()
        self.viewport().update()

    def set_header_grid(self, header_grid: HeaderGrid) -> None:
        self._grid = header_grid
        self._layout_cache = None
        self.updateGeometry()
        self.viewport().update()

    # ------------------------------------------------------------------
    # Layout computation — heights + uniform font per level
    # ------------------------------------------------------------------

    def _compute_layout(self) -> tuple[list[int], list[float]]:
        """Return (height_per_level, font_pts_per_level).

        Height grows freely up to _LEVEL_HEIGHT_MAX to fit wrapped text.
        All cells in a level share the same font size (the smallest needed).
        """
        if self._layout_cache is not None:
            return self._layout_cache
        if self._grid is None:
            return [], []

        fm = self.fontMetrics()
        base_pts = self.font().pointSizeF()
        if base_pts <= 0:
            base_pts = 12.0
        base_pts = max(base_pts, float(_MIN_LABEL_PT))
        rc_line_h = max(int(fm.height() * _RC_FONT_SCALE), _MIN_RC_PT) + 4

        heights: list[int] = []
        font_pts_list: list[float] = []

        for cells in self._grid.levels:
            max_natural_h = _LEVEL_HEIGHT_MIN
            min_scale = 1.0
            leaf_cursor = 0

            for cell in cells:
                span = 1 if cell.is_leaf else cell.span
                cell_w = (
                    sum(
                        self.sectionSize(leaf_cursor + k) or self.defaultSectionSize()
                        for k in range(span)
                        if leaf_cursor + k < self.count()
                    )
                    - 8  # horizontal padding
                )
                if cell_w > 0 and cell.label:
                    text_h = fm.boundingRect(0, 0, cell_w, 10000, _WRAP, cell.label).height()
                    if cell.rc_code:
                        natural_h = text_h + rc_line_h + _LEVEL_HEIGHT_PAD
                        avail_for_label = int(_LEVEL_HEIGHT_MAX * _LABEL_SPLIT) - 4
                    else:
                        natural_h = text_h + _LEVEL_HEIGHT_PAD
                        avail_for_label = _LEVEL_HEIGHT_MAX - _LEVEL_HEIGHT_PAD
                    max_natural_h = max(max_natural_h, natural_h)
                    if text_h > avail_for_label > 0:
                        min_scale = min(min_scale, avail_for_label / text_h)
                leaf_cursor += span

            # Let the height grow freely — only cap at the generous maximum
            level_h = min(max(max_natural_h, _LEVEL_HEIGHT_MIN), _LEVEL_HEIGHT_MAX)
            level_pts = max(base_pts * min_scale, float(_MIN_LABEL_PT))
            heights.append(level_h)
            font_pts_list.append(level_pts)

        self._layout_cache = (heights, font_pts_list)
        return self._layout_cache

    # ------------------------------------------------------------------
    # QHeaderView overrides
    # ------------------------------------------------------------------

    def sizeHint(self) -> QSize:
        if self._grid is None:
            return super().sizeHint()
        heights, _ = self._compute_layout()
        total_h = sum(heights)
        if total_h <= 0:
            return super().sizeHint()
        return QSize(super().sizeHint().width(), total_h)

    def paintSection(self, painter: QPainter, rect: QRect, logical_index: int) -> None:
        if self._grid is None:
            super().paintSection(painter, rect, logical_index)
            return

        painter.save()
        painter.setClipping(False)

        heights, font_pts_per_level = self._compute_layout()
        depth = self._grid.depth
        y_offset = 0

        for level_idx, cells in enumerate(self._grid.levels):
            level_h = heights[level_idx] if level_idx < len(heights) else _LEVEL_HEIGHT_MIN
            level_pts = font_pts_per_level[level_idx] if level_idx < len(font_pts_per_level) else float(_MIN_LABEL_PT)
            y = y_offset
            leaf_cursor = 0

            for cell in cells:
                span = 1 if cell.is_leaf else cell.span
                if leaf_cursor <= logical_index < leaf_cursor + span:
                    x_start = self.sectionViewportPosition(leaf_cursor)
                    full_width = sum(
                        self.sectionSize(leaf_cursor + k)
                        for k in range(span)
                        if leaf_cursor + k < self.count()
                    )
                    cell_rect = QRect(x_start, y, full_width, level_h)
                    is_leaf_level = (level_idx == depth - 1)
                    self._paint_cell(painter, cell_rect, cell, is_leaf_level, level_idx, depth, level_pts)
                    break
                leaf_cursor += span

            y_offset += level_h

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
        # Background gradient
        if is_leaf:
            bg = _BG_LEAF
        elif level_idx == 0 and total_levels > 2:
            bg = _BG_SPAN_LIGHT
        else:
            bg = _BG_SPAN

        grad = QLinearGradient(rect.topLeft(), rect.bottomLeft())
        grad.setColorAt(0.0, bg.lighter(112))
        grad.setColorAt(1.0, bg)
        painter.fillRect(rect, grad)

        # Border
        painter.setPen(_BORDER)
        painter.drawLine(rect.bottomLeft(), rect.bottomRight())
        painter.drawLine(rect.topRight(), rect.bottomRight())

        # Label font — uniform size for this level
        painter.setPen(_TEXT_HEADER)
        base_font = QFont(painter.font())
        base_font.setBold(True)
        base_font.setPointSizeF(font_pts)
        painter.setFont(base_font)

        _wrap_flag = Qt.TextFlag.TextWordWrap
        if cell.rc_code:
            # Bottom strip for rc_code; label fills the rest
            rc_line_h = max(int(self.fontMetrics().height() * _RC_FONT_SCALE), _MIN_RC_PT) + 4
            label_area_h = rect.height() - rc_line_h - 4
            label_rect = QRect(rect.x() + 4, rect.y() + 2, rect.width() - 8, max(label_area_h, 0))
            rc_y = rect.y() + label_area_h + 2
            rc_rect = QRect(rect.x() + 4, rc_y, rect.width() - 8, rc_line_h)
            painter.drawText(
                label_rect,
                Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignBottom | _wrap_flag,
                cell.label,
            )
            rc_font = QFont(base_font)
            rc_font.setBold(False)
            rc_font.setPointSizeF(max(font_pts * _RC_FONT_SCALE, float(_MIN_RC_PT)))
            painter.setFont(rc_font)
            painter.setPen(_TEXT_RC)
            painter.drawText(rc_rect, Qt.AlignmentFlag.AlignCenter, cell.rc_code)
        else:
            inner_rect = rect.adjusted(4, 2, -4, -2)
            painter.drawText(
                inner_rect,
                Qt.AlignmentFlag.AlignCenter | Qt.AlignmentFlag.AlignVCenter | _wrap_flag,
                cell.label,
            )
