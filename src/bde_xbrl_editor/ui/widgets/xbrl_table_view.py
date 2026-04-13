"""XbrlTableView — main compound table rendering widget."""

from __future__ import annotations

from typing import TYPE_CHECKING

from PySide6.QtCore import Qt, QThread, QTimer, Signal
from PySide6.QtWidgets import (
    QCheckBox,
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
from bde_xbrl_editor.ui.loading import TableLayoutLoadWorker
from bde_xbrl_editor.ui.widgets.cell_edit_delegate import CellEditDelegate
from bde_xbrl_editor.ui.widgets.column_header import MultiLevelColumnHeader
from bde_xbrl_editor.ui.widgets.row_header import MultiLevelRowHeader
from bde_xbrl_editor.ui.widgets.table_body_model import TableBodyModel
from bde_xbrl_editor.ui.widgets.z_axis_selector import ZAxisSelector

if TYPE_CHECKING:
    from bde_xbrl_editor.instance.models import XbrlInstance
    from bde_xbrl_editor.taxonomy.models import TableDefinitionPWD, TaxonomyStructure

_DEFAULT_BODY_COLUMN_WIDTH = 172
_EDIT_TRIGGERS = (
    QTableView.EditTrigger.DoubleClicked
    | QTableView.EditTrigger.EditKeyPressed
    | QTableView.EditTrigger.AnyKeyPressed
    | QTableView.EditTrigger.SelectedClicked
)


def _table_identity(table: TableDefinitionPWD | None) -> str:
    if table is None:
        return ""
    return table.display_code or table.table_id


def _empty_layout() -> ComputedTableLayout:
    from bde_xbrl_editor.table_renderer.models import HeaderGrid  # noqa: PLC0415

    empty_grid = HeaderGrid(levels=[[]], leaf_count=0, depth=0)
    return ComputedTableLayout(
        table_id="",
        table_label="",
        column_header=empty_grid,
        row_header=empty_grid,
        z_members=[],
        active_z_index=0,
        body=[],
    )


class XbrlTableView(QFrame):
    """Main compound widget for rendering an XBRL table."""

    cell_selected = Signal(int, int)
    z_index_changed = Signal(int)
    editing_mode_changed = Signal(bool)
    layout_ready = Signal(object)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)

        self._taxonomy: TaxonomyStructure | None = None
        self._table: TableDefinitionPWD | None = None
        self._instance: XbrlInstance | None = None
        self._layout: ComputedTableLayout | None = None
        self._active_z_index: int = 0
        self._editing_enabled: bool = False
        self._pending_table_request: tuple[TableDefinitionPWD, TaxonomyStructure, XbrlInstance | None, int] | None = None
        self._table_load_thread: QThread | None = None
        self._table_load_worker: TableLayoutLoadWorker | None = None
        self._table_load_request_id = 0

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

        self._editing_switch = QCheckBox("Editing mode on", self._table_header)
        self._editing_switch.setCursor(Qt.CursorShape.PointingHandCursor)
        self._editing_switch.setStyleSheet(
            f"""
            QCheckBox {{
                color: {theme.TEXT_MAIN};
                font-size: 11px;
                font-weight: 600;
                spacing: 8px;
            }}
            QCheckBox::indicator {{
                width: 34px;
                height: 18px;
                border-radius: 9px;
                border: 1px solid {theme.BORDER};
                background: {theme.DISABLED_BG};
            }}
            QCheckBox::indicator:checked {{
                background: {theme.NAV_BG_DEEP};
                border-color: {theme.NAV_BG_DEEP};
            }}
            """
        )
        self._editing_switch.toggled.connect(self._set_editing_enabled)
        status_col.addWidget(self._editing_switch, alignment=Qt.AlignmentFlag.AlignRight)
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
        self._body_view.setEditTriggers(QTableView.EditTrigger.NoEditTriggers)
        self._outer_layout.addWidget(self._body_view)

        self._table_request_timer = QTimer(self)
        self._table_request_timer.setSingleShot(True)
        self._table_request_timer.timeout.connect(self._apply_requested_table)

    # ------------------------------------------------------------------
    # Properties
    # ------------------------------------------------------------------

    @property
    def active_z_index(self) -> int:
        return self._active_z_index

    @property
    def active_table_id(self) -> str | None:
        return self._table.table_id if self._table is not None else None

    @property
    def editing_enabled(self) -> bool:
        return self._editing_enabled

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
        self._cancel_async_table_load()
        self._table_request_timer.stop()
        self._pending_table_request = None
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

    def request_table(
        self,
        table: TableDefinitionPWD,
        taxonomy: TaxonomyStructure,
        instance: XbrlInstance | None = None,
    ) -> None:
        """Queue a table render for the next UI turn so the shell can paint first."""
        z_index = 0
        self._pending_table_request = (table, taxonomy, instance, z_index)
        self._show_loading_state(table, taxonomy, instance, z_index=z_index, loading_label="Loading table…")
        self._table_request_timer.start(0)

    def set_layout(self, layout: ComputedTableLayout) -> None:
        """Install a pre-computed ComputedTableLayout."""
        self._install_layout(layout)

    def set_z_index(self, z_index: int) -> None:
        """Recompute layout for the given Z-axis member and refresh."""
        if self._table is None or self._taxonomy is None:
            return
        if self._layout is not None and self._layout.active_z_index == z_index:
            return
        self._pending_table_request = (self._table, self._taxonomy, self._instance, z_index)
        self._show_loading_state(
            self._table,
            self._taxonomy,
            self._instance,
            z_index=z_index,
            loading_label="Loading view…",
        )
        self._table_request_timer.start(0)

    def refresh_instance(self, instance: XbrlInstance | None) -> None:
        """Re-match fact values without recomputing structure."""
        self._instance = instance
        if self._pending_table_request is not None:
            table, taxonomy, _, z_index = self._pending_table_request
            self._pending_table_request = (table, taxonomy, instance, z_index)
        if self._table is None or self._taxonomy is None:
            return
        engine = TableLayoutEngine(self._taxonomy)
        if self._layout is not None and self._layout.table_id == self._table.table_id:
            layout = engine.populate_facts(self._layout, instance)
        else:
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
        self._cancel_async_table_load()
        self._table_request_timer.stop()
        self._pending_table_request = None
        self._table = None
        self._taxonomy = None
        self._instance = None
        self._layout = None
        self._error_banner.hide()
        self._title_label.setText("No table selected")
        self._subtitle_label.setText("Select a table from the sidebar to start working.")
        self._meta_label.setText("")
        self._editing_switch.blockSignals(True)
        self._editing_switch.setChecked(False)
        self._editing_switch.blockSignals(False)
        self._editing_switch.setVisible(False)
        self._editing_switch.setText("Editing mode off")
        self._set_editing_enabled(False)
        self._clear_z_selector()
        self._body_view.setModel(TableBodyModel(_empty_layout(), self))

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    def _apply_requested_table(self) -> None:
        if self._pending_table_request is None:
            return
        table, taxonomy, instance, z_index = self._pending_table_request
        self._pending_table_request = None
        self._start_async_table_load(table, taxonomy, instance, z_index)

    def _start_async_table_load(
        self,
        table: TableDefinitionPWD,
        taxonomy: TaxonomyStructure,
        instance: XbrlInstance | None,
        z_index: int,
    ) -> None:
        self._cancel_async_table_load()
        self._table_load_request_id += 1
        request_id = self._table_load_request_id
        worker = TableLayoutLoadWorker(
            request_id=request_id,
            table=table,
            taxonomy=taxonomy,
            instance=instance,
            z_index=z_index,
        )
        thread = QThread(self)
        worker.moveToThread(thread)
        thread.started.connect(worker.run)
        worker.finished.connect(self._on_async_table_loaded, Qt.ConnectionType.QueuedConnection)
        worker.error.connect(self._on_async_table_error, Qt.ConnectionType.QueuedConnection)
        thread.finished.connect(worker.deleteLater)
        thread.finished.connect(thread.deleteLater)
        self._table_load_worker = worker
        self._table_load_thread = thread
        thread.start()

    def _cancel_async_table_load(self) -> None:
        worker = self._table_load_worker
        thread = self._table_load_thread
        self._table_load_worker = None
        self._table_load_thread = None
        if worker is not None:
            worker.cancel()
        if thread is not None and thread.isRunning():
            thread.quit()

    def _finish_async_table_load(self, request_id: int) -> bool:
        if request_id != self._table_load_request_id:
            return False
        thread = self._table_load_thread
        worker = self._table_load_worker
        self._table_load_thread = None
        self._table_load_worker = None
        if worker is not None:
            worker.cancel()
        if thread is not None and thread.isRunning():
            thread.quit()
        return True

    def _on_async_table_loaded(self, request_id: int, layout: ComputedTableLayout, warning: str) -> None:
        if not self._finish_async_table_load(request_id):
            return
        if warning:
            self._error_banner.setText(f"⚠ Table layout warning: {warning}")
            self._error_banner.show()
        else:
            self._error_banner.hide()
        self._install_layout(layout)

    def _on_async_table_error(self, request_id: int, message: str) -> None:
        if not self._finish_async_table_load(request_id):
            return
        self._error_banner.setText(f"⚠ {message}")
        self._error_banner.show()
        self._meta_label.setText("Layout failed")

    def _show_loading_state(
        self,
        table: TableDefinitionPWD,
        taxonomy: TaxonomyStructure,
        instance: XbrlInstance | None,
        *,
        z_index: int,
        loading_label: str,
    ) -> None:
        self._taxonomy = taxonomy
        self._table = table
        self._instance = instance
        self._layout = None
        self._active_z_index = z_index
        self._error_banner.hide()
        if self._z_selector is not None:
            self._outer_layout.removeWidget(self._z_selector)
            self._z_selector.deleteLater()
            self._z_selector = None

        title = table.label or table.table_id or "Selected table"
        self._title_label.setText(title)
        subtitle_parts = []
        table_identity = _table_identity(table)
        if table_identity:
            subtitle_parts.append(table_identity)
        subtitle_parts.append(loading_label)
        self._subtitle_label.setText("  |  ".join(subtitle_parts))
        self._meta_label.setText("Preparing layout…")
        self._editing_switch.setVisible(instance is not None)
        self._editing_switch.setEnabled(False)
        self._editing_switch.blockSignals(True)
        self._editing_switch.setChecked(False)
        self._editing_switch.blockSignals(False)
        self._editing_switch.setText(loading_label)
        self._body_view.setModel(TableBodyModel(_empty_layout(), self))

    def _clear_z_selector(self) -> None:
        if self._z_selector is not None:
            self._outer_layout.removeWidget(self._z_selector)
            self._z_selector.deleteLater()
            self._z_selector = None

    def _install_layout(self, layout: ComputedTableLayout) -> None:
        self._layout = layout
        self._refresh_header(layout)

        # Update Z-axis selector
        self._clear_z_selector()

        if layout.z_members:
            self._z_selector = ZAxisSelector(layout.z_members, parent=self)
            self._z_selector.z_index_changed.connect(self._on_z_selector_changed)
            self._outer_layout.insertWidget(1, self._z_selector)

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

        self._set_editing_enabled(self._editing_enabled and self._instance is not None)

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
        self.layout_ready.emit(layout)

    def _on_z_selector_changed(self, index: int) -> None:
        self.set_z_index(index)
        self.z_index_changed.emit(index)

    def _refresh_header(self, layout: ComputedTableLayout) -> None:
        title = layout.table_label or layout.table_id or "Selected table"
        self._title_label.setText(title)

        subtitle_parts = []
        table_identity = _table_identity(self._table)
        if table_identity:
            subtitle_parts.append(table_identity)
        if self._instance is not None:
            subtitle_parts.append(
                "Editing enabled" if self._editing_enabled else "Editing disabled"
            )
        else:
            subtitle_parts.append("Taxonomy browse")
        if layout.z_members and len(layout.z_members) > 1:
            active = min(layout.active_z_index, len(layout.z_members) - 1)
            subtitle_parts.append(f"View {layout.z_members[active].label}")
        elif layout.z_members:
            subtitle_parts.append("Single view")
        self._subtitle_label.setText("  |  ".join(subtitle_parts))

        row_count = len(layout.body)
        col_count = len(layout.body[0]) if layout.body else 0
        self._meta_label.setText(f"{row_count} rows  |  {col_count} columns")
        self._editing_switch.setVisible(self._instance is not None)
        self._editing_switch.setEnabled(self._instance is not None)
        self._editing_switch.blockSignals(True)
        self._editing_switch.setChecked(self._editing_enabled and self._instance is not None)
        self._editing_switch.blockSignals(False)
        self._editing_switch.setText(
            "Editing mode on" if self._editing_enabled and self._instance is not None else "Editing mode off"
        )

    def _set_editing_enabled(self, enabled: bool) -> None:
        self._editing_enabled = bool(enabled) and self._instance is not None
        self._body_view.setEditTriggers(
            _EDIT_TRIGGERS if self._editing_enabled else QTableView.EditTrigger.NoEditTriggers
        )
        self._editing_switch.setText("Editing mode on" if self._editing_enabled else "Editing mode off")
        if self._layout is not None:
            self._refresh_header(self._layout)
        self.editing_mode_changed.emit(self._editing_enabled)
