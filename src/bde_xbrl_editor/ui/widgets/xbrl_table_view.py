"""XbrlTableView — main compound table rendering widget."""

from __future__ import annotations

from typing import TYPE_CHECKING

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QTableView,
    QVBoxLayout,
    QWidget,
)

from bde_xbrl_editor.table_renderer.errors import TableLayoutError, ZIndexOutOfRangeError
from bde_xbrl_editor.table_renderer.layout_engine import TableLayoutEngine
from bde_xbrl_editor.table_renderer.models import ComputedTableLayout
from bde_xbrl_editor.ui import theme
from bde_xbrl_editor.ui.widgets.cell_edit_delegate import CellEditDelegate
from bde_xbrl_editor.ui.widgets.column_header import MultiLevelColumnHeader
from bde_xbrl_editor.ui.widgets.row_header import MultiLevelRowHeader
from bde_xbrl_editor.ui.widgets.table_body_model import TableBodyModel
from bde_xbrl_editor.ui.widgets.z_axis_selector import ZAxisSelector

if TYPE_CHECKING:
    from bde_xbrl_editor.instance.models import XbrlInstance
    from bde_xbrl_editor.taxonomy.models import TableDefinitionPWD, TaxonomyStructure

_DEFAULT_BODY_COLUMN_WIDTH = 172


