"""XbrlTableView — main compound table rendering widget."""

from __future__ import annotations

from typing import TYPE_CHECKING

from PySide6.QtCore import Signal
from PySide6.QtWidgets import (
    QFrame,
    QLabel,
    QTableView,
    QVBoxLayout,
    QWidget,
)

from bde_xbrl_editor.table_renderer.errors import TableLayoutError, ZIndexOutOfRangeError
from bde_xbrl_editor.table_renderer.layout_engine import TableLayoutEngine
from bde_xbrl_editor.table_renderer.models import ComputedTableLayout
from bde_xbrl_editor.ui.widgets.column_header import MultiLevelColumnHeader
from bde_xbrl_editor.ui.widgets.row_header import MultiLevelRowHeader
from bde_xbrl_editor.ui.widgets.table_body_model import TableBodyModel
from bde_xbrl_editor.ui.widgets.z_axis_selector import ZAxisSelector

if TYPE_CHECKING:
    from bde_xbrl_editor.instance.models import XbrlInstance
    from bde_xbrl_editor.taxonomy.models import TableDefinitionPWD, TaxonomyStructure


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

        # Error banner (hidden by default)
        self._error_banner = QLabel(self)
        self._error_banner.setWordWrap(True)
        self._error_banner.setStyleSheet("background: #FFF3CD; color: #856404; padding: 4px;")
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

        # Update headers
        self._col_header.set_header_grid(layout.column_header)
        self._row_header.set_header_grid(layout.row_header)

        # Adjust header sizes
        self._body_view.horizontalHeader().setMinimumHeight(
            layout.column_header.depth * 28
        )
        self._body_view.verticalHeader().setMinimumWidth(
            layout.row_header.depth * 120
        )

        # Wire cell selection
        self._body_view.clicked.connect(
            lambda idx: self.cell_selected.emit(idx.row(), idx.column())
        )
