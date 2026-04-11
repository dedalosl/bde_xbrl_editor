"""MultiLevelRowHeader — single-column row header with level-based indentation.

Instead of one column per hierarchy level, all rows are rendered in a single
column. The depth of each row in the hierarchy is conveyed by indentation
(16 px per level), a coloured left-edge accent strip, and a subtle background
shade — matching the regulator's reference display.
"""

from __future__ import annotations

from typing import Any

from PySide6.QtCore import QRect, QSize, Qt
from PySide6.QtGui import QColor, QFont, QPainter
from PySide6.QtWidgets import QHeaderView, QWidget

from bde_xbrl_editor.table_renderer.models import HeaderGrid
from bde_xbrl_editor.ui import theme

# ── Geometry ──────────────────────────────────────────────────────────────
_COL_W = 280  # total width of the single header column
_INDENT_BASE = 10  # left padding for the outermost level
_INDENT_STEP = 16  # additional indent per hierarchy level
_ACCENT_W = 4  # width of the coloured left-edge strip
_ROW_HEIGHT_MIN = 24  # minimum row height in px
_ROW_HEIGHT_PAD = 8  # vertical padding inside a row

# ── Typography ────────────────────────────────────────────────────────────
_MIN_LABEL_PT = 9
_MIN_RC_PT = 8
_RC_FONT_SCALE = 0.82  # rc_code drawn smaller than the main label

_TEXT_MAIN = QColor(theme.TEXT_MAIN)
_TEXT_RC = QColor(theme.TEXT_MUTED)
_BORDER = QColor(theme.BORDER)
_BORDER_RIGHT = QColor(theme.BORDER_STRONG)

_WRAP = Qt.AlignmentFlag.AlignLeft | Qt.TextFlag.TextWordWrap


class MultiLevelRowHeader(QHeaderView):
    """Single-column vertical header with indentation-based hierarchy."""

    def __init__(
        self, header_grid: HeaderGrid | None = None, parent: QWidget | None = None
    ) -> None:
        super().__init__(Qt.Orientation.Vertical, parent)
        self._grid: HeaderGrid | None = header_grid
        # Pre-computed per-section depth (0 = outermost group)
        self._section_depth: list[int] = []
        self._section_cells: list[Any] = []
        self.setDefaultSectionSize(_ROW_HEIGHT_MIN)
        self.setSectionResizeMode(QHeaderView.ResizeMode.Interactive)

    # ------------------------------------------------------------------
    # Grid installation
    # ------------------------------------------------------------------

    def set_header_grid(self, header_grid: HeaderGrid) -> None:
        self._grid = header_grid
        self._build_section_map()
        self._auto_size_sections()
        self.viewport().update()

    def _build_section_map(self) -> None:
        """For each section index build (depth, cell).

        The row grid is DFS-ordered: levels[i] = [cell_i].
        Section i maps directly to levels[i][0]; depth comes from cell.level.
        """
        if self._grid is None:
            self._section_depth = []
            self._section_cells = []
            return

        self._section_depth = []
        self._section_cells = []
        for i in range(self._grid.leaf_count):
            if i < len(self._grid.levels) and self._grid.levels[i]:
                cell = self._grid.levels[i][0]
                self._section_depth.append(cell.level)
                self._section_cells.append(cell)
            else:
                self._section_depth.append(0)
                self._section_cells.append(None)

    # ------------------------------------------------------------------
    # Section height sizing
    # ------------------------------------------------------------------

    def _auto_size_sections(self) -> None:
        if self._grid is None:
            return
        fm = self.fontMetrics()
        depth = self._grid.depth

        for section_idx, cell in enumerate(self._section_cells):
            if cell is None:
                continue
            level = (
                self._section_depth[section_idx] if section_idx < len(self._section_depth) else 0
            )
            indent = _ACCENT_W + _INDENT_BASE + level * _INDENT_STEP
            text_w = max(_COL_W - indent - 6, 20)
            label = _display_label(cell)
            if not label:
                continue
            text_h = fm.boundingRect(0, 0, text_w, 10000, int(_WRAP), label).height()
            needed = text_h + _ROW_HEIGHT_PAD
            # Outermost groups (depth 0) get a bit more height
            if level == 0 and depth > 1:
                needed = max(needed, _ROW_HEIGHT_MIN + 6)
            self.resizeSection(section_idx, max(_ROW_HEIGHT_MIN, needed))

    # ------------------------------------------------------------------
    # QHeaderView overrides
    # ------------------------------------------------------------------

    def sizeHint(self) -> QSize:
        return QSize(_COL_W, super().sizeHint().height())

    def paintSection(self, painter: QPainter, rect: QRect, logical_index: int) -> None:
        if self._grid is None or not self._section_cells:
            super().paintSection(painter, rect, logical_index)
            return

        if logical_index >= len(self._section_cells):
            super().paintSection(painter, rect, logical_index)
            return

        cell = self._section_cells[logical_index]
        level = (
            self._section_depth[logical_index] if logical_index < len(self._section_depth) else 0
        )
        depth = self._grid.depth
        is_leaf = (level == depth - 1) or (cell is not None and getattr(cell, "is_leaf", True))

        painter.save()
        painter.setClipping(False)

        self._paint_row(painter, rect, cell, level, depth, is_leaf)

        painter.restore()

    def _paint_row(
        self,
        painter: QPainter,
        rect: QRect,
        cell: Any,
        level: int,
        depth: int,
        is_leaf: bool,
    ) -> None:
        # ── Background ────────────────────────────────────────────────
        bg = QColor(theme.HEADER_SURFACE_BG)
        painter.fillRect(rect, bg)

        # ── Left accent strip ──────────────────────────────────────────
        accent_rect = QRect(rect.x(), rect.y(), _ACCENT_W, rect.height())
        accent = QColor(theme.HEADER_SURFACE_BG)
        painter.fillRect(accent_rect, accent)

        # ── Borders ───────────────────────────────────────────────────
        painter.setPen(_BORDER)
        painter.drawLine(rect.bottomLeft(), rect.bottomRight())
        painter.setPen(_BORDER_RIGHT)
        painter.drawLine(rect.topRight(), rect.bottomRight())

        if cell is None:
            return

        # ── Text ──────────────────────────────────────────────────────
        base_pts = self.font().pointSizeF()
        if base_pts <= 0:
            base_pts = 12.0
        base_pts = max(base_pts, float(_MIN_LABEL_PT))

        base_font = QFont(painter.font())
        base_font.setPointSizeF(base_pts)
        # Group rows (not leaf-level) are bold
        base_font.setBold(not is_leaf)
        painter.setFont(base_font)
        painter.setPen(_TEXT_MAIN)

        indent = _ACCENT_W + _INDENT_BASE + level * _INDENT_STEP
        text_x = rect.x() + indent
        text_w = max(rect.width() - indent - 4, 4)

        label = _display_label(cell)
        inner_rect = QRect(text_x, rect.y() + 2, text_w, rect.height() - 4)
        painter.drawText(
            inner_rect,
            Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter | Qt.TextFlag.TextWordWrap,
            label,
        )


# ---------------------------------------------------------------------------
# Helper
# ---------------------------------------------------------------------------


def _display_label(cell: Any) -> str:
    """Return display text: 'Label (rc_code)' or just 'Label'."""
    label = getattr(cell, "label", "") or ""
    rc = getattr(cell, "rc_code", "") or ""
    if rc and f"({rc})" not in label:
        return f"{label} ({rc})" if label else rc
    return label