class XbrlTableView(QFrame):
    """Main compound widget for rendering an XBRL table."""

    cell_selected = Signal(int, int)
    z_index_changed = Signal(int)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)

        self._taxonomy: TaxonomyStructure | None = None
        self._table: TableDefinitionPWD | None = None
        self._instance: XbrlInstance | None = None
        self._layout: ComputedTableLayout | None = None
        self._active_z_index: int = 0

        # Layout
        self._outer_layout = QVBoxLayout(self)
        self._outer_layout.setContentsMargins(0, 0, 0, 0)
        self._outer_layout.setSpacing(0)

        self.setStyleSheet(f"QFrame {{ background: {theme.SURFACE_BG}; }}")

        # Table workspace header
        self._table_header = QFrame(self)
        self._table_header.setStyleSheet(
            f"QFrame {{ background: {theme.SURFACE_BG}; }}"
        )
        header_layout = QHBoxLayout(self._table_header)
        header_layout.setContentsMargins(16, 12, 16, 12)
        header_layout.setSpacing(16)

        title_col = QVBoxLayout()
        title_col.setContentsMargins(0, 0, 0, 0)
        title_col.setSpacing(2)

        self._title_label = QLabel("No table selected", self._table_header)
        self._title_label.setStyleSheet(
            f"color: {theme.TEXT_MAIN}; font-size: 18px; font-weight: 700; background: transparent;"
        )
        title_col.addWidget(self._title_label)

        self._subtitle_label = QLabel("Select a table from the sidebar to start working.", self._table_header)
        self._subtitle_label.setStyleSheet(
            f"color: {theme.TEXT_MUTED}; font-size: 11px; background: transparent;"
        )
        title_col.addWidget(self._subtitle_label)
        header_layout.addLayout(title_col, stretch=1)

        status_col = QVBoxLayout()
        status_col.setContentsMargins(0, 0, 0, 0)
        status_col.setSpacing(6)

        self._meta_label = QLabel("", self._table_header)
        self._meta_label.setStyleSheet(
            f"color: {theme.TEXT_SUBTLE}; font-size: 10px; font-weight: 600; background: transparent;"
        )
        self._meta_label.setAlignment(Qt.AlignmentFlag.AlignRight)
        status_col.addWidget(self._meta_label)

        pills_row = QHBoxLayout()
        pills_row.setContentsMargins(0, 0, 0, 0)
        pills_row.setSpacing(8)

        self._mode_pill = QLabel("Browse mode", self._table_header)
        self._mode_pill.setStyleSheet(self._pill_style(theme.SURFACE_ALT_BG, theme.TEXT_MUTED))
        pills_row.addWidget(self._mode_pill)

        self._z_pill = QLabel("Single view", self._table_header)
        self._z_pill.setStyleSheet(self._pill_style(theme.HEADER_BG_LIGHT, theme.TEXT_MAIN))
        pills_row.addWidget(self._z_pill)

        status_col.addLayout(pills_row)
        header_layout.addLayout(status_col, stretch=0)

        self._outer_layout.addWidget(self._table_header)

        # Error banner (hidden by default)
        self._error_banner = QLabel(self)
        self._error_banner.setWordWrap(True)
        self._error_banner.setStyleSheet(
            f"background: {theme.WARNING_BG}; color: {theme.WARNING_FG};"
            f" border-bottom: 1px solid {theme.BORDER}; padding: 4px;"
        )
        self._error_banner.hide()
        self._outer_layout.addWidget(self._error_banner)

        # Z-axis selector placeholder
        self._z_selector: ZAxisSelector | None = None

        # Body QTableView
        self._body_view = QTableView(self)
        self._col_header = MultiLevelColumnHeader(parent=self._body_view)
        self._row_header = MultiLevelRowHeader(parent=self._body_view)
        self._body_view.setHorizontalHeader(self._col_header)
        self._body_view.setVerticalHeader(self._row_header)
        self._body_view.horizontalHeader().setDefaultSectionSize(_DEFAULT_BODY_COLUMN_WIDTH)
        self._body_view.horizontalHeader().setMinimumSectionSize(120)
        self._body_view.setStyleSheet(
            f"QTableView {{ background: {theme.CELL_BG}; border: none; }}"
        )
        self._outer_layout.addWidget(self._body_view)

    # ------------------------------------------------------------------
    # Properties
    # ------------------------------------------------------------------

    @property
    def active_z_index(self) -> int:
        return self._active_z_index

    @property
    def active_table_id(self) -> str | None:
        return self._table.table_id if self._table is not None else None

    @staticmethod
    def _pill_style(background: str, color: str) -> str:
        return (
            f"QLabel {{ color: {color}; font-size: 10px; font-weight: 600;"
            f" background: {background}; border: 1px solid {theme.BORDER};"
            " border-radius: 8px; padding: 3px 8px; }}"
        )

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def set_table(
        self,
        table: TableDefinitionPWD,
        taxonomy: TaxonomyStructure,
        instance: XbrlInstance | None = None,
    ) -> None:
        """Load and render a table. Clears the previous table if any."""
        self._taxonomy = taxonomy
        self._table = table
        self._instance = instance
        self._active_z_index = 0

        self._error_banner.hide()

        engine = TableLayoutEngine(taxonomy)
        try:
            layout = engine.compute(table, instance=instance, z_index=0)
        except TableLayoutError as exc:
            self._error_banner.setText(f"⚠ Table layout warning: {exc.reason}")
            self._error_banner.show()
            # Try to render with z_index=0 anyway (partial layout)
            try:
                layout = engine.compute(table, instance=None, z_index=0)
            except Exception:  # noqa: BLE001
                return
        except ZIndexOutOfRangeError:
            return

        self._install_layout(layout)

    def set_layout(self, layout: ComputedTableLayout) -> None:
        """Install a pre-computed ComputedTableLayout."""
        self._install_layout(layout)

    def set_z_index(self, z_index: int) -> None:
        """Recompute layout for the given Z-axis member and refresh."""
        if self._table is None or self._taxonomy is None:
            return
        engine = TableLayoutEngine(self._taxonomy)
        try:
            layout = engine.compute(self._table, instance=self._instance, z_index=z_index)
        except (TableLayoutError, ZIndexOutOfRangeError):
            return
        self._active_z_index = z_index
        self._install_layout(layout)
        self.z_index_changed.emit(z_index)

    def refresh_instance(self, instance: XbrlInstance | None) -> None:
        """Re-match fact values without recomputing structure."""
        self._instance = instance
        if self._table is None or self._taxonomy is None:
            return
        engine = TableLayoutEngine(self._taxonomy)
        try:
            layout = engine.compute(
                self._table,
                instance=instance,
                z_index=self._active_z_index,
            )
        except (TableLayoutError, ZIndexOutOfRangeError):
            return
        self._install_layout(layout)

    def clear(self) -> None:
        """Remove the current table and show empty state."""
        self._table = None
        self._taxonomy = None
        self._instance = None
        self._layout = None
        self._error_banner.hide()
        self._title_label.setText("No table selected")
        self._subtitle_label.setText("Select a table from the sidebar to start working.")
        self._meta_label.setText("")
        self._mode_pill.setText("Browse mode")
        self._z_pill.setText("Single view")
        from bde_xbrl_editor.table_renderer.models import (  # noqa: PLC0415
            ComputedTableLayout,
            HeaderGrid,
        )

        empty_grid = HeaderGrid(levels=[[]], leaf_count=0, depth=0)
        empty_layout = ComputedTableLayout(
            table_id="",
            table_label="",
            column_header=empty_grid,
            row_header=empty_grid,
            z_members=[],
            active_z_index=0,
            body=[],
        )
        self._body_view.setModel(TableBodyModel(empty_layout, self))

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    def _install_layout(self, layout: ComputedTableLayout) -> None:
        self._layout = layout
        self._refresh_header(layout)

        # Update Z-axis selector
        if self._z_selector is not None:
            self._outer_layout.removeWidget(self._z_selector)
            self._z_selector.deleteLater()
            self._z_selector = None

        if layout.z_members:
            self._z_selector = ZAxisSelector(layout.z_members, parent=self)
            self._z_selector.z_index_changed.connect(self.set_z_index)
            self._outer_layout.insertWidget(1, self._z_selector)  # after error banner

        # Update body model
        model = TableBodyModel(layout, self)
        if self._taxonomy is not None:
            from bde_xbrl_editor.table_renderer.fact_formatter import FactFormatter  # noqa: PLC0415

            formatter = FactFormatter(self._taxonomy)
            model.set_formatter(formatter, self._taxonomy)
        self._body_view.setModel(model)

        # Keep delegate in sync with the new layout. If main_window has installed a full
        # CellEditDelegate (with taxonomy + editor), update its layout reference so coordinate
        # lookups stay correct after Z-axis changes. Otherwise install a minimal one for painting.
        existing_delegate = self._body_view.itemDelegate()
        if isinstance(existing_delegate, CellEditDelegate):
            existing_delegate.set_table_layout(layout)
        else:
            self._body_view.setItemDelegate(CellEditDelegate(table_view_widget=self._body_view))

        # Update headers
        self._col_header.set_header_grid(layout.column_header)
        self._row_header.set_header_grid(layout.row_header)

        # Adjust header sizes
        self._body_view.horizontalHeader().setDefaultSectionSize(_DEFAULT_BODY_COLUMN_WIDTH)
        self._body_view.horizontalHeader().setMinimumHeight(
            layout.column_header.depth * 28
        )
        self._body_view.verticalHeader().setMinimumWidth(280)

        # Wire cell selection
        self._body_view.clicked.connect(
            lambda idx: self.cell_selected.emit(idx.row(), idx.column())
        )

    def _refresh_header(self, layout: ComputedTableLayout) -> None:
        title = layout.table_label or layout.table_id or "Selected table"
        self._title_label.setText(title)

        subtitle_parts = []
        if layout.table_id:
            subtitle_parts.append(layout.table_id)
        if self._instance is not None:
            subtitle_parts.append("Instance editing")
        else:
            subtitle_parts.append("Taxonomy browse")
        self._subtitle_label.setText("  |  ".join(subtitle_parts))

        row_count = len(layout.body)
        col_count = len(layout.body[0]) if layout.body else 0
        self._meta_label.setText(f"{row_count} rows  |  {col_count} columns")

        self._mode_pill.setText("Edit mode" if self._instance is not None else "Browse mode")
        if layout.z_members:
            active = min(layout.active_z_index, len(layout.z_members) - 1)
            current = layout.z_members[active].label
            if len(layout.z_members) > 1:
                self._z_pill.setText(f"Z-axis: {current}")
            else:
                self._z_pill.setText("Single view")
        else:
            self._z_pill.setText("Single view")
